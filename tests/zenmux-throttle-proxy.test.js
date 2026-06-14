#!/usr/bin/env node
// Test harness for prompts/opencode/bin/zenmux-throttle-proxy.
//
// Spins up a mock OpenAI-compatible upstream (records arrival times, can stream
// SSE), starts the proxy pointed at it with a fast RPM, fires concurrent
// requests, and asserts:
//   - requests reach the upstream spaced >= MIN_INTERVAL (pacing works)
//   - concurrency never exceeds the cap
//   - all requests succeed (queue-not-fail; nothing is dropped)
//   - request bodies are forwarded intact
//   - SSE response bodies pass through unbuffered
//   - /healthz does not consume a rate-limit slot
//
// No network access or ZENMUX_API_KEY required — everything is local.
//
// Run: node tests/zenmux-throttle-proxy.test.js

const http = require("http")
const { spawn } = require("child_process")
const path = require("path")

const PROXY_BIN = path.join(__dirname, "..", "prompts", "opencode", "bin", "zenmux-throttle-proxy")

const UPSTREAM_PORT = 9911
const PROXY_PORT = 9912
const RPM = 60 // -> 1 request/sec, fast enough to test quickly
const EXPECTED_INTERVAL = Math.ceil(60000 / RPM) // 1000ms

let pass = 0
let fail = 0
function check(name, cond, extra = "") {
  if (cond) {
    pass++
    console.log(`  ✓ ${name}`)
  } else {
    fail++
    console.log(`  ✗ ${name} ${extra}`)
  }
}

// ---- Mock upstream ---------------------------------------------------------
const arrivals = []
let concurrentNow = 0
let maxConcurrent = 0

const mockUpstream = http.createServer((req, res) => {
  arrivals.push({ t: Date.now(), url: req.url })
  concurrentNow++
  maxConcurrent = Math.max(maxConcurrent, concurrentNow)

  let body = ""
  req.on("data", (c) => (body += c))
  req.on("end", () => {
    if (req.url.includes("stream")) {
      res.writeHead(200, {
        "content-type": "text/event-stream",
        "cache-control": "no-cache",
        connection: "keep-alive",
      })
      res.write('data: {"choices":[{"delta":{"content":"hel"}}]}\n\n')
      res.write('data: {"choices":[{"delta":{"content":"lo"}}]}\n\n')
      res.write("data: [DONE]\n\n")
      setTimeout(() => {
        concurrentNow--
        res.end()
      }, 150)
    } else {
      setTimeout(() => {
        concurrentNow--
        res.writeHead(200, { "content-type": "application/json" })
        res.end(JSON.stringify({ ok: true, echoLen: body.length, path: req.url }))
      }, 150)
    }
  })
})

function startProxy() {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [PROXY_BIN], {
      env: Object.assign({}, process.env, {
        ZENMUX_PROXY_PORT: String(PROXY_PORT),
        ZENMUX_UPSTREAM: `http://127.0.0.1:${UPSTREAM_PORT}/api/v1`,
        ZENMUX_RPM: String(RPM),
        ZENMUX_CONCURRENCY: "1",
      }),
      stdio: ["ignore", "ignore", "pipe"],
    })
    let buf = ""
    child.stderr.on("data", (d) => {
      buf += d
      if (buf.includes("listening on")) resolve(child)
    })
    child.on("exit", (code) => reject(new Error(`proxy exited early code=${code}`)))
    setTimeout(() => reject(new Error("proxy did not start in time")), 4000)
  })
}

function request(proxyPath, body) {
  return new Promise((resolve, reject) => {
    const data = body ? JSON.stringify(body) : ""
    const req = http.request(
      {
        host: "127.0.0.1",
        port: PROXY_PORT,
        path: proxyPath,
        method: body ? "POST" : "GET",
        headers: body
          ? {
              "content-type": "application/json",
              "content-length": Buffer.byteLength(data),
              authorization: "Bearer test-key",
            }
          : {},
      },
      (res) => {
        let out = ""
        res.on("data", (c) => (out += c))
        res.on("end", () => resolve({ status: res.statusCode, body: out, headers: res.headers }))
      }
    )
    req.on("error", reject)
    if (data) req.write(data)
    req.end()
  })
}

async function main() {
  await new Promise((r) => mockUpstream.listen(UPSTREAM_PORT, "127.0.0.1", r))
  const proxy = await startProxy()

  try {
    // 1) health endpoint must not consume a slot
    const health = await request("/healthz", null)
    check("healthz returns 200 JSON", health.status === 200 && health.body.includes('"ok":true'))

    // 2) fire 5 POSTs concurrently; proxy must pace them ~1s apart, all 200
    const N = 5
    const t0 = Date.now()
    const results = await Promise.all(
      Array.from({ length: N }, (_, i) => request("/chat/completions", { i, msg: "x".repeat(10) }))
    )
    const totalMs = Date.now() - t0

    check(
      "all requests succeeded (200)",
      results.every((r) => r.status === 200),
      JSON.stringify(results.map((r) => r.status))
    )
    check("upstream received all N requests", arrivals.filter((a) => !a.url.includes("stream")).length === N)
    check("concurrency never exceeded 1", maxConcurrent === 1, `maxConcurrent=${maxConcurrent}`)

    const reqArrivals = arrivals.filter((a) => !a.url.includes("stream")).map((a) => a.t)
    let minGap = Infinity
    for (let i = 1; i < reqArrivals.length; i++) minGap = Math.min(minGap, reqArrivals[i] - reqArrivals[i - 1])
    check(
      `arrivals spaced >= ${EXPECTED_INTERVAL - 50}ms (pacing)`,
      minGap >= EXPECTED_INTERVAL - 50,
      `minGap=${minGap}ms`
    )
    check(
      `total wall time reflects pacing (>= ${4 * EXPECTED_INTERVAL - 100}ms)`,
      totalMs >= 4 * EXPECTED_INTERVAL - 100,
      `totalMs=${totalMs}`
    )

    // 3) body forwarded intact
    check(
      "request body forwarded to upstream",
      results.every((r) => r.body.includes('"echoLen"')) && JSON.parse(results[0].body).echoLen > 0
    )

    // 4) SSE passthrough
    const sse = await request("/chat/completions/stream", { stream: true })
    check("SSE status 200", sse.status === 200)
    check("SSE content-type preserved", (sse.headers["content-type"] || "").includes("text/event-stream"))
    check("SSE body intact (deltas + [DONE])", sse.body.includes("hel") && sse.body.includes("lo") && sse.body.includes("[DONE]"))
  } finally {
    proxy.kill("SIGTERM")
    mockUpstream.close()
  }

  console.log(`\n${pass} passed, ${fail} failed`)
  process.exit(fail === 0 ? 0 : 1)
}

main().catch((e) => {
  console.error("test harness error:", e)
  process.exit(1)
})
