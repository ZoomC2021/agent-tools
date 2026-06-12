---
description: Wide fan-out code review across four cheap-model CLIs (Grok Composer 2.5, Qwen3.7-Max, OpenCode / MiMo v2.5 Pro, MiniMax-M3 via pi) run in parallel, then consolidated into a vote-weighted report. Diff mode (default) or full-codebase mode (--full)
mode: subagent
model: xiaomi/mimo-v2.5-pro
---

# WideReview: Wide Fan-Out Cheap-Model Code Review

Run code reviews across **four independent cheap-model CLIs in parallel** — `Grok Composer 2.5`, `Qwen3.7-Max`, `OpenCode` (MiMo v2.5 Pro), and `pi` (MiniMax-M3) — then consolidate the findings into a single vote-weighted report.

💡 **Cost note**: All four are low-cost models. Unlike `ultrareview` (2 premium models, depth), WideReview favors **breadth** — several independent reviewers at near-zero cost. Use it for broad coverage and cheap second opinions.

## Modes

WideReview has two modes. The host agent is the **orchestrator only** — it gathers context, launches the lanes, and consolidates results; it does not review the code itself.

| Mode | Invocation | What is reviewed |
|------|-----------|------------------|
| **Diff** (default) | `/widereview` | Uncommitted changes (`git diff`) — fast, cheap, the common pre-commit case |
| **Full** | `/widereview --full [path]` | The entire application source (or just `path`) — a whole-codebase audit |

Pick the mode from the user's request, then follow Phase 1 for that mode. Phases 2–6 are identical for both.

## Lanes

| Lane | CLI | Model | Reasoning effort |
|------|-----|-------|------------------|
| A | `grok` | `grok-composer-2.5-fast` | model default |
| B | `qodercli` | `Qwen3.7-Max` | max (flag) |
| C | `opencode run` | `xiaomi/mimo-v2.5-pro` (MiMo v2.5 Pro) | model default |
| D | `pi` | `MiniMax-M3` (via `tokenrouter` provider) | n/a |

Consolidating four independent reviewers catches issues any single model misses and surfaces conflicting interpretations.

## Prerequisites

Each lane is optional. Missing or unauthenticated CLIs are **skipped**, and the review proceeds with whatever is available (at least one lane is required).

- `grok` (Grok) — `command -v grok`
- `qodercli` (Qoder) — `command -v qodercli`
- `opencode` (MiMo v2.5 Pro) — `command -v opencode`
- `pi` (MiniMax-M3) — `command -v pi`

⚠️ **Secret hygiene**: The OpenCode lane is backed by OpenCode's xiaomi provider configuration; the `pi` lane is backed by pi's `tokenrouter` provider configuration (custom provider defined in `~/.pi/agent/models.json`, OpenAI-compatible API at `https://api.tokenrouter.com/v1`, auth via `$TOKENROUTER_API_KEY`). Reference the model ids `xiaomi/mimo-v2.5-pro` and `MiniMax-M3` only — never read, print, or copy provider API keys.

## Phase 1 (Diff mode): Gather Context

Capture the uncommitted changes into one shared diff bundle. Use `git add -N` first so newly created (untracked) files appear in the diff:

```bash
WR_DIR=$(mktemp -d)
BUNDLE="$WR_DIR/bundle.diff"
git add -N . 2>/dev/null   # intent-to-add: surfaces untracked files in the diff
{
  echo "===== git status --short ====="
  git status --short
  echo "===== git diff HEAD (unstaged + staged vs HEAD) ====="
  git diff HEAD -U40
  echo "===== git diff --cached ====="
  git diff --cached -U40
} > "$BUNDLE"
WR_TIMEOUT=${WR_TIMEOUT:-480}
```

If the bundle is empty, report "No changes to review" and stop.

## Phase 1 (Full mode): Build a Scoped Manifest

Full-codebase reviews must be **anchored to a deterministic file manifest** — this scopes the review, excludes vendored/build noise, and (critically) stops the agentic lanes from wandering. Do NOT dump the whole tree into the prompt.

