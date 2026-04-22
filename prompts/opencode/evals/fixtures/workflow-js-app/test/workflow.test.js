const test = require("node:test")
const assert = require("node:assert/strict")

const { createWorkflowEngine } = require("../src/workflow")

test("claims ready steps in priority order within one run", () => {
  const engine = createWorkflowEngine()
  engine.createRun({ id: "run-a", queue: "jobs" })
  engine.addStep("run-a", { id: "low", priority: 10, availableAt: 0, createdAt: 1 })
  engine.addStep("run-a", { id: "high", priority: 20, availableAt: 0, createdAt: 2 })

  const claimed = engine.claim({ queue: "jobs", workerId: "worker-1", now: 100, limit: 2 })

  assert.deepEqual(
    claimed.map((step) => step.id),
    ["high", "low"],
  )
})

test("replays stored events from a cursor", async () => {
  const engine = createWorkflowEngine()
  engine.createRun({ id: "run-a", queue: "jobs" })
  engine.emitRunEvent("run-a", "run.created", {})
  engine.emitRunEvent("run-a", "step.ready", { stepId: "a" })

  const stream = engine.streamRunEvents("run-a", { afterEventId: 1 })
  const seen = []
  stream.on("event", (event) => seen.push(event.type))

  await new Promise((resolve) => setImmediate(resolve))
  stream.close()

  assert.deepEqual(seen, ["step.ready"])
})
