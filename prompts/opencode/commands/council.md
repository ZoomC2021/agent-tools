---
description: Wide fan-out multi-model consultation across four model CLIs (Grok Composer 2.5 via grok, Cursor Grok 4.5 High via cursor-agent, GPT-5.6 Sol via codex, and Kimi K3 via cmd) on a single question, consolidated into a vote-weighted council report with explicit dissent. Use for non-review questions: architecture tradeoffs, technology choice, design stress-test, second opinions, "should I do X" decisions.
mode: subagent
---

# Council: Wide Fan-Out Multi-Model Consultation

Run a **four-model council in parallel** — `grok` (Grok Composer 2.5), `cursor-agent` (Cursor Grok 4.5 High), `codex` (GPT-5.6 Sol), and `cmd` (Kimi K3) — on a single question, then consolidate the answers into a vote-weighted report that surfaces consensus **and** dissent.

Council is the consultation analog of `widereview`. Same lanes, same parallel scaffolding, different prompt and output contract: instead of `SEVERITY | CATEGORY | file:line | description | CONFIDENCE`, each lane emits `POSITION | CONFIDENCE | KEY-REASONING | CAVEATS`.

💡 **When to use council vs widereview vs oracle**:
- `widereview` — review uncommitted changes or a codebase for **bugs/issues**.
- `council` — consult on a **question or decision** that is not a code review (architecture, tech choice, design tradeoff, "should I adopt X", second opinion on a plan).
- `oracle` — single deep-reasoning model when you want one focused answer rather than a vote.

The host agent is the **orchestrator only** — it gathers the question, launches the lanes, and consolidates results; it does not answer the question itself. Use the host harness's active or primary model for orchestration; do not select or override the orchestrator model.

## Lanes

| Lane | CLI | Model | Reasoning effort |
|------|-----|-------|------------------|
| A | `grok` | `grok-composer-2.5-fast` | model default |
| B | `cursor-agent` | `cursor-grok-4.5-high` | encoded in model variant |
| C | `codex exec` | `gpt-5.6-sol` | model default |
| D | `cmd` | `moonshotai/Kimi-K3` | model default |

Four independent harness/model combinations give diverse perspectives and make disagreement visible. Disagreement is the signal — never average it out.

## Prerequisites

Each lane is optional. Missing or unauthenticated CLIs are **skipped**, and the council proceeds with whatever is available (at least one lane is required).

- `grok` (Grok) — `command -v grok`
- `cursor-agent` (Cursor) — `command -v cursor-agent`
- `codex` (Codex) — `command -v codex`
- `cmd` (Command Code) — `command -v cmd`

⚠️ **Secret hygiene**: Reference the model ids `grok-composer-2.5-fast`, `cursor-grok-4.5-high`, `gpt-5.6-sol`, and `moonshotai/Kimi-K3` only — never read, print, or copy provider API keys or auth tokens from any lane's config.

## Phase 1: Capture the Question

The user's question is the entire input to the council. Collect it from the invocation arguments (everything after `/council`) or from the current conversation context if the user invoked `/council` bare with a question already on screen.

Write the question to a temp file so it is byte-identical across lanes and so long/multiline questions survive shell quoting:

```bash
C_DIR=$(mktemp -d)
QUESTION_FILE="$C_DIR/question.md"
cat > "$QUESTION_FILE" <<'EOF'
<paste the user's exact question here, preserving newlines and code fences>
EOF
C_TIMEOUT=${C_TIMEOUT:-360}
```

If the question is empty, report "No question provided to council" and stop. Do not invent a question.

**Scope guard**: if the question is longer than ~2 KB, warn the user that very long prompts can dilute lane focus and suggest tightening it. Do not refuse — just warn.

## Phase 2: Pre-flight

Detect available lanes with `command -v` (`grok`, `cursor-agent`, `codex`, `cmd`) and build the active lane list. Note any skipped lanes for the final report. No per-lane configuration is required — each lane sets its model on the command line.

## Phase 3: Launch Parallel Consultations