```bash
WR_DIR=$(mktemp -d)
ROOT="${1:-.}"                 # optional subpath argument
MANIFEST="$WR_DIR/manifest.txt"

# Prefer git (honors .gitignore); fall back to find. Then strip vendor/build noise.
if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  ( cd "$ROOT" && git ls-files )
else
  find "$ROOT" -type f
fi \
  | grep -vE '/(\.venv|venv|node_modules|dist|build|\.git|site-packages|__pycache__|vendor|third_party|migrations)/' \
  | grep -vE '\.(lock|map|min\.js)$|/(package-lock\.json|uv\.lock|poetry\.lock|yarn\.lock|pnpm-lock\.yaml)$' \
  > "$MANIFEST"

# Full reviews need more headroom than diffs (the agentic lanes read many files).
WR_TIMEOUT=${WR_TIMEOUT:-720}
```

**Scale guard**: if the manifest has more than ~150 files, warn the user and suggest narrowing to a `path`; instruct the lanes to surface only the highest-value findings rather than reviewing exhaustively. If the manifest is empty, stop.

## Phase 2: Pre-flight

Detect available lanes with `command -v` (`grok`, `qodercli`, `opencode`, `pi`) and build the active lane list. Note any skipped lanes for the final report. No per-lane configuration is required — each lane sets its model on the command line.

## Phase 3: Launch Parallel Reviews

Build the strict-format review prompt for the selected mode. The pipe-delimited format makes the free-form text output parseable.

**Diff mode prompt:**

```bash
read -r -d '' WR_PROMPT <<EOF
You are a meticulous code reviewer. Read the diff file at $BUNDLE and review ONLY those changes.
Read full files for context where needed, but report only issues in the diff.
$WR_FORMAT
EOF
```

**Full mode prompt** — firmer and manifest-anchored (this is what keeps the agentic lanes on task):

```bash
read -r -d '' WR_PROMPT <<EOF
You are a meticulous code reviewer performing a FULL codebase review (not a diff).
Review ONLY the files listed in the manifest at $MANIFEST (read them as needed). Do not review anything outside it.
Do NOT run git commands. Do NOT explore unrelated directories. Do NOT describe your plan, narrate your steps, or summarize your work.
Find the highest-value issues: logic bugs, security/auth/secret handling, error handling gaps, race conditions, performance, and correctness risks.
$WR_FORMAT
EOF
```

Both modes share the output contract:

```bash
read -r -d '' WR_FORMAT <<'EOF'
For EACH issue, output exactly one line, pipe-delimited, and NOTHING else:
SEVERITY | CATEGORY | file:line | description | CONFIDENCE
- SEVERITY: Critical | Warning | Suggestion
- CATEGORY: Logic | Security | Performance | Regression | Style | Other
- CONFIDENCE: High | Medium | Low
If there are no issues, output exactly: NO_ISSUES
Do not include headings, summaries, prose, code fences, or markdown — only the lines above.
EOF
```

Launch each available lane in the background, each with the mode's timeout, writing to its own output file. `timeout(1)` is GNU coreutils and does not exist on stock macOS, so resolve a portable wrapper first. The wrapper must be able to **SIGKILL** — some lane CLIs ignore softer signals like SIGALRM/SIGTERM:

```bash
wr_timeout() {
  if command -v timeout >/dev/null 2>&1; then timeout -k 10 "$WR_TIMEOUT" "$@"
  elif command -v gtimeout >/dev/null 2>&1; then gtimeout -k 10 "$WR_TIMEOUT" "$@"   # Homebrew coreutils on macOS
  else  # stock macOS: pure-shell watchdog; kill -9 because some CLIs ignore softer signals
    "$@" & local p=$!
    ( sleep "$WR_TIMEOUT"; kill -9 "$p" 2>/dev/null ) & local w=$!
    wait "$p"; local s=$?; kill "$w" 2>/dev/null; return "$s"
  fi
}
```

Every lane gets `< /dev/null`: under an orchestrator, stdin is an open pipe that never closes, and some CLIs block forever reading it. Lanes with a native working-directory flag use it; `pi` has no `--cwd`, so lane D runs in a subshell `cd`:

