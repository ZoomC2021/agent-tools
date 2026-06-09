# Widereview workflow

Wide fan-out code review across four independent cheap-model CLIs run in parallel.

## Purpose

Widereview runs four low-cost models on the same code changes simultaneously, then consolidates findings into a vote-weighted report. Where [ultrareview](ultrareview.md) favors depth (two premium models), widereview favors **breadth** — several independent reviewers at near-zero cost. The host agent acts as orchestrator only; it does not review the code itself.

## Modes

| Mode | Invocation | What is reviewed |
|------|-----------|------------------|
| Diff (default) | `/widereview` | Uncommitted changes (`git diff`) — fast, the common pre-commit case |
| Full | `/widereview --full [path]` | The entire application source, or just `path` — a whole-codebase audit |

Only Phase 1 (context gathering) and the lane prompt differ between modes; the parallel fan-out, parsing, vote-weighted consolidation, and reporting are identical.

## How it works

```
1. Gather context for the mode:
   - Diff: `git add -N .` (so untracked files appear) + shared git diff bundle
            (git status + git diff HEAD -U40 + git diff --cached -U40); timeout 480/lane
   - Full: deterministic file manifest via `git ls-files` (fallback find), stripping vendor/build
            noise (.venv, node_modules, dist, build, site-packages, __pycache__, vendor, lock files);
            optional path arg; scale guard at ~150 files; timeout 720/lane
2. Pre-flight:
   - Detect available lanes with `command -v` (no per-lane config required)
3. Launch parallel lanes (each with the mode's timeout, own output file):
   - Lane A: Grok Composer 2.5 (grok -p -m grok-composer-2.5-fast --always-approve --cwd <root>)
   - Lane B: Qwen3.7-Max       (qodercli -p --model "Qwen3.7-Max" --reasoning-effort max --dangerously-skip-permissions --cwd <root>)
   - Lane C: OpenCode / K2.6   (droid exec -m custom:OpenCode-0 --skip-permissions-unsafe --cwd <root>)
   - Lane D: MiMo v2.5 Pro     (cmd -p --model xiaomi/mimo-v2.5-pro --skip-onboarding -t; subshell cd <root>)
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
| A | `grok` (Grok) | `grok-composer-2.5-fast` | model default | n/a |
| B | `qodercli` (Qoder) | `Qwen3.7-Max` | max | `--reasoning-effort` flag |
| C | `droid exec` (Factory) | `custom:OpenCode-0` (MiMo v2.5 Pro) | n/a | router model |
| D | `cmd` (Command Code) | `xiaomi/mimo-v2.5-pro` | model default | n/a |

## Strict finding format

Each lane is given one prompt that forces a parseable, pipe-delimited line per issue:

```
SEVERITY | CATEGORY | file:line | description | CONFIDENCE
```

with `NO_ISSUES` for a clean lane. The parser must strip markdown code fences, preambles, and stray log/tool-error lines — some lanes wrap their findings in a ``` block, prepend a sentence, or emit stderr noise before the lines.

In **full mode** the prompt is additionally hardened and manifest-anchored: "review ONLY the files in the manifest; do NOT run git, do NOT explore unrelated directories, do NOT describe your plan or summarize your work." This keeps the agentic lanes on task instead of wandering the tree.

## Known lane behavior

- **Lane A (Grok Composer 2.5 via `grok`)** replaced the original deepseek-via-`cmd` lane, which was the slowest and timed out on full reviews. Grok is fast, supports native `--cwd`, and needs no effort pre-flight.
- **Lane D (MiMo v2.5 Pro via `cmd`)** returns `cmd` to the lineup with a faster model (mimo-v2.5-pro) and no effort pre-flight. `cmd` has no `--cwd`, so it runs in a subshell `cd`; bundle/manifest paths are absolute so reads still work.
- A review with only some lanes succeeding is still valuable — the lanes tend to cover complementary ground (e.g. one backend-heavy, one frontend-heavy).
- An `agy`/Gemini 3.5 Flash lane was trialled and **dropped**: it wandered (running `git status`, narrating steps, announcing its model) and produced no findings in both diff and full modes, even with the hardened prompt.

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
- One or more of: `grok`, `qodercli`, `droid`, `cmd` installed and authenticated
- Git repository (diff mode needs changes to review; full mode uses `git ls-files`, falling back to `find`)

## Secret hygiene

The OpenCode lane is backed by a custom model whose xiaomi API key is stored in plaintext in `~/.factory/settings.json`. The workflow references the model id `custom:OpenCode-0` only and must never read, print, or copy that settings file.

## When to use

Use for broad coverage and cheap second opinions. For deep, high-stakes review of critical changes, prefer [ultrareview](ultrareview.md).

## Not available for

Gemini CLI, Antigravity, Amp (these agents don't have the orchestration to run parallel reviews).

## Related workflows

- [Ultrareview](ultrareview.md) — Dual premium-model review (depth over breadth)
- [Review](review.md) — Standard single-model review
- [Deslop](deslop.md) — Principle-based quality audit
