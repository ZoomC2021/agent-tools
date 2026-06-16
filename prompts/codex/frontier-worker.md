---
name: frontier-worker
description: "Orchestrate a task by delegating all exploration and coding to the cmd CLI (MiniMax-M3), then dual-review every change with a clean-context subagent (Codex multi-agent) and an independent agy reviewer (Gemini 3.1 Pro)."
---

# Frontier Worker

You are the **orchestrator**. You plan, sequence, delegate, consolidate, and iterate — but you do **not** investigate the codebase or write code yourself. **All exploration and all coding are delegated to the `cmd` CLI** (a free MiniMax-M3 worker): read-only investigation in plan mode, implementation in edit mode. Every change is then reviewed twice in parallel — by a **clean-context subagent you dispatch** via Codex's native multi-agent capability (so the review is uncontaminated by your planning context), and by an **independent reviewer** running the `agy` CLI (Gemini 3.1 Pro). You consolidate both reviews and route fixes back to the worker until the work is clean.

Operate on the task the user described in this session.

Neither `cmd` nor `agy` supports ACP or an SDK, so both are driven one-shot in `--print` mode. Treat each invocation as a stateless call: everything the worker or reviewer needs must be in the prompt.

## Roles

| Role | Who | Model | Responsibility |
|------|-----|-------|----------------|
| **Orchestrator** | you (this CLI) | — | Plan, sequence, write briefs, consolidate reviews, decide when done |
| **Explorer** | `cmd -p --permission-mode plan` | `MiniMaxAI/MiniMax-M3-Free` | **All** read-only investigation: search, read, trace, report findings |
| **Worker** | `cmd -p --yolo` | `MiniMaxAI/MiniMax-M3-Free` | **All** coding: implementation, edits, refactors, test writing |
| **Reviewer A** | dispatched subagent (Codex multi-agent) | codex default | Reviews the worker's diff with **clean context** |
| **Reviewer B** | `agy -p` | `Gemini 3.1 Pro (High)` | **Independent** review of the same diff, in parallel with Reviewer A |

You never read project source or edit files directly. Delegate: exploration → `cmd` plan mode, coding → `cmd` edit mode, review → a dispatched subagent. You may read/write only scratch files under `$FW_DIR` — prompts, bundles, and the CLIs' output files.

## Configuration (flexible knobs)

All overridable via environment; defaults shown:

```bash
FW_WORKER_MODEL="${FW_WORKER_MODEL:-MiniMaxAI/MiniMax-M3-Free}"   # cmd explore + coding model
FW_REVIEW_MODEL="${FW_REVIEW_MODEL:-Gemini 3.1 Pro (High)}"        # agy reviewer model
FW_TIMEOUT="${FW_TIMEOUT:-900}"                                    # per-call seconds
FW_MAX_TURNS="${FW_MAX_TURNS:-40}"                                 # cmd --max-turns cap
FW_MAX_ITERS="${FW_MAX_ITERS:-3}"                                  # implement→review→fix loops
FW_DIR="$(mktemp -d)"                                              # scratch for prompts/bundles
```

## Prerequisites

- `cmd` (Command Code) — required. `command -v cmd`. If missing, stop and tell the user the worker is unavailable.
- Codex multi-agent dispatch — used for Reviewer A (the `multi_agent` feature is on by default). If subagent dispatch is unavailable in this environment, fall back to a fresh `codex exec -s read-only` process for the same clean-context review (see Phase 3).
- `agy` (Antigravity CLI) — optional. `command -v agy`. If missing, **skip Reviewer B** and run with the Reviewer A subagent only; note it in the final report.

A portable, **SIGKILL-capable** timeout wrapper (stock macOS has no `timeout`; some CLIs ignore softer signals):

```bash
fw_timeout() {
  if command -v timeout >/dev/null 2>&1; then timeout -k 10 "$FW_TIMEOUT" "$@"
  elif command -v gtimeout >/dev/null 2>&1; then gtimeout -k 10 "$FW_TIMEOUT" "$@"
  else
    "$@" & local p=$!
    ( sleep "$FW_TIMEOUT"; kill -9 "$p" 2>/dev/null ) & local w=$!
    wait "$p"; local s=$?; kill "$w" 2>/dev/null; return "$s"
  fi
}
```

## Phase 0: Plan, with exploration delegated to `cmd`

