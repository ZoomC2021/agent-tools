const { EventEmitter } = require("node:events")

const TERMINAL_STATUSES = new Set(["succeeded", "failed", "blocked"])

function createWorkflowEngine() {
  const runs = new Map()
  const steps = new Map()
  const events = []
  const subscribers = new Map()
  let nextEventId = 1

  function createRun({ id, queue }) {
    if (runs.has(id)) {
      throw new Error(`RUN_EXISTS:${id}`)
    }

    runs.set(id, {
      id,
      queue,
      status: "active",
      steps: [],
    })
  }

  function addStep(runId, step) {
    const run = mustGetRun(runId)
    const normalized = {
      runId,
      id: step.id,
      queue: step.queue || run.queue,
      priority: step.priority || 0,
      availableAt: step.availableAt || 0,
      createdAt: step.createdAt || 0,
      status: step.status || "ready",
      attempts: step.attempts || 0,
      maxAttempts: step.maxAttempts || 3,
      workerId: null,
      leaseExpiresAt: null,
      output: null,
    }

    if (steps.has(normalized.id)) {
      throw new Error(`STEP_EXISTS:${normalized.id}`)
    }

    steps.set(normalized.id, normalized)
    run.steps.push(normalized.id)
  }

  function claim({ queue, workerId, now, limit = 1, leaseMs = 30000 }) {
    const claimed = []

    for (const run of runs.values()) {
      if (run.queue !== queue || run.status !== "active") continue

      const eligible = run.steps
        .map((id) => steps.get(id))
        .filter((step) => step.status === "ready" && step.availableAt <= now)
        .sort(compareEligibleSteps)

      for (const step of eligible) {
        if (claimed.length >= limit) return claimed.map(publicStep)
        step.status = "running"
        step.workerId = workerId
        step.leaseExpiresAt = now + leaseMs
        step.attempts += 1
        claimed.push(step)
      }
    }

    return claimed.map(publicStep)
  }

  function complete({ stepId, workerId, now, output }) {
    const step = mustGetStep(stepId)
    assertWorkerOwnsStep(step, workerId)

    step.status = "succeeded"
    step.output = output
    step.leaseExpiresAt = null
    emitRunEvent(step.runId, "step.completed", { stepId, now })
    return publicStep(step)
  }

  function fail({ stepId, workerId, now, error }) {
    const step = mustGetStep(stepId)
    assertWorkerOwnsStep(step, workerId)

    if (step.attempts >= step.maxAttempts) {
      step.status = "failed"
      failRun(step.runId)
    } else {
      step.status = "waiting_retry"
      step.availableAt = now + 1000
    }

    step.workerId = null
    step.leaseExpiresAt = null
    emitRunEvent(step.runId, "step.failed", { stepId, error, now })
    return publicStep(step)
  }

  function recoverExpiredLeases({ now }) {
    const expired = [...steps.values()].filter(
      (step) => step.status === "running" && step.leaseExpiresAt <= now,
    )

    for (const snapshot of expired) {
      const step = mustGetStep(snapshot.id)
      if (snapshot.attempts >= snapshot.maxAttempts) {
        step.status = "failed"
        step.workerId = null
        step.leaseExpiresAt = null
        failRun(step.runId)
      } else {
        step.status = "waiting_retry"
        step.workerId = null
        step.leaseExpiresAt = null
        step.availableAt = now + 1000
      }
    }
  }

  function emitRunEvent(runId, type, payload = {}) {
    mustGetRun(runId)
    const event = {
      id: nextEventId,
      runId,
      type,
      payload,
    }
    nextEventId += 1
    events.push(event)

    const listeners = subscribers.get(runId) || new Set()
    for (const listener of listeners) listener(event)

    return event
  }

  function streamRunEvents(runId, { afterEventId = 0 } = {}) {
    mustGetRun(runId)
    const stream = new EventEmitter()
    const replay = events.filter((event) => event.runId === runId && event.id > afterEventId)

    queueMicrotask(() => {
      for (const event of replay) stream.emit("event", event)
    })

    stream.close = () => {}
    return stream
  }

  function getRun(runId) {
    const run = mustGetRun(runId)
    return {
      id: run.id,
      queue: run.queue,
      status: run.status,
      steps: run.steps.map((id) => publicStep(steps.get(id))),
    }
  }

  function getStep(stepId) {
    return publicStep(mustGetStep(stepId))
  }

  function failRun(runId) {
    const run = mustGetRun(runId)
    run.status = "failed"

    for (const stepId of run.steps) {
      const step = mustGetStep(stepId)
      if (!TERMINAL_STATUSES.has(step.status)) {
        step.status = "blocked"
        step.workerId = null
        step.leaseExpiresAt = null
      }
    }
  }

  function mustGetRun(runId) {
    const run = runs.get(runId)
    if (!run) throw new Error(`RUN_NOT_FOUND:${runId}`)
    return run
  }

  function mustGetStep(stepId) {
    const step = steps.get(stepId)
    if (!step) throw new Error(`STEP_NOT_FOUND:${stepId}`)
    return step
  }

  function assertWorkerOwnsStep(step, workerId) {
    if (step.status !== "running" || step.workerId !== workerId) {
      throw new Error("LEASE_NOT_HELD")
    }
  }

  return {
    addStep,
    claim,
    complete,
    createRun,
    emitRunEvent,
    fail,
    getRun,
    getStep,
    recoverExpiredLeases,
    streamRunEvents,
  }
}

function compareEligibleSteps(left, right) {
  return (
    right.priority - left.priority ||
    left.availableAt - right.availableAt ||
    left.createdAt - right.createdAt
  )
}

function publicStep(step) {
  return {
    id: step.id,
    runId: step.runId,
    queue: step.queue,
    priority: step.priority,
    availableAt: step.availableAt,
    createdAt: step.createdAt,
    status: step.status,
    attempts: step.attempts,
    maxAttempts: step.maxAttempts,
    workerId: step.workerId,
    leaseExpiresAt: step.leaseExpiresAt,
    output: step.output,
  }
}

module.exports = {
  createWorkflowEngine,
}
