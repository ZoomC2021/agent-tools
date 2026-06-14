# OpenCode Worker Eval Results

Living reference for worker model comparisons.
Last updated: 2026-06-14.

## Matrix Results (both explore + general agents set to same model)

| Harness | Provider | Model | Score | agent-def | fail-tests | add-helper | debug-fix | spec-comp | state-mach |
|---------|----------|-------|-------|-----------|------------|------------|-----------|-----------|------------|
| opencode | xiaomi | **mimo-v2.5** | **6/6** | ✓ 31s | ✓ 14s | ✓ 10s | ✓ 13s | ✓ 177s | ✓ 76s |
| opencode | xiaomi | **mimo-v2.5-pro** | **6/6** | ✓ 26s | ✓ 22s | ✓ 25s | ✓ 22s | ✓ 268s | ✓ 211s |
| opencode | tokenrouter | **kimi-k2.7-code** | **6/6** | ✓ 19s | ✓ 20s | ✓ 17s | ✓ 20s | ✓ 197s | ✓ 149s |
| opencode | tokenrouter | **deepseek-v4-pro** | **6/6** | ✓ 36s | ✓ 20s | ✓ 34s | ✓ 40s | ✓ 118s | ✓ 137s |
| opencode | tokenrouter | MiniMax-M3 | 5/6 | ✓ 37s | ✓ 37s | ✓ 38s | ✓ 31s | ✗ 23/28 | ✓ 202s |
| cmd | tokenrouter | MiniMax-M3 | 6/6 | REVIEW | REVIEW | ✓ pass 3 | ✓ pass 3 | ✓ pass | ✓ pass 2 |
| opencode | tokenrouter | deepseek-v4-flash | 5/6 | ✓ 38s | ✓ 27s | ✓ 69s | ✗ 18/21 | ✓ 232s | ✓ 186s |
| cmd | tokenrouter | deepseek-v4-flash | 6/6 | REVIEW | REVIEW | ✓ pass 3 | ✓ pass 3 | ✓ pass | ✓ pass 2 |
| opencode | tokenrouter | glm-5.1 | 4/6 | ✓ 34s | ✓ 32s | ✓ 20s | ✗ 14/21 | ✗ 20/28 | ✓ 140s |
| opencode | nvidia | glm-5.1 | 3/6 | ✓ 18s | ✗ TO | ✓ 10s | ✓ 11s | ✗ TO | ✗ 12/20 |
| opencode | nousresearch | step-3.7-flash | 3/6 | ✓ 18s | ✗ 21/22 | ✓ 16s | ✓ 23s | ✗ 26/28 | ✗ 18/20 |
| opencode | nousresearch | nemotron-3-ultra | 2/6 | ✓ 50s | ✗ 14/22 | ✗ 9/18 | ✓ 64s | ✗ 20/28 | ✗ 16/20 |
| opencode | zenmux | kimi-k2.7-code-free (9 RPM) | 0/4 | ✗ TO | ✗ TO | ✗ TO | ✗ TO | — | — |

### Harness Comparison (cmd vs opencode)

| Provider | Model | opencode Score | cmd Score | opencode Time | cmd Time | Speedup |
|----------|-------|----------------|-----------|---------------|----------|---------|
| tokenrouter | MiniMax-M3 | 5/6 | 6/6 | 607s | 455s | **25% faster** |
| tokenrouter | deepseek-v4-flash | 5/6 | 6/6 | 636s | 517s | **19% faster** |

**cmd is faster and more accurate for both models.** Per-scenario opencode durations:

| Scenario | deepseek-v4-flash | minimax-m3 |
|----------|-------------------|------------|
| explore-agent-definition | 38s | 37s |
| explore-failing-tests | 27s | 37s |
| general-add-helper | 69s | 38s |
| general-debug-minimal-fix | 84s | 31s |
| general-workflow-spec-compliance | 232s | 262s |
| general-workflow-state-machine | 186s | 202s |
| **Total** | **636s** | **607s** |

