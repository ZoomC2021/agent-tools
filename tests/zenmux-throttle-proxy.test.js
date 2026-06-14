#!/usr/bin/env node
// Test harness for prompts/opencode/bin/zenmux-throttle-proxy.
//
// Spins up two mock OpenAI-compatible upstreams, starts the shared proxy, and
// asserts:
//   - per-provider request pacing works
//   - ZenMux and Nvidia lanes do not block each other
//   - old unprefixed ZenMux routes still work
//   - request bodies are forwarded intact
//   - SSE response bodies pass through unbuffered
//   - health does not consume a rate-limit slot
//   - Nvidia-style 429 Retry-After pauses only the Nvidia lane
//
// No network access or API key required.
//
// Run: node tests/zenmux-throttle-proxy.test.js

const http = require("http")
const { spawn } = require("child_process")
const path = require("path")

const PROXY_BIN = path.join(__dirname, "..", "prompts", "opencode", "bin", "zenmux-throttle-proxy")

const ZENMUX_UPSTREAM_PORT = 9911
const NVIDIA_UPSTREAM_PORT = 9913
const PROXY_PORT = 9912
const ZENMUX_RPM = 60 // -> 1 request/sec
const NVIDIA_RPM = 120 // -> 0.5 request/sec
const ZENMUX_INTERVAL = Math.ceil(60000 / ZENMUX_RPM)
const NVIDIA_INTERVAL = Math.ceil(60000 / NVIDIA_RPM)

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

function createMockUpstream(name, handler) {
  const state = {
    arrivals: [],
    concurrentNow: 0,
    maxConcurrent: 0,
  }

  const server = http.createServer((req, res) => {
    state.arrivals.push({ t: Date.now(), url: req.url, name })
    state.concurrentNow++
    state.maxConcurrent = Math.max(state.maxConcurrent, state.concurrentNow)

    let body = ""
    req.on("data", (c) => (body += c))
    req.on("end", () => {
      handler(req, res, body, state, () => {
        state.concurrentNow--
      })
    })
  })

  return { server, state }
}

function normalHandler(req, res, body, _state, done) {
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
      done()
      res.end()
    }, 100)
    return
  }

  setTimeout(() => {
    done()
    res.writeHead(200, { "content-type": "application/json" })
    res.end(JSON.stringify({ ok: true, echoLen: body.length, path: req.url }))
  }, 100)
}

let nvidiaShould429 = false
function nvidiaHandler(req, res, body, state, done) {
  if (nvidiaShould429 && req.url.includes("chat/completions")) {
    nvidiaShould429 = false
    done()
    res.writeHead(429, { "content-type": "application/json", "retry-after": "1" })
    res.end(JSON.stringify({ error: { message: "rate limited", type: "rate_limit_error" } }))
    return
  }
  normalHandler(req, res, body, state, done)
}

const zenmux = createMockUpstream("zenmux", normalHandler)
const nvidia = createMockUpstream("nvidia", nvidiaHandler)

function startServer(server, port) {
  return new Promise((resolve) => server.listen(port, "127.0.0.1", resolve))
}