Build the strict-format consultation prompt. The pipe-delimited format makes the free-form text output parseable.

```bash
read -r -d '' C_PROMPT <<EOF
You are a member of a multi-model council consulted on a single question.
Read the question at $QUESTION_FILE and answer it directly.
Reason about tradeoffs, assumptions, and risks before committing to a position.
You may read files in the current repo for grounding if the question references code, but do not explore unrelated directories or run git commands.
Do NOT describe your plan, narrate your steps, or summarize your process — output only the answer line.
$C_FORMAT
EOF
```

Output contract (shared by all lanes):

```bash
read -r -d '' C_FORMAT <<'EOF'
Output exactly ONE line, pipe-delimited, and NOTHING else:
POSITION | CONFIDENCE | KEY-REASONING | CAVEATS
- POSITION: a short stance (<=12 words). Examples: "Adopt X", "Reject X", "Depends on Y", "X over Y", "Insufficient information", "Yes, with caveat Z".
- CONFIDENCE: High | Medium | Low
- KEY-REASONING: one or two sentences giving the core argument for your position.
- CAVEATS: assumptions, risks, or conditions that would change your position; write "none" if there are none.
If the question is unanswerable as written, set POSITION to "Insufficient information" and explain what is missing in KEY-REASONING.
Do not include headings, summaries, prose, code fences, or markdown — only the single line above.
EOF
```

Launch each available lane in the background, each with the timeout, writing to its own output file. `timeout(1)` is GNU coreutils and does not exist on stock macOS, so resolve a portable wrapper first. The wrapper must be able to **SIGKILL** — some lane CLIs ignore softer signals like SIGALRM/SIGTERM:

```bash
c_timeout() {
  if command -v timeout >/dev/null 2>&1; then timeout -k 10 "$C_TIMEOUT" "$@"
  elif command -v gtimeout >/dev/null 2>&1; then gtimeout -k 10 "$C_TIMEOUT" "$@"   # Homebrew coreutils on macOS
  else  # stock macOS: pure-shell watchdog; kill -9 because some CLIs ignore softer signals
    "$@" & local p=$!
    ( sleep "$C_TIMEOUT"; kill -9 "$p" 2>/dev/null ) & local w=$!
    wait "$p"; local s=$?; kill "$w" 2>/dev/null; return "$s"
  fi
}
```

Every lane gets `< /dev/null`: under an orchestrator, stdin is an open pipe that never closes, and some CLIs block forever reading it. Each lane uses its native working-directory option:

```bash
c_timeout grok -p "$C_PROMPT" -m grok-composer-2.5-fast --always-approve --cwd "${ROOT:-.}" < /dev/null \
  > "$C_DIR/laneA.txt" 2>&1 & A=$!
c_timeout cursor-agent -p --model cursor-grok-4.5-high --mode ask --trust --workspace "${ROOT:-.}" "$C_PROMPT" < /dev/null \
  > "$C_DIR/laneB.txt" 2>&1 & B=$!
c_timeout codex exec --ephemeral -s read-only --skip-git-repo-check -C "${ROOT:-.}" -m gpt-5.6-sol "$C_PROMPT" < /dev/null \
  > "$C_DIR/laneC.txt" 2>&1 & C=$!
( cd "${ROOT:-.}" && c_timeout cmd -p "$C_PROMPT" --model moonshotai/Kimi-K3 --permission-mode plan --max-turns 30 < /dev/null \
  ) > "$C_DIR/laneD.txt" 2>&1 & D=$!
wait "$A"; A_STATUS=$?
wait "$B"; B_STATUS=$?
wait "$C"; C_STATUS=$?
wait "$D"; D_STATUS=$?
```

(Only start lanes whose CLI was detected in Phase 2. `ROOT` is unset unless the user passed a subpath — `${ROOT:-.}` keeps lanes in the current repo; the question file path is absolute so lane D's subshell `cd` still resolves it. Wait only for the PIDs of lanes you started; do not use bare `wait`, because it can block on unrelated background jobs in the orchestrator shell. Record each lane's exit code: `0` = ok, `124` (or `137` if SIGKILL was needed) = timeout, other = failed.)