cmd doesn't report per-scenario durations; total wall-clock measured at 517s and 455s respectively.

### Provider Notes

| Provider | RPM Limit | Notes |
|----------|-----------|-------|
| xiaomi | ~60 | Direct Xiaomi API |
| tokenrouter | ~60+ | Aggregator, many models |
| nvidia | 40 | NVIDIA NIM, lower limits |
| nousresearch | ~60 | Nous Research (aggregates nvidia, stepfun, etc.) |
| zenmux | 9 | Leak-bucket proxy, throttle-bound on multi-turn |

### Speed Ranking (opencode only, light tasks: add-helper + debug-fix average)

| Provider | Model | Avg Light (s) | Notes |
|----------|-------|---------------|-------|
| xiaomi | mimo-v2.5 | 11.5 | Fastest overall, 6/6 |
| tokenrouter | kimi-k2.7-code | 18.5 | Fast, clean, 6/6 |
| xiaomi | mimo-v2.5-pro | 23.5 | Solid, 6/6 |
| tokenrouter | deepseek-v4-pro | 37.0 | Best spec-compliance time (118s) |
| tokenrouter | minimax-m3 | 34.5 | Fails spec-compliance on opencode |
| tokenrouter | deepseek-v4-flash | 76.5 | 6× slower than v4-pro |
| tokenrouter | glm-5.1 | 10.5 | Fast on easy, fails debug-fix + spec |
| nousresearch | step-3.7-flash | 19.5 | Fails explore + hard tasks |
| nousresearch | nemotron-3-ultra | 4.0 | Very slow on hard tasks |
| zenmux | kimi-k2.7-code-free | TO | Throttle-bound |

## Per-Scenario Details (opencode)

### Light Scenarios

**agent-definition** (read-only discovery — find agent registration in config)

| Provider | Model | Result | Time |
|----------|-------|--------|------|
| xiaomi | mimo-v2.5 | ✓ | 31s |
| xiaomi | mimo-v2.5-pro | ✓ | 26s |
| tokenrouter | kimi-k2.7-code | ✓ | 19s |
| tokenrouter | deepseek-v4-pro | ✓ | 36s |
| tokenrouter | deepseek-v4-flash | ✓ | 38s |
| tokenrouter | MiniMax-M3 | ✓ | 37s |
| tokenrouter | glm-5.1 | ✓ | 34s |
| nvidia | glm-5.1 | ✓ | 18s |
| nousresearch | step-3.7-flash | ✓ | 18s |
| nousresearch | nemotron-3-ultra | ✓ | 50s |
| zenmux | kimi-k2.7-code-free | ✗ | TO |

**failing-tests** (read-only discovery — find test failures and explain root cause)

| Provider | Model | Result | Time |
|----------|-------|--------|------|
| xiaomi | mimo-v2.5 | ✓ | 14s |
| xiaomi | mimo-v2.5-pro | ✓ | 22s |
| tokenrouter | kimi-k2.7-code | ✓ | 20s |
| tokenrouter | deepseek-v4-pro | ✓ | 20s |
| tokenrouter | deepseek-v4-flash | ✓ | 27s |
| tokenrouter | MiniMax-M3 | ✓ | 37s |
| tokenrouter | glm-5.1 | ✓ | 32s |
| nvidia | glm-5.1 | ✗ | TO |
| nousresearch | step-3.7-flash | ✗ 21/22 | 12s |
| nousresearch | nemotron-3-ultra | ✗ 14/22 | 34s |
| zenmux | kimi-k2.7-code-free | ✗ | TO |

**add-helper** (implementation — add a helper function to an existing module)