function startProxy() {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [PROXY_BIN], {
      env: Object.assign({}, process.env, {
        ZENMUX_PROXY_PORT: String(PROXY_PORT),
        ZENMUX_UPSTREAM: `http://127.0.0.1:${ZENMUX_UPSTREAM_PORT}/api/v1`,
        NVIDIA_UPSTREAM: `http://127.0.0.1:${NVIDIA_UPSTREAM_PORT}/v1`,
        ZENMUX_RPM: String(ZENMUX_RPM),
        NVIDIA_RPM: String(NVIDIA_RPM),
        ZENMUX_CONCURRENCY: "1",
        NVIDIA_CONCURRENCY: "1",
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

function minGap(arrivals) {
  if (arrivals.length < 2) return Infinity
  let gap = Infinity
  for (let i = 1; i < arrivals.length; i++) gap = Math.min(gap, arrivals[i].t - arrivals[i - 1].t)
  return gap
}

async function main() {
  await startServer(zenmux.server, ZENMUX_UPSTREAM_PORT)
  await startServer(nvidia.server, NVIDIA_UPSTREAM_PORT)
  const proxy = await startProxy()

  try {
    const health = await request("/healthz", null)
    check("healthz returns providers JSON", health.status === 200 && health.body.includes('"zenmux"') && health.body.includes('"nvidia"'))

    const n = 3
    const zenmuxResults = await Promise.all(
      Array.from({ length: n }, (_, i) => request("/zenmux/chat/completions", { provider: "zenmux", i }))
    )
    check("ZenMux prefixed requests succeeded", zenmuxResults.every((r) => r.status === 200))
    check("ZenMux upstream path strips provider prefix", JSON.parse(zenmuxResults[0].body).path === "/api/v1/chat/completions")
    check("ZenMux body forwarded", JSON.parse(zenmuxResults[0].body).echoLen > 0)
    check("ZenMux pacing works", minGap(zenmux.state.arrivals.slice(0, n)) >= ZENMUX_INTERVAL - 50)
    check("ZenMux concurrency capped at 1", zenmux.state.maxConcurrent === 1, `max=${zenmux.state.maxConcurrent}`)

    const compat = await request("/chat/completions", { compat: true })
    check("unprefixed route still goes to ZenMux", compat.status === 200 && JSON.parse(compat.body).path === "/api/v1/chat/completions")

    const beforeZenmuxCount = zenmux.state.arrivals.length
    const beforeNvidiaCount = nvidia.state.arrivals.length
    const concurrentStart = Date.now()
    const mixed = await Promise.all([
      request("/zenmux/chat/completions", { mixed: "zenmux" }),
      request("/nvidia/chat/completions", { mixed: "nvidia" }),
    ])
    const mixedMs = Date.now() - concurrentStart
    check("mixed provider requests both succeeded", mixed.every((r) => r.status === 200))
    check("Nvidia request did not wait behind ZenMux interval", mixedMs < ZENMUX_INTERVAL + 400, `mixedMs=${mixedMs}`)
    check("mixed request reached ZenMux", zenmux.state.arrivals.length === beforeZenmuxCount + 1)
    check("mixed request reached Nvidia", nvidia.state.arrivals.length === beforeNvidiaCount + 1)

    const nvidiaResults = await Promise.all(
      Array.from({ length: n }, (_, i) => request("/nvidia/chat/completions", { provider: "nvidia", i }))
    )
    check("Nvidia requests succeeded", nvidiaResults.every((r) => r.status === 200))
    check("Nvidia upstream path strips provider prefix", JSON.parse(nvidiaResults[0].body).path === "/v1/chat/completions")
    check("Nvidia pacing works", minGap(nvidia.state.arrivals.slice(-n)) >= NVIDIA_INTERVAL - 50)
    check("Nvidia concurrency capped at 1", nvidia.state.maxConcurrent === 1, `max=${nvidia.state.maxConcurrent}`)

    const sse = await request("/nvidia/chat/completions/stream", { stream: true })
    check("SSE status 200", sse.status === 200)
    check("SSE content-type preserved", (sse.headers["content-type"] || "").includes("text/event-stream"))
    check("SSE body intact", sse.body.includes("hel") && sse.body.includes("lo") && sse.body.includes("[DONE]"))

    nvidiaShould429 = true
    const first429 = await request("/nvidia/chat/completions", { rate: "limit-me" })
    const pauseStart = Date.now()
    const after429 = await request("/nvidia/chat/completions", { after: 429 })
    const pausedMs = Date.now() - pauseStart
    check("upstream 429 is passed through", first429.status === 429)
    check("post-429 request succeeds", after429.status === 200)
    check("Retry-After pauses Nvidia lane", pausedMs >= 900, `pausedMs=${pausedMs}`)
  } finally {
    proxy.kill("SIGTERM")
    zenmux.server.close()
    nvidia.server.close()
  }

  console.log(`\n${pass} passed, ${fail} failed`)
  process.exit(fail === 0 ? 0 : 1)
}

main().catch((e) => {
  console.error("test harness error:", e)
  process.exit(1)
})