1. Restate the user's intent in one sentence so a misread is caught early.
2. **Delegate investigation to the Explorer** — you do not read project files yourself. Write a focused exploration brief and run `cmd` in read-only **plan mode**:

   ```bash
   read -r -d '' EXPLORE_BRIEF <<'EOF'
   <what to find: relevant files, structure, constraints, where a change would go, risks.
   Report findings only — file paths, key signatures, and how the pieces connect. Do NOT modify anything.>
   EOF

   fw_timeout cmd -p "$EXPLORE_BRIEF" \
     -m "$FW_WORKER_MODEL" \
     --permission-mode plan -t --skip-onboarding --max-turns "$FW_MAX_TURNS" \
     < /dev/null > "$FW_DIR/explore.out" 2>&1
   ```

   Plan mode is read-only — the Explorer cannot edit. Read `explore.out` (a scratch file, allowed) for the findings. Run more passes if a question remains open.
3. From the Explorer's findings, decompose the work into the smallest sequence of **independently verifiable** steps. Prefer one focused worker call per step (each `cmd` call is a stateless print-mode process; smaller briefs review better and fail smaller).

## Phase 1: Delegate Implementation to the Worker

For each step, write a **self-contained brief** — the worker shares none of your context. Include: the goal, exact files/paths, relevant code excerpts or signatures, constraints, and a crisp definition of done. Then invoke `cmd` in print mode (it operates on the current working directory):

```bash
read -r -d '' WORKER_BRIEF <<'EOF'
<self-contained task brief: goal, files, constraints, definition-of-done>
EOF

fw_timeout cmd -p "$WORKER_BRIEF" \
  -m "$FW_WORKER_MODEL" \
  --yolo --skip-onboarding --max-turns "$FW_MAX_TURNS" \
  < /dev/null > "$FW_DIR/worker.out" 2>&1
WORKER_STATUS=$?
```

- `--yolo` skips permission prompts, `--skip-onboarding` skips taste setup (both required for non-interactive runs).
- `< /dev/null` is mandatory: under an orchestrator, stdin is an open pipe that never closes and the worker can block on it forever.
- Exit `8` = turn cap hit (`--max-turns`): the worker stopped mid-task. Treat the result as **partial** — inspect the diff, then either raise `FW_MAX_TURNS` or send a follow-up brief for the remainder. Exit `124`/`137` = timeout. Other non-zero = failure: read `worker.out` and re-brief with the error.

## Phase 2: Capture the Diff Bundle

After each worker call (or after the full step sequence), snapshot the changes for review. `git add -N` surfaces newly created files in the diff:

```bash
BUNDLE="$FW_DIR/bundle.diff"
git add -N . 2>/dev/null
{
  echo "===== git status --short ====="; git status --short
  echo "===== git diff HEAD -U40 ====="; git diff HEAD -U40
} > "$BUNDLE"
```

If the bundle is empty, the worker made no changes — re-read `worker.out`, decide whether the brief was wrong or the work is genuinely a no-op, and re-brief or report accordingly.

## Phase 3: Dual Review (in parallel, both clean-context)

Run **both** reviewers against the same bundle at the same time. Launch the independent `agy` reviewer in the background, then dispatch the Reviewer A subagent so they run concurrently.

Shared output contract:

```bash
read -r -d '' REVIEW_PROMPT <<EOF
You are a meticulous, independent code reviewer. Read the diff at $BUNDLE and review ONLY those changes (read full files in the repo for context as needed).
Find correctness bugs, regressions, security/secret issues, error-handling gaps, race conditions, and missing tests.
For EACH issue output exactly one pipe-delimited line and NOTHING else:
SEVERITY | CATEGORY | file:line | description | CONFIDENCE
- SEVERITY: Critical | Warning | Suggestion   - CATEGORY: Logic | Security | Performance | Regression | Tests | Other   - CONFIDENCE: High | Medium | Low
If there are no issues, output exactly: NO_ISSUES. No prose, headings, or code fences.
EOF
```

**Reviewer B — independent (`agy`, Gemini 3.1 Pro High):**

```bash
if command -v agy >/dev/null 2>&1; then
  fw_timeout agy -p "$REVIEW_PROMPT" \
    --model "$FW_REVIEW_MODEL" --dangerously-skip-permissions \
    < /dev/null > "$FW_DIR/review-agy.txt" 2>&1 &
  AGY_PID=$!
fi
```