## Phase 4: Collect and Parse

For each lane output file:
1. **Strip wrappers**: remove markdown code fences (```` ``` ````), tool-error/log lines, and any preamble/narration prose. Lanes may wrap the answer in a fence, prepend "Let me think about this…", or emit stray log lines on stderr — discard all of it.
2. Keep only the first line matching `POSITION | CONFIDENCE | KEY-REASONING | CAVEATS` (split on `|` with at most 4 fields; trim whitespace on each field).
3. Treat a lane that produced only narration / no conforming line as an empty lane.
4. Preserve each lane's exact text for the final report — do not paraphrase positions.

Record per-lane status: ok / timeout / failed / skipped / empty.

## Phase 5: Consolidate (Vote-Weighted, Dissent-Preserving)

Normalize each position into a **stance signature**: lowercase, strip punctuation, collapse whitespace, drop filler tokens ("i think", "probably", "should"). Fuzzy-match stances that say the same thing with different wording (e.g. "adopt x" == "go with x" == "use x"). Count how many lanes hold each stance.

| Agreement | Status | Icon |
|-----------|--------|------|
| ≥3 lanes share a stance | **Strong Consensus** | 🟢🟢 |
| 2 lanes share a stance | **Consensus** | 🟢 |
| 1 lane, High confidence | **Exclusive** | 🔵 |
| 1 lane, Medium/Low confidence | **Lower Confidence** | ⚪ |
| ≥2 distinct stances with material disagreement | **Divergent** | ⚠️ |

**Never auto-resolve divergences.** A 2–2 split or a 3-way disagreement is the most valuable output the council can produce — surface every stance with attribution and label it for human decision. Do not pick a winner.

## Phase 6: Output Final Report

```
## Council Summary
- Strong Consensus (3-4 lanes):  <count>
- Consensus (2 lanes):           <count>
- Exclusive (high conf):         <count>
- Lower Confidence:              <count>
- Divergent:                     <count>

### Lane status
| Lane | Model                | Status        | Position |
|------|----------------------|---------------|----------|
| A    | Grok Composer 2.5    | ok/timeout/.. | <short>  |
| B    | Cursor Grok 4.5 High | ...           | <short>  |
| C    | GPT-5.6 Sol          | ...           | <short>  |
| D    | Kimi K3              | ...           | <short>  |

- Lanes used: <k>/4
- Question: <one-line summary of the question asked>

Verdict: <if Strong Consensus/Consensus exists, state it plainly. If Divergent or no majority, state "No majority — human decision required" and list the competing stances.>
```

Then list positions grouped by the buckets in Phase 5, each as:

```
<icon> [Confidence] <POSITION>   (agreement: <k>/4 lanes)
   Sources: <lanes that hold this stance>
   Reasoning: <KEY-REASONING from one representative lane, verbatim>
   Caveats: <CAVEATS, merged from the sources; dedupe identical caveats>
```

For **Divergent** buckets, additionally include every lane's full position line verbatim so the human can see the exact disagreement:

```
⚠️ Divergent — competing stances
   Lane A (Grok Composer 2.5, High): <verbatim position line>
   Lane C (GPT-5.6 Sol, Medium):     <verbatim position line>
   ...
```

Finally, clean up: `rm -rf "$C_DIR"`.

## Error Handling

- **A CLI is missing/unauthenticated** → skip that lane, note it in the report, continue.
- **A lane times out (`124`, or `137` if SIGKILL was needed) or errors** → mark it failed, continue with the rest. (Raise `C_TIMEOUT` if a lane keeps timing out on questions that require deep reasoning.)
- **A lane returns only narration / no conforming line** → mark it empty, continue.
- **All lanes fail/empty** → report failure and suggest using `/oracle` for a single-model deep-reasoning consultation instead.
- **Divergence** → never auto-resolve; always surface every stance for human decision. A 2–2 or 3-way split is the signal, not a failure.
- **Insufficient information from all lanes** → report that the question needs clarification and list what each lane said was missing.
