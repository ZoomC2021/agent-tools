# Oracle

Consult an external deep-reasoning oracle — **GPT-5.5 (low reasoning effort)** driven via the `codex` CLI — when stuck on a hard problem. You bundle a compact, self-contained context package and hand it to the oracle for a second opinion; the oracle runs read-only and cannot change your repo.

Question / problem: **$ARGUMENTS**

Use this when the user asks to consult an oracle, wants a second opinion from a stronger reasoning model, or escalates a complex engineering question.

## When to Use

- **Stuck on complex bugs**: root cause still unclear after initial investigation
- **Architecture decisions**: tradeoffs and patterns need expert guidance
- **Risky code review**: a second opinion on critical or risky changes
- **Refactoring uncertainty**: unsure about approach or consequences
- **Cross-domain problems**: issues spanning multiple technologies or systems
- **Performance optimization**: bottleneck analysis and solutions

Do **not** use it for simple lookups, formatting changes, or questions answerable by reading one obvious file.

## Prerequisites

- The `codex` CLI installed and authenticated (`codex --version`).
- Access to the `gpt-5.5` model through your Codex configuration (ChatGPT plan auth or a configured provider / `OPENAI_API_KEY`).

If `codex` is missing, tell the user to install it (`npm install -g @openai/codex`) and authenticate (`codex login`), then retry.

## Workflow

1. **Decide whether the oracle is appropriate** (see *When to Use*). If it is trivial, just answer directly instead.

2. **Prepare a compact context bundle.** Write a single self-contained prompt:
   - The exact question or decision point.
   - 3–8 highest-signal files or excerpts with precise paths and why each matters — quote the relevant lines rather than pointing at huge files.
   - Prior attempts, current hypotheses, constraints, failing commands, and validation/log output.
   - Exclude secrets, credentials, PII, and broad unrelated files.

   Structure it like:

   ```markdown
   GOAL: [specific question]

   CONTEXT:
   - [facts]
   - [prior attempts]
   - [constraints]

   FILES / EXCERPTS:
   - `path/to/file`: [why it matters, with the relevant excerpt]

   VALIDATION / LOGS:
   - [command output or failure]

   REQUESTED OUTPUT:
   - Assessment
   - Findings (with location references)
   - Recommendations with rationale and tradeoffs
   - Prioritized next steps
   ```

3. **Invoke the oracle.** Write the prompt to a scratch file and run `codex` read-only with GPT-5.5 at low reasoning effort. It runs inside the repo with read-only access, so it can verify referenced files, but treat the bundle as the authoritative working set.

   ```bash
   ORACLE_DIR="$(mktemp -d)"
   cat > "$ORACLE_DIR/prompt.md" <<'EOF'
   <your bundled prompt here>
   EOF

   timeout 900 codex exec \
     -s read-only \
     --skip-git-repo-check \
     --model gpt-5.5 \
     -c 'model_reasoning_effort="low"' \
     "$(cat "$ORACLE_DIR/prompt.md")" \
     < /dev/null > "$ORACLE_DIR/oracle.txt" 2>&1
   echo "exit: $?"; cat "$ORACLE_DIR/oracle.txt"
   ```

   Notes:
   - `-s read-only` keeps the oracle from editing anything; it is purely advisory.
   - `< /dev/null` prevents the CLI from blocking on stdin.
   - Bump the `timeout` for very large bundles; treat a timeout/non-zero exit as a failed consultation and report it rather than guessing.

4. **Apply judgment after the oracle responds.**
   - Summarize the oracle's key findings for the user.
   - Validate every recommendation against the actual codebase before applying it.
   - Do **not** blindly implement suggestions that conflict with local evidence — say so and explain.

## Guidelines

### DO
- Ask specific, focused questions and include the exact files/excerpts that matter.
- Summarize prior investigation so the oracle does not redo it.
- Use the oracle for genuinely hard problems, then verify its output.

### DO NOT
- Send secrets, credentials, or PII.
- Hand the oracle a broad "look around the repo" task instead of a curated bundle.
- Apply recommendations without validating them locally.

### STOP IF
- The consultation would expose sensitive data.
- The issue is trivial or better resolved by direct investigation.
- Cost/latency clearly outweighs the problem's impact.

## Output Format

The oracle returns structured analysis: **Assessment**, **Findings**, **Recommendations** (with rationale and tradeoffs), and **Prioritized Next Steps**. Relay the substance to the user along with your plan for acting on it.