| Provider | Model | Result | Time |
|----------|-------|--------|------|
| xiaomi | mimo-v2.5 | ✓ | 10s |
| xiaomi | mimo-v2.5-pro | ✓ | 25s |
| tokenrouter | kimi-k2.7-code | ✓ | 17s |
| tokenrouter | deepseek-v4-pro | ✓ | 34s |
| tokenrouter | deepseek-v4-flash | ✓ | 69s |
| tokenrouter | MiniMax-M3 | ✓ | 38s |
| tokenrouter | glm-5.1 | ✓ | 20s |
| nvidia | glm-5.1 | ✓ | 10s |
| nousresearch | step-3.7-flash | ✓ | 16s |
| nousresearch | nemotron-3-ultra | ✗ 9/18 | 4s |
| zenmux | kimi-k2.7-code-free | ✗ | TO |

**debug-minimal-fix** (implementation — fix a failing test with minimal change)

| Provider | Model | Result | Time |
|----------|-------|--------|------|
| xiaomi | mimo-v2.5 | ✓ | 13s |
| xiaomi | mimo-v2.5-pro | ✓ | 22s |
| tokenrouter | kimi-k2.7-code | ✓ | 20s |
| tokenrouter | deepseek-v4-pro | ✓ | 40s |
| tokenrouter | deepseek-v4-flash | ✗ 18/21 | 84s |
| tokenrouter | MiniMax-M3 | ✓ | 31s |
| tokenrouter | glm-5.1 | ✗ 14/21 | 7s |
| nvidia | glm-5.1 | ✓ | 11s |
| nousresearch | step-3.7-flash | ✓ | 23s |
| nousresearch | nemotron-3-ultra | ✓ | 64s |
| zenmux | kimi-k2.7-code-free | ✗ | TO |

### Hard Scenarios

**workflow-spec-compliance** (implementation — build a feature to spec with 28 assertions)

| Provider | Model | Result | Time |
|----------|-------|--------|------|
| xiaomi | mimo-v2.5 | ✓ 28/28 | 177s |
| xiaomi | mimo-v2.5-pro | ✓ 28/28 | 268s |
| tokenrouter | kimi-k2.7-code | ✓ 28/28 | 197s |
| tokenrouter | deepseek-v4-pro | ✓ 28/28 | 118s |
| tokenrouter | deepseek-v4-flash | ✓ 28/28 | 232s |
| tokenrouter | MiniMax-M3 | ✗ 23/28 | 262s |
| tokenrouter | glm-5.1 | ✗ 20/28 | 282s |
| nvidia | glm-5.1 | ✗ | TO |
| nousresearch | step-3.7-flash | ✗ 26/28 | 241s |
| nousresearch | nemotron-3-ultra | ✗ 20/28 | 10s |
| zenmux | kimi-k2.7-code-free | — | — |

**workflow-state-machine** (implementation — implement a multi-step state machine with 20 assertions)

| Provider | Model | Result | Time |
|----------|-------|--------|------|
| xiaomi | mimo-v2.5 | ✓ 20/20 | 76s |
| xiaomi | mimo-v2.5-pro | ✓ 20/20 | 211s |
| tokenrouter | kimi-k2.7-code | ✓ 20/20 | 149s |
| tokenrouter | deepseek-v4-pro | ✓ 20/20 | 137s |
| tokenrouter | deepseek-v4-flash | ✓ 20/20 | 186s |
| tokenrouter | MiniMax-M3 | ✓ 20/20 | 202s |
| tokenrouter | glm-5.1 | ✓ 20/20 | 140s |
| nvidia | glm-5.1 | ✗ 12/20 | 30s |
| nousresearch | step-3.7-flash | ✗ 18/20 | 114s |
| nousresearch | nemotron-3-ultra | ✗ 16/20 | 291s |
| zenmux | kimi-k2.7-code-free | — | — |

## Methodology

### opencode harness
- **Harness**: `prompts/opencode/bin/opencode-eval` runs `opencode run --format json --agent <agent>` in isolated workspace copies
- **Matrix variants**: Both `worker-explore` and `worker-general` set to the same model via `configOverrides` + `promptFrontmatterOverrides`
- **Timeouts**: Light scenarios 90s (default); hard scenarios 300s. Runs exceeding timeout are clock-killed (marked ✗ TO)
- **Assertions**: `outputRegex` patterns check final assistant message content. npm-test checks use `(#|ℹ) fail 0\b` and `(#|ℹ) pass [1-9][0-9]*\b` (node --test emits `ℹ` not `#`)
- **MiniMax-M3 `<think>` strip**: `worker-routing-guard.js` strips raw `<think>` blocks from M3 output via `tool.execute.after` hook. Hook is active for all models (no-op for non-M3)

