---
name: oracle
description: "Consult a read-only GPT-5.6 Sol reasoning agent for difficult debugging, architecture, review, or optimization decisions."
---

# Oracle

Consult GPT-5.6 Sol through a fresh, read-only `codex exec` process for hard
software-engineering judgments. The oracle may inspect the repository but
cannot change it. Its answer is advisory: validate it against the code before
implementing anything.

## When to Use

Use Oracle for:

- Subtle bugs that remain unclear after focused investigation
- Architecture, migration, or API-boundary tradeoffs
- Risky reviews where correctness, security, data loss, or concurrency matters
- Stress-testing a complex implementation plan
- Comparing several plausible approaches

Do not use it for codebase discovery, routine edits, simple lookups, or obvious
bugs. Investigate those directly first.

## Prerequisites

- The `codex` CLI is installed and authenticated (`codex --version`).
- The Codex configuration provides access to `gpt-5.6-sol`.

If Codex is unavailable, report that the consultation could not run rather than
substituting a different model silently.

## Workflow

1. **Investigate first.** Establish the relevant ownership path, current
   behavior, and concrete uncertainty. Do not ask Oracle to perform broad
   discovery that a targeted read or search can answer.

2. **Write a focused task.** Give Oracle enough direction to inspect the right
   evidence without pasting repository files into the prompt:

   ```markdown
   INTENT: [behavior or outcome that must be preserved]

   DECISION / QUESTION: [the exact judgment needed]

   RELEVANT FILES:
   - @path/to/file: [why it matters]
   - @path/to/test: [why it matters]

   CURRENT EVIDENCE:
   - [observed behavior, reproduction, test failure, or prior attempt]

   CONSTRAINTS:
   - [compatibility, rollout, performance, or scope limits]

   REVIEW INSTRUCTIONS:
   - [where to begin, such as "start with git diff"]
   - Focus on: [specific risks]
   - Ignore: [explicit non-goals]

   OUTPUT: [the useful shape: recommendation, ranked risks, alternatives,
   smallest fixes, unverified assumptions, etc.]
   ```

   Prefer exact paths and symbols. Include log excerpts or external facts that
   are not present in the repository, but do not duplicate readable source
   files. Never include secrets, credentials, PII, or customer data.

3. **Run the oracle from the repository root.** Use a scratch file so quoting
   cannot alter the task. The child process is ephemeral and read-only:

   ```bash
   ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
   ORACLE_DIR="$(mktemp -d)"
   cat > "$ORACLE_DIR/prompt.md" <<'EOF'
   <focused task here>
   EOF

   if command -v timeout >/dev/null 2>&1; then
     ORACLE_TIMEOUT=(timeout 900)
   elif command -v gtimeout >/dev/null 2>&1; then
     ORACLE_TIMEOUT=(gtimeout 900)
   else
     ORACLE_TIMEOUT=()
   fi

   "${ORACLE_TIMEOUT[@]}" codex exec \
     --ephemeral \
     -s read-only \
     --skip-git-repo-check \
     -C "$ROOT" \
     -m gpt-5.6-sol \
     -c 'model_reasoning_effort="high"' \
     --output-last-message "$ORACLE_DIR/oracle.txt" \
     "$(cat "$ORACLE_DIR/prompt.md")" \
     < /dev/null > "$ORACLE_DIR/codex.log" 2>&1
   status=$?

   if [ "$status" -ne 0 ] || [ ! -s "$ORACLE_DIR/oracle.txt" ]; then
     cat "$ORACLE_DIR/codex.log" >&2
     rm -rf "$ORACLE_DIR"
     [ "$status" -ne 0 ] && exit "$status"
     exit 1
   fi

   cat "$ORACLE_DIR/oracle.txt"
   rm -rf "$ORACLE_DIR"
   ```

   `timeout` is used on Linux and Homebrew's `gtimeout` on macOS when present;
   otherwise Codex runs without an outer deadline. A timeout, non-zero status,
   or empty final response is a failed consultation. Do not treat diagnostic
   output as an Oracle answer or guess what Oracle would have said.

4. **Apply independent judgment.** Check each material claim against the
   repository. Reject advice that conflicts with local evidence or the stated
   intent. If changes are requested, implement them in the parent session and
   run the narrowest meaningful verification.

## Oracle Inspection Rules

The task should tell Oracle to:

- Start with the named files or current diff, then read only surrounding code
  needed to verify relevant invariants.
- Use read-only commands for inspection; never modify files, dependencies, git
  state, or external systems.
- Distinguish observed facts from hypotheses and state unverified assumptions.
- Prioritize high-confidence, behavior-affecting findings over style comments.
- Recommend the smallest safe fix and explain meaningful tradeoffs.
- Ask for one narrow missing artifact only when it would materially change the
  answer; never request broad repository rediscovery.

## Reporting

Return the substance, not a transcript: the recommendation, evidence-backed
findings, tradeoffs or plan changes that matter, and unresolved assumptions.
State explicitly when Oracle found no issue or when the consultation failed.
