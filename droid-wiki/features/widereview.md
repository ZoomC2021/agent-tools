# Widereview workflow

Wide fan-out code review across four independent cheap-model CLIs run in parallel.

## Purpose

Widereview runs four low-cost models on the same code changes simultaneously, then consolidates findings into a vote-weighted report. Where [ultrareview](ultrareview.md) favors depth (two premium models), widereview favors **breadth** — many independent reviewers at near-zero cost. The host agent acts as orchestrator only; it does not review the code itself.

## Modes

| Mode | Invocation | What is reviewed |
|------|-----------|------------------|
| Diff (default) | `/widereview` | Uncommitted changes (`git diff`) — fast, the common pre-commit case |
| Full | `/widereview --full [path]` | The entire application source, or just `path` — a whole-codebase audit |

Only Phase 1 (context gathering) and the lane prompt differ between modes; the parallel fan-out, parsing, vote-weighted consolidation, and reporting are identical.

## How it works

```
1. Gather context for the mode:
   - Diff: shared git diff bundle (git status + git diff HEAD -U40 + git diff --cached -U40); timeout 480/lane
   - Full: deterministic file manifest via `git ls-files` (fallback find), stripping vendor/build
            noise (.venv, node_modules, dist, build, site-packages, __pycache__, vendor, lock files);
            optional path arg; scale guard at ~150 files; timeout 720/lane
2. Pre-flight:
   - jq-merge reasoningEffort["deepseek/deepseek-v4-pro"]="max" into ~/.commandcode/config.json
   - Detect available lanes with `command -v`
3. Launch parallel lanes (each with timeout 480, own output file):
   - Lane A: deepseek-v4-pro   (cmd -p --model deepseek/deepseek-v4-pro --skip-onboarding -t)
   - Lane B: Qwen3.7-Max       (qodercli -p --model "Qwen3.7-Max" --reasoning-effort max --dangerously-skip-permissions)
   - Lane C: FirePass / K2.6   (droid exec -m custom:FirePass-0 --skip-permissions-unsafe)
   - Lane D: Gemini 3.5 Flash  (agy -p --model "Gemini 3.5 Flash (High)" --dangerously-skip-permissions)
4. Collect exit codes (0=ok, 124=timeout, other=failed); parse pipe-delimited findings, discard narration
5. Consolidate by vote count:
   - 🔴🔴 Strong Consensus: 3-4 lanes agree
   - 🔴 Consensus: 2 lanes agree
   - 🟠 Exclusive: 1 lane, high confidence
   - 🟡 Lower Confidence: 1 lane, medium/low confidence
   - ⚠️ Divergent: same location, conflicting assessment — human review recommended
6. Never auto-resolves conflicts — all perspectives shown
7. Graceful fallback: skip missing/failed lanes, require at least one
```

## Lanes

| Lane | CLI | Model | Reasoning effort | Effort mechanism |
|------|-----|-------|------------------|------------------|
| A | `cmd` (Command Code) | `deepseek/deepseek-v4-pro` | max | `~/.commandcode/config.json` |
| B | `qodercli` (Qoder) | `Qwen3.7-Max` | max | `--reasoning-effort` flag |
| C | `droid exec` (Factory) | `custom:FirePass-0` (Kimi K2.6 router) | n/a | router model |
| D | `agy` | `Gemini 3.5 Flash (High)` | high | baked into model name |

## Strict finding format

Each lane is given one prompt that forces a parseable, pipe-delimited line per issue:

```
SEVERITY | CATEGORY | file:line | description | CONFIDENCE
```

with `NO_ISSUES` for a clean lane. This makes the free-form text lanes (A and D) parseable and lets the orchestrator strip agentic narration. The parser must also strip markdown code fences and preambles — some lanes wrap their findings in a ``` block or prepend a sentence before the lines.

In **full mode** the prompt is additionally hardened and manifest-anchored: "review ONLY the files in the manifest; do NOT run git, do NOT explore unrelated directories, do NOT describe your plan or summarize your work." Without this anchor the `agy`/Gemini lane tends to wander (running `git status`, narrating steps) and produce no findings.

## Known lane behavior

- **Lane A (deepseek via `cmd`)** is the slowest — it can exceed the diff timeout on a full review. Raise `WR_TIMEOUT` if it keeps timing out (`124`).
- **Lane D (agy / Gemini 3.5 Flash)** is the most prone to wandering; the hardened full-mode prompt mitigates this, but treat it as best-effort.
- A review with only **2 of 4 lanes** succeeding is still valuable — the lanes tend to cover complementary ground (e.g. one backend-heavy, one frontend-heavy).

## Consolidation rules

| Finding type | Criteria | Action |
|--------------|----------|--------|
| Strong Consensus | Found by 3-4 lanes | Highest priority, very likely a real issue |
| Consensus | Found by 2 lanes | High priority |
| Exclusive | 1 lane, high confidence | Include with lane attribution |
| Lower Confidence | 1 lane, medium/low confidence | Include for consideration |
| Divergent | Lanes disagree on severity/nature | Flag for human review |

Original per-lane severities are always preserved; agreement is additional metadata.

## Usage

### OpenCode
```
/widereview              # diff mode (uncommitted changes)
/widereview --full       # full-codebase audit
/widereview --full src   # full audit scoped to a subpath
```

### Requirements
- One or more of: `cmd`, `qodercli`, `droid`, `agy` installed and authenticated
- `jq` (for the cmd effort pre-flight)
- Git repository (diff mode needs changes to review; full mode uses `git ls-files`, falling back to `find`)

## Secret hygiene

The FirePass lane is backed by a custom model whose Fireworks API key is stored in plaintext in `~/.factory/settings.json`. The workflow references the model id `custom:FirePass-0` only and must never read, print, or copy that settings file.

## When to use

Use for broad coverage and cheap second opinions. For deep, high-stakes review of critical changes, prefer [ultrareview](ultrareview.md).

## Not available for

Gemini CLI, Antigravity, Amp (these agents don't have the orchestration to run parallel reviews).

## Related workflows

- [Ultrareview](ultrareview.md) — Dual premium-model review (depth over breadth)
- [Review](review.md) — Standard single-model review
- [Deslop](deslop.md) — Principle-based quality audit