### cmd harness
- **Harness**: `prompts/opencode/bin/cmd-eval` runs `cmd -p <prompt> --yolo --max-turns 30 --model <model>` in isolated workspace copies
- **Evaluation**: Mechanical checks only (fileContains, workspaceCommands, exitCode). `forbiddenTools`/`requiredSubagents` marked as unevaluable (REVIEW)
- **Pass criteria**: `pass: true` when all evaluable checks pass and no unevaluable checks exist. `pass: null` (REVIEW) when unevaluable checks exist but all evaluable ones pass. `pass: false` when any evaluable check fails.
- **Output**: Results in `evals/cmd-out/` mirroring `evals/out/` structure

### Provider notes
- **ZenMux 9-RPM proxy**: Leak-bucket throttle at 9 RPM (~1 req/6.7s). Viable for few-turn tasks; multi-turn hard scenarios are throttle-bound regardless of timeout. The unthrottled `kimi-k2.7-code` row captures the model's actual capability
- **glm-5.1 provider switch**: Moved from nvidia (40 RPM) to tokenrouter (60+ RPM) which resolved state-machine timeouts

## Key Findings

1. **mimo-v2.5 is the clear winner**: 6/6, fastest on hard tasks (76s state-machine), zero issues. Best cost/speed/quality trade-off.
2. **deepseek-v4-pro is the best runner-up**: 6/6, fastest spec-compliance (118s), but 3-4× slower on light tasks.
3. **kimi-k2.7-code is excellent**: 6/6, very fast on light tasks (17-20s), solid on hard.
4. **mimo-v2.5-pro is solid but slow**: 6/6 but 2-3× slower than mimo-v2.5 on everything. Pro tax doesn't help here.
5. **cmd improves MiniMax-M3 and deepseek-v4-flash**: Both go from 5/6 to 6/6 under cmd. MiniMax-M3 passes spec-compliance; deepseek-v4-flash passes debug-fix and state-machine. The `--yolo --max-turns 30` flags and cmd's agent architecture give models more room to work.
6. **MiniMax-M3 is not viable on opencode**: Slower than alternatives, fails spec-compliance (23/28), leaks `<think>` blocks.
7. **deepseek-v4-flash is slow on opencode**: 69s on add-helper (7× slower than mimo-v2.5). Hard tasks pass but at 2× the time.
8. **glm-5.1 (tokenrouter)**: 4/6, fast on light tasks but fails debug-fix (14/21) and spec-compliance (20/28). State-machine passes after provider switch from nvidia.
9. **step-3.7-flash (nousresearch)**: 3/6, fast on light tasks but fails explore-failing-tests (21/22) and both hard scenarios. Not production-ready.
10. **nemotron-3-ultra (nousresearch)**: 2/6, worst performer. Fails add-helper in 4s, spec-compliance in 10s. Only passes agent-def and debug-fix.
11. **ZenMux free tier is throttle-bound**: 0/4 on light scenarios at 9 RPM. Viable only for very few-turn tasks.

## Adding New Models

1. Add model definition to `prompts/opencode/opencode.json.example` under the appropriate provider
2. Add `matrix-*` variant to `prompts/opencode/evals/variants.json` following the existing pattern
3. Run opencode: `prompts/opencode/bin/opencode-eval run --variants matrix-<model-name> --scenarios "subagent-worker-*" --timeout 300000`
4. Run cmd: `prompts/opencode/bin/cmd-eval run --variants matrix-<model-name> --scenarios "subagent-worker-*"`
5. Collect results: `prompts/opencode/bin/opencode-eval report <run-dir>` or `cmd-eval report <run-dir>`
6. Update this file with the new rows