```bash
wr_timeout grok -p "$WR_PROMPT" -m grok-composer-2.5-fast --always-approve --cwd "${ROOT:-.}" < /dev/null \
  > "$WR_DIR/laneA.txt" 2>&1 & A=$!
wr_timeout qodercli -p --model "Qwen3.7-Max" --reasoning-effort max --dangerously-skip-permissions --cwd "${ROOT:-.}" "$WR_PROMPT" < /dev/null \
  > "$WR_DIR/laneB.txt" 2>&1 & B=$!
wr_timeout opencode run "$WR_PROMPT" --pure -m xiaomi/mimo-v2.5-pro --dir "${ROOT:-.}" --dangerously-skip-permissions -f "${BUNDLE:-$MANIFEST}" < /dev/null \
  > "$WR_DIR/laneC.txt" 2>&1 & C=$!
# Lane D: pi has no --cwd, so wrap in a subshell cd. The bundle/manifest is inlined
# via @ so diff mode needs no tool use; in full mode pi reads files itself.
( cd "${ROOT:-.}" && wr_timeout pi -p --provider tokenrouter --model MiniMax-M3 @"${BUNDLE:-$MANIFEST}" "$WR_PROMPT" < /dev/null \
  ) > "$WR_DIR/laneD.txt" 2>&1 & D=$!
wait "$A"; A_STATUS=$?
wait "$B"; B_STATUS=$?
wait "$C"; C_STATUS=$?
wait "$D"; D_STATUS=$?
```

(Only start lanes whose CLI was detected in Phase 2. `ROOT` is unset in diff mode — `${ROOT:-.}` keeps lanes in the current repo; bundle/manifest paths are absolute so lane D's subshell `cd` still resolves them. Wait only for the PIDs of lanes you started; do not use bare `wait`, because it can block on unrelated background jobs in the orchestrator shell. Record each lane's exit code: `0` = ok, `124` (or `137` if SIGKILL was needed) = timeout, other = failed.)

## Phase 4: Collect and Parse

For each lane output file:
1. **Strip wrappers**: remove markdown code fences (```` ``` ````), tool-error/log lines, and any preamble/narration prose. Lanes may wrap findings in a fence, prepend "Now I have enough context…", or emit stray log lines on stderr — discard all of it.
2. Keep only lines matching `SEVERITY | CATEGORY | file:line | description | CONFIDENCE`.
3. Treat `NO_ISSUES` (and a lane that produced only narration) as a clean/empty lane.
4. Normalize file paths (strip leading `./`).

Record per-lane status: ok / timeout / failed / skipped / empty.

## Phase 5: Consolidate (Vote-Weighted)

Build a normalized signature for each finding: `file:line:category` (fuzzy-match nearby line numbers and equivalent locations across lanes). Count how many lanes report each signature. **Always preserve each lane's original severity.**

| Agreement | Status | Icon |
|-----------|--------|------|
| ≥3 lanes report it | **Strong Consensus** | 🔴🔴 |
| 2 lanes report it | **Consensus** | 🔴 |
| 1 lane, High confidence | **Exclusive** | 🟠 |
| 1 lane, Medium/Low confidence | **Lower Confidence** | 🟡 |
| Same location, conflicting severity/assessment | **Divergent** | ⚠️ |

**Never auto-resolve divergences.** Show every lane's assessment with attribution and label it for human review.

## Phase 6: Output Final Report

```
## WideReview Summary  (<mode>: diff | full)
- Strong Consensus (3-4 lanes):  <count>
- Consensus (2 lanes):         <count>
- Exclusive (high conf):       <count>
- Lower Confidence:            <count>
- Divergent:                   <count>

### Lane status
| Lane | Model              | Status        | Findings |
|------|--------------------|---------------|----------|
| A    | Grok Composer 2.5  | ok/timeout/.. | <n>      |
| B    | Qwen3.7-Max        | ...           | <n>      |
| C    | OpenCode           | ...           | <n>      |
| D    | MiniMax-M3 (pi)    | ...           | <n>      |

- Lanes used: <k>/4
- Cost Level: Low (4 cheap models)

Recommendation: <prioritized next steps — consensus issues first>
```

Then list findings grouped by the buckets in Phase 5, each as:

```
<icon> [<Severity>] [Category] file:line   (agreement: <k>/4 lanes)
   Sources: <lanes that reported it>
   Problem: <description>
   Fix: <recommendation>
```

Finally, clean up: `rm -rf "$WR_DIR"`.

## Error Handling

- **A CLI is missing/unauthenticated** → skip that lane, note it in the report, continue.
- **A lane times out (`124`, or `137` if SIGKILL was needed) or errors** → mark it failed, continue with the rest. (Raise `WR_TIMEOUT` if a lane keeps timing out on large full-mode reviews.)
- **A lane returns only narration / no conforming lines** → mark it empty, continue.
- **All lanes fail/empty** → report failure and suggest the standard `/review` instead.
- **Divergence** → never auto-resolve; always surface both/all assessments for human review.
