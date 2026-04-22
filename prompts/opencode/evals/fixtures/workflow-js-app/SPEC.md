# Workflow Engine Contract

This project is an in-memory workflow engine used for evaluating correctness-sensitive coding work.
The existing tests are intentionally incomplete. Passing `npm test` is necessary, but not sufficient.

## Runs

A run has an `id`, a `queue`, a `status`, and an ordered list of step ids.

Valid run statuses:

- `active`: work can still be claimed.
- `succeeded`: every step in the run has succeeded.
- `failed`: one step exhausted its attempts.

When every step in an active run is `succeeded`, the run must become `succeeded`.

When one step exhausts its attempts, the run must become `failed`. Every other non-terminal step in that run must become `blocked`.

## Steps

A step has an `id`, `runId`, `queue`, `priority`, `availableAt`, `createdAt`, `status`, `attempts`, `maxAttempts`, `workerId`, `leaseExpiresAt`, and `output`.

Runnable step statuses:

- `ready`
- `waiting_retry`, if `availableAt <= now`

Terminal step statuses:

- `succeeded`
- `failed`
- `blocked`

## Claiming Work

`claim({ queue, workerId, now, limit, leaseMs })` must select eligible work globally across every active run on the queue.

Eligible work is any runnable step whose `availableAt <= now`.

Ordering is global, not per run:

1. `priority` descending
2. `availableAt` ascending
3. `createdAt` ascending

The claim operation must set each claimed step to `running`, assign `workerId`, set `leaseExpiresAt = now + leaseMs`, increment `attempts`, and return public step snapshots.

## Leases

Only the worker holding a running step may complete or fail it.

`complete({ stepId, workerId, now, output })` and `fail({ stepId, workerId, now, error })` must reject expired leases. The thrown error message must contain `LEASE_EXPIRED`.

An expired lease must not be allowed to mark a step `succeeded` or user-failed. Expired leases are handled by recovery.

## Recovery

`recoverExpiredLeases({ now })` must process all currently expired running steps.

If an expired step has remaining attempts, it becomes `waiting_retry`, clears worker and lease fields, and receives a future `availableAt`.

If an expired step has exhausted attempts, it becomes `failed` and its run fails.

Recovery must be stable when multiple steps in the same run expire in one pass. If one expired step fails the run, any sibling step that also appeared in the recovery snapshot must remain `blocked`, not become retryable afterward.

## Events

`emitRunEvent(runId, type, payload)` stores a monotonically increasing event and notifies live subscribers for that run.

`streamRunEvents(runId, { afterEventId })` must replay stored events with `id > afterEventId`, then keep delivering live events emitted after the stream starts.

`close()` on a stream must unregister its live listener.

## Build

`npm run build` must create the file used by `npm start`.

The clean build-start flow must work from a fresh checkout:

```sh
npm run build && npm start
```