`agy` quirks to respect: it **hangs forever without `< /dev/null`**; it must run inside a directory listed in `trustedWorkspaces` in `~/.gemini/antigravity-cli/settings.json` (untrusted dirs block on a trust prompt — if the run produces no output and no findings, this is the likely cause; tell the user to add the repo to `trustedWorkspaces`); and it ignores SIGALRM/SIGTERM, so only the SIGKILL-capable `fw_timeout` above can stop a stuck run.

**Reviewer A — clean-context subagent (Codex multi-agent):** dispatch a subagent using Codex's native multi-agent capability to perform the review. A subagent starts with **clean context** — none of your planning history — so its read of the diff is unbiased. Pass it the bundle path and `$REVIEW_PROMPT` (the same contract as Reviewer B), and have it report findings back as pipe-delimited lines. Launch it so it runs concurrently with the `agy` lane.

If native subagent dispatch is unavailable in this environment, fall back to a fresh `codex exec` process (also clean context), read-only:

```bash
fw_timeout codex exec -s read-only --skip-git-repo-check "$REVIEW_PROMPT" \
  < /dev/null > "$FW_DIR/review-codex.txt" 2>&1
CODEX_STATUS=$?
```

Do not review the diff yourself in your own context — the whole point is to keep this review uncontaminated. Then join the background `agy` lane:

```bash
if [[ -n "${AGY_PID:-}" ]]; then wait "$AGY_PID"; AGY_STATUS=$?; fi
```

Collect Reviewer A's findings (returned by the subagent, or from `review-codex.txt` if you used the `codex exec` fallback) and parse `review-agy.txt`: strip code fences / log lines / narration, keep only conforming pipe lines, treat `NO_ISSUES` (or pure narration) as clean. If a lane timed out/failed, note it and proceed with whichever review succeeded.

## Phase 4: Consolidate

Merge both reviewers' findings. Cross-reference by `file:line + category`:

| Agreement | Weight |
|-----------|--------|
| Both the subagent **and** agy flag it | **Consensus — fix first** |
| Only one flags it, High confidence | Likely real — fix |
| Only one, Medium/Low | Judgment call — fix if cheap/safe, else note |
| Conflicting assessments | **Never auto-resolve** — keep both, decide explicitly and say why |

Drop nits that don't affect correctness unless they're trivial. Produce a concrete fix list.

## Phase 5: Iterate

If there are must-fix findings and you are under `FW_MAX_ITERS`:
1. Write a **fix brief** for the worker (consolidated findings + exact locations + what "fixed" means).
2. Re-run **Phase 1** (worker) → **Phase 2** (bundle) → **Phase 3** (dual review) → **Phase 4**.

Stop when: both reviewers are clean (or only accepted low-severity notes remain), **or** `FW_MAX_ITERS` is reached, **or** two consecutive iterations fail to make progress — in that case STOP, summarize the unresolved findings, and hand back to the user rather than thrashing.

## Phase 6: Report

```
## Frontier Worker — <one-line task>
Explore+Code: cmd / <FW_WORKER_MODEL>   |   Reviewers: clean-context subagent + agy / <FW_REVIEW_MODEL>
Iterations: <n>/<FW_MAX_ITERS>

### Changes
<files touched, what changed, why>

### Review outcome
- Consensus issues fixed:  <n>
- Single-reviewer fixed:   <n>
- Accepted / deferred:     <n>  (with reasons)
- subagent reviewer: ok / timeout / failed   |   agy reviewer: ok / timeout / failed / skipped(not installed)

### Verification
<tests/build run by the worker and their result, or what still needs checking>

### Open items / risks
<anything unresolved or needing human judgment>
```

Then clean up: `rm -rf "$FW_DIR"`.

## Failure Handling

- **`cmd` missing** → stop; the worker is required.
- **`agy` missing/unauthenticated/untrusted-workspace** → skip Reviewer B, review with the Reviewer A subagent only, note it.
- **Worker exit 8 (turn cap)** → partial result; inspect diff, raise `FW_MAX_TURNS` or send a remainder brief.
- **Worker/reviewer timeout (124/137)** → raise `FW_TIMEOUT` or narrow the brief; retry once, then report.
- **Worker produces no diff** → re-read its output; re-brief or report a genuine no-op.
- **Reviewers disagree** → surface both, decide explicitly, never silently pick one.
- **No progress two iterations running** → stop and hand back to the user.
- **Secret hygiene** → never read, print, or copy provider API keys; reference model ids only.
