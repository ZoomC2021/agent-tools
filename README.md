# Agent Tools

Custom prompts, skills, and workflows for AI coding agents. Provides consistent developer workflows across multiple coding assistants.

## Workflows Included

| Workflow | Description |
|----------|-------------|
| **frontier-worker** | *(Claude Code & Codex)* Orchestrate a task: delegate **all** exploration and coding to the `cmd` CLI (MiniMax-M3-Free), then dual-review every change with a clean-context host subagent **and** an independent `agy` reviewer (Gemini 3.1 Pro High), looping fixes until clean |
| **refactor** | Analyze codebase for refactoring opportunities, prioritize by severity/effort |
| **review** | Review uncommitted changes for bugs, regressions, and improvements |
| **ultrareview** | Parallel dual-model review using GPT 5.5 + Gemini 3.1 Pro Preview simultaneously, with helper-managed Gemini bundling/chunking/retries *(Not available: Gemini, Antigravity, Amp)* |
| **ultrareview-lite** | Parallel dual-model review using MiMo v2.5 Pro + Gemini 3 Flash Preview simultaneously, with helper-managed Gemini bundling/chunking/retries *(Not available: Gemini, Antigravity, Amp)* |
| **widereview** | Wide fan-out review across four cheap-model CLIs (Grok Composer 2.5, Qwen3.7-Max, MiMo v2.5 Pro via OpenCode, MiniMax-M3 via pi) run in parallel, then consolidated into a vote-weighted report. Diff mode (default) or full-codebase mode (`--full`) *(Not available: Gemini, Antigravity, Amp)* |
| **pr-reviewer** | Fetch PR comments, summarize issues, address them, update PR |
| **pr-reviewer-only** | Fetch PR comments, summarize issues, generate implementation prompt for another agent |
| **create-pr** | Create PR with auto-generated title and description |
| **cp** | Commit current work with meaningful boundaries and push to origin |
| **deslop** | Analyze code for quality issues using established software engineering principles |
| **predict-issues** | Analyze codebase to predict potential problems before they impact the project |
| **oracle** | Consult a deep-reasoning oracle subagent for complex bugs, architecture tradeoffs, and risky reviews |
| **github-librarian** | Read-only remote GitHub code research on default-branch snapshots |
| **docs-research** | Research official documentation and external API behavior using web sources |
| **walkthrough** | Explain local architecture and code flow with evidence-backed walkthroughs |

## Frontier Worker (Claude Code & Codex)

A flexible, CLI-driven variant of the OpenCode `frontier-worker` orchestrator. Here the **host CLI (Claude Code or Codex) is the orchestrator**: it plans and routes but delegates **all** investigation and coding to the `cmd` CLI, then reviews every change with two independent reviewers in parallel. Because neither `cmd` nor `agy` exposes ACP or an SDK, both are driven one-shot via their `--print` modes.

Invoke with `/frontier-worker <task>` (Claude Code) or the `frontier-worker` skill (Codex).

```
┌──────────────────────────────────────────────────────────────┐
│  Orchestrator = host CLI (Claude Code / Codex)               │
│  • Plans & sequences  • Writes briefs  • Consolidates review │
│  • Never reads/edits project files itself                    │
└───────────┬───────────────────────┬──────────────────────────┘
            │ explore + code        │ dual review (parallel)
   ┌────────▼─────────┐    ┌─────────▼──────────┬───────────────┐
   │ cmd  (MiniMax-   │    │ clean-context      │ agy           │
   │ M3-Free)         │    │ subagent           │ (Gemini 3.1   │
   │ • plan mode =    │    │ (Task tool /       │  Pro High)    │
   │   read-only      │    │  Codex multi-agent)│ independent   │
   │   exploration    │    │ reviews the diff   │ reviewer      │
   │ • --yolo = edits │    └────────────────────┴───────────────┘
   └──────────────────┘
```

| Role | CLI / mechanism | Model |
|------|-----------------|-------|
| Orchestrator | host (Claude Code / Codex) | — |
| Explorer (read-only) | `cmd -p --permission-mode plan` | `MiniMaxAI/MiniMax-M3-Free` |
| Worker (coding) | `cmd -p --yolo` | `MiniMaxAI/MiniMax-M3-Free` |
| Reviewer A (clean context) | Claude `Task` subagent / Codex multi-agent (`codex exec` fallback) | host default |
| Reviewer B (independent) | `agy -p` | `Gemini 3.1 Pro (High)` |

**Flexible knobs** (env overrides): `FW_WORKER_MODEL`, `FW_REVIEW_MODEL`, `FW_TIMEOUT`, `FW_MAX_TURNS`, `FW_MAX_ITERS`.

**Notes**: `cmd` is required; `agy` is optional (missing → host-subagent review only). `agy` must run inside a directory listed in `trustedWorkspaces` (`~/.gemini/antigravity-cli/settings.json`) or it blocks on a trust prompt. Never print or copy provider API keys — reference model ids only.

## Opencode GPT-5.5 Worker Setup (Primary Agent Architecture)

This repository includes a sophisticated agent architecture for OpenCode using GPT-5.5 as the orchestrator and model-swappable worker subagents for execution and discovery.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  GPT-5.5 Worker Orchestrator                         │
│  • Plans and sequences work                                  │
│  • Makes routing decisions                                    │
│  • Delegates to specialized subagents                       │
└──────────────────────┬────────────────────────────────────────┘
                       │
   ┌───────────┬──────────────┬──────────────────┬──────────────┐
   │           │              │                  │              │
┌──▼────────┐ ┌▼───────────┐ ┌▼────────────────┐ ┌▼────────────┐
│ mimo-     │ │ mimo-      │ │ github-         │ │ docs-       │
│ general   │ │ explore    │ │ librarian       │ │ research    │
│ execution │ │ local find │ │ remote GitHub   │ │ official    │
└───────────┘ └────────────┘ └─────────────────┘ └─────────────┘
   │               │                 │                  │
┌──▼────────┐ ┌────▼─────┐ ┌────────▼──────┐ ┌─────────▼──────┐
│walkthrough│ │ review   │ │ deslop        │ │ pr-reviewer    │
│ diagrams  │ │ local QA │ │ code quality  │ │ PR fixes       │
└───────────┘ └──────────┘ └───────────────┘ └────────────────┘
                            │                  │
                      ┌─────▼─────┐      ┌────▼────┐
                      │ create-pr │      │ oracle  │
                      │ workflow  │      │ deep    │
                      └───────────┘      │ reasoning│
                                         └─────────┘
```

### Deterministic Routing

The orchestrator uses keyword-based deterministic routing:

| Trigger | Keywords | Agent Selected |
|---------|----------|----------------|
| PR creation | "create PR", "pull request" | **create-pr** |
| PR feedback | "PR comment", "address PR" | **pr-reviewer** |
| Code audit | "audit", "code quality" | **deslop** |
| Local review | "review changes", "uncommitted" | **review** |
| Remote repo research | GitHub URL, `owner/repo`, "reference implementation" | **github-librarian** |
| Official docs research | "official docs", "migration guide", "API docs" | **docs-research** |
| Local walkthrough | "walk me through", "diagram", "architecture" | **walkthrough** |
| Local discovery | "find", "search", "explore" | **worker-explore** |
| Implementation | "implement", "fix", "refactor" | **worker-general** |

### Orchestrator Safety Gates

Before routing, the orchestrator applies these safety checks (in order):

| Gate | Purpose |
|------|---------|
| **Intent Verbalization** | State routing reasoning out loud so users can catch misroutes before work begins |
| **Turn-Local Intent Reset** | Reclassify intent from the CURRENT message only — never carry "implementation mode" from prior turns |
| **Context-Completion Gate** | Block `spec-compiler` until an explicit implementation verb + concrete scope + no pending research |
| **Consecutive Failure Protocol** | After 2 No-Go results → auto-escalate to Oracle; after 3 → STOP, revert, report to user |

### Mission-Aware Implementation Workflow

For implementation/debugging/refactoring tasks, the orchestrator uses one of two paths:

1. **Standard flow** for small/medium single-milestone work:
   1. **PHASE 0 (optional): docs-research / github-librarian** → Gather official docs or upstream reference code first
   2. **PHASE 1: spec-compiler** → Compile Execution Contract (scope, risks, success criteria)
   3. **PHASE 2: worker-general** → Execute implementation based on contract
   4. **PHASE 3: quick-validator** → Run validation tests/checks
   5. **PHASE 4 (optional): change-auditor** → Deep audit for high-risk areas

2. **Mission flow** for long-running, multi-step work:
   1. **PHASE 0 (optional): docs-research / github-librarian** → Gather external references first when needed
   2. **PHASE 1: mission-scrutiny** → Front-load scrutiny, decompose into milestones, set validation cadence
   3. **PHASE 2 (loop per milestone): spec-compiler → worker-general → milestone-validator**
   4. **PHASE 3: quick-validator** → Final end-to-end validation across all milestones
   5. **PHASE 4 (optional): change-auditor** → Deep audit for high-risk milestone or final changes

### Directory Layout

```
~/.config/opencode/
├── opencode.json              # Main configuration (see example)
├── bin/                       # Helper scripts (e.g. opencode-gh-librarian,
│                              #   zenmux-throttle-proxy)
├── agent/                     # Primary agent definitions
│   ├── frontier-worker.md       # Orchestrator (routing logic)
│   ├── worker-general.md       # Execution worker
│   ├── worker-explore.md       # Local read-only discovery
│   ├── github-librarian.md   # Remote GitHub research
│   ├── docs-research.md      # Official docs + API research
│   ├── walkthrough.md        # Architecture walkthroughs + diagrams
│   └── oracle.md             # Deep reasoning (GPT-5.5)
└── commands/                  # Workflow prompts
    ├── review.md
    ├── ultrareview.md
    ├── ultrareview-lite.md
    ├── widereview.md
    ├── deslop.md
    ├── mission-scrutiny.md
    ├── milestone-validator.md
    ├── pr-reviewer.md
    ├── create-pr.md
    ├── cp.md
    ├── spec-compiler.md
    ├── quick-validator.md
    ├── change-auditor.md
    ├── plan-review.md
    └── refactor.md
```

### Subagent Reference

| Subagent | Purpose | Model | Reasoning Effort |
|----------|---------|-------|------------------|
| **frontier-worker** | Primary orchestrator (plans, routes, delegates) | GPT-5.5 | High |
| **worker-general** | Implementation, debugging, refactoring execution | MiniMax-M3 | — |
| **worker-explore** | Local read-only codebase discovery and search | MiniMax-M3 | — |
| **github-librarian** | Remote GitHub research (default branches, history) | MiMo v2.5 Pro | — |
| **docs-research** | Official docs, API behavior, release notes | MiMo v2.5 Pro | — |
| **walkthrough** | Architecture walkthroughs with Mermaid diagrams | MiMo v2.5 Pro | — |
| **oracle** | Deep reasoning for complex problems | GPT-5.5 | **High** |
| **spec-compiler** | Compile Execution Contracts before implementation | MiMo v2.5 Pro | — |
| **plan-review** | Binary validation of Execution Contracts | MiMo v2.5 Pro | — |
| **quick-validator** | Fast validation of implementation output | MiMo v2.5 Pro | — |
| **mission-scrutiny** | Front-load scrutiny, milestone planning | GPT-5.5 | — |
| **milestone-validator** | Validate each milestone before advancing | GPT-5.5 | — |
| **change-auditor** | Deep audit for security, breaking changes | GPT-5.5 | **High** |
| **review** | Review uncommitted changes | GPT-5.5 | **High** |
| **ultrareview** | Parallel dual-model review (GPT 5.5 + Gemini 3.1 Pro Preview) | MiMo v2.5 Pro | — |
| **ultrareview-lite** | Parallel dual-model review (MiMo v2.5 Pro + Gemini 3 Flash Preview) | MiMo v2.5 Pro | — |
| **widereview** | Wide fan-out review across 4 cheap-model CLIs (Grok Composer 2.5 + Qwen3.7-Max + MiMo v2.5 Pro via OpenCode + MiniMax-M3 via pi); diff or full-codebase (`--full`) | MiMo v2.5 Pro | — |
| **deslop** | Code quality audit against principles | MiMo v2.5 Pro | — |
| **imagegen-grok** | Generate/edit images with xAI Grok Imagine | xAI Grok Imagine Image Quality | — |
| **imagegen-google** | Generate/edit images with Google Nano Banana Pro | Gemini 3 Pro Image Preview | — |
| **pr-reviewer** | Fetch PR comments and apply fixes | MiMo v2.5 Pro | — |
| **pr-reviewer-only** | Fetch PR comments, produce implementation prompt | MiMo v2.5 Pro | — |
| **create-pr** | Create PR with auto-generated title/description | MiMo v2.5 Pro | — |
| **cp** | Commit current work with meaningful boundaries and push to origin | MiMo v2.5 | — |
| **refactor** | Analyze and prioritize refactoring opportunities | MiMo v2.5 Pro | — |

### ⚠️ Security Warning

**NEVER commit your `opencode.json` with real API keys to version control.**

- Use environment variables: `OPENCODE_XIAOMI_API_KEY`
- Or keep the config file in a secure location with `apiKey: "YOUR_KEY_HERE"`
- The example file includes placeholder warnings to help prevent accidental commits

### Reference Example

A local reference setup uses:
- Xiaomi MiMo v2.5 Pro for build mode and subagents
- GPT-5.5 for the orchestrator (plan mode)
- Specialized subagents for local discovery, remote GitHub research, docs research, architecture walkthroughs, and execution

See `prompts/opencode/opencode.json.example` for the full configuration structure.

### Rate-Limited Providers (Throttle Proxy)

Some providers enforce a hard requests-per-minute cap. ZenMux's free `moonshotai/kimi-k2.7-code-free` (10 RPM) can stop serving when you exceed it, while Nvidia NIM returns retryable `429 Too Many Requests` around its 40 RPM cap. OpenCode has no native RPM control, so bursts (agentic tool loops, parallel fan-out skills like `widereview`) can fail a whole scenario.

`prompts/opencode/bin/zenmux-throttle-proxy` is a dependency-free Node streaming reverse proxy that enforces provider caps at one local chokepoint. One process serves independent per-provider queues: `/zenmux/...` defaults to 9 RPM, `/nvidia/...` defaults to 40 RPM, and old unprefixed ZenMux routes still work. Callers that arrive too fast **wait** in the proxy instead of failing. SSE streaming and the `Authorization` header pass through unchanged (your API keys stay in OpenCode config).

Run it (targets should stay **below** real caps for margin):

```bash
# Defaults:
#   /zenmux -> https://zenmux.ai/api/v1 at 9 RPM
#   /nvidia -> https://integrate.api.nvidia.com/v1 at 40 RPM
prompts/opencode/bin/zenmux-throttle-proxy
```

Then point provider `baseURL`s at the provider-specific routes (no trailing `/api/v1` — the proxy prepends each upstream base path):

```json
"zenmux": {
  "options": {
    "apiKey": "{env:ZENMUX_API_KEY}",
    "baseURL": "http://127.0.0.1:8787/zenmux"
  }
},
"nvidia": {
  "options": {
    "apiKey": "{env:NVIDIA_API_KEY}",
    "baseURL": "http://127.0.0.1:8787/nvidia"
  }
}
```

Config is via env vars: `ZENMUX_PROXY_PORT` (8787), `ZENMUX_PROXY_HOST` (127.0.0.1), `ZENMUX_UPSTREAM` (`https://zenmux.ai/api/v1`), `NVIDIA_UPSTREAM` (`https://integrate.api.nvidia.com/v1`), `ZENMUX_RPM` (9), `NVIDIA_RPM` (40), `ZENMUX_CONCURRENCY` / `NVIDIA_CONCURRENCY` (1), `ZENMUX_QUEUE_MAX` / `NVIDIA_QUEUE_MAX` (0 = unbounded), and per-provider `*_UPSTREAM_TIMEOUT_MS` (600000). `GET /healthz` reports live per-provider state without consuming a slot. If Nvidia still returns `429`, the proxy forwards that response and pauses only the Nvidia lane according to `Retry-After` before releasing queued Nvidia requests.

Notes:
- The shipped `opencode.json.example` points providers at upstreams directly — switch a provider to the proxy **only on machines where you run the proxy**, otherwise that model will fail.
- For Pi, use `scripts/pi-zenmux.sh [pi args...]` (or local alias `pi-zenmux`). It starts/reuses the proxy, creates a temporary Pi config with `zenmux.baseUrl` set to `http://127.0.0.1:8787/zenmux`, and launches `pi --provider zenmux --model z-ai/glm-5.2-free` by default without mutating `~/.pi/agent/models.json`.
- Throttling at one process can only bound RPM if **all** traffic for that provider funnels through it. Multiple providers can share this one proxy process because each provider has its own queue and timer.
- Tested by `tests/zenmux-throttle-proxy.test.js` (`node tests/zenmux-throttle-proxy.test.js`).

## Supported Agents

| Agent | Type | Prompt Location |
|-------|------|-----------------|
| [Claude Code](https://claude.ai) | CLI | `~/.claude/commands/` |
| [Codex](https://github.com/openai/codex) | CLI | `~/.codex/skills/` |
| [OpenCode](https://opencode.ai) | CLI | `~/.config/opencode/commands/` |
| [Pi](https://pi.dev) | CLI | `~/.pi/agent/prompts/` |
| [Warp](https://www.warp.dev) | CLI/Editor | `~/.warp/workflows/` or `${XDG_DATA_HOME:-$HOME/.local/share}/warp-terminal/workflows/` or `%APPDATA%\warp\Warp\data\workflows\` |
| [Antigravity](https://antigravity.dev) | Editor | `~/.antigravity/prompts/` or `~/Library/.../Antigravity/User/prompts/` |
| [agy](https://antigravity.dev) | CLI | `~/.gemini/antigravity-cli/skills/` |
| [Copilot CLI](https://githubnext.com/projects/copilot-cli) | CLI | `~/.copilot/agents/` |
| [Amp](https://ampcode.com) | CLI/Editor | `~/.config/agents/skills/` |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | CLI | `~/.gemini/skills/` |
| [Grok CLI (grok)](https://x.ai) | CLI | `~/.grok/skills/` |
| [Droid](https://factory.ai) | CLI/Editor | `~/.factory/droids/` and `~/.factory/skills/` |
| [Kilo Code](https://kilocode.com) | CLI | `~/.kilocode/prompts/` |
| [Cursor](https://cursor.com) | Editor | `~/.cursor/commands/` |
| [Cline](https://cline.bot) | Editor | `~/Documents/Cline/Rules/` |
| [cmd](https://commandcode.ai) | CLI | `~/.commandcode/skills/` |
| [Windsurf](https://codeium.com/windsurf) | Editor | `~/.codeium/windsurf/skills/` |

### Codex ccapi Provider

The Codex installer also adds a persistent custom provider for the ccapi.us OpenAI-compatible endpoint in `~/.codex/config.toml`:

```toml
[model_providers.ccapi]
name = "ccapi"
base_url = "https://api-direct.ccapi.us/v1"
env_key = "CCAPI_API_KEY"
wire_api = "responses"
```

Codex's model picker changes only the model name, not the provider, so provider-specific entries such as `ccapi/gpt-5.5` are not supported. Launch with the ccapi profile first; then selecting `gpt-5.5` or `gpt-5.4` in the normal picker routes that model through ccapi:

```bash
export CCAPI_API_KEY=sk-...
codex --profile ccapi
```

For one-off full-access sessions without installing the profile, use `scripts/codex-ccapi.sh` with `--model gpt-5.5` or `--model gpt-5.4`.

## Quick Install

### All Agents

```bash
git clone https://github.com/YOUR_USERNAME/agent-tools.git
cd agent-tools
./scripts/install.sh
```

### Specific Agents

```bash
./scripts/install.sh claude codex amp warp
```

Available options: `claude`, `codex`, `opencode`, `pi`, `warp`, `antigravity`, `agy`, `copilot-cli`, `cmd`, `grok`, `amp`, `gemini`, `droid`, `kilocode`, `cursor`, `cline`, `windsurf`

## Manual Installation

### macOS

<details>
<summary>Claude Code</summary>

```bash
mkdir -p ~/.claude/commands
cp prompts/claude/*.md ~/.claude/commands/
```
</details>

<details>
<summary>Codex</summary>

```bash
for file in prompts/codex/*.md; do
  skill_name="$(basename "$file" .md)"
  mkdir -p "$HOME/.codex/skills/$skill_name"
  cp "$file" "$HOME/.codex/skills/$skill_name/SKILL.md"
done

cat >> ~/.codex/config.toml <<'EOF'

[model_providers.ccapi]
name = "ccapi"
base_url = "https://api-direct.ccapi.us/v1"
env_key = "CCAPI_API_KEY"
wire_api = "responses"
EOF

cat > ~/.codex/ccapi.config.toml <<'EOF'
model_provider = "ccapi"
model = "gpt-5.5"
EOF
```
</details>

<details>
<summary>OpenCode (GPT-5.5 Worker Architecture)</summary>

```bash
# Create directories
mkdir -p ~/.config/opencode/commands
mkdir -p ~/.config/opencode/agent
mkdir -p ~/.config/opencode/bin

# Copy workflow prompts to commands/
for f in prompts/opencode/commands/review.md prompts/opencode/commands/deslop.md \
         prompts/opencode/commands/mission-scrutiny.md prompts/opencode/commands/milestone-validator.md \
         prompts/opencode/commands/pr-reviewer.md prompts/opencode/commands/create-pr.md \
         prompts/opencode/commands/cp.md \
         prompts/opencode/commands/spec-compiler.md prompts/opencode/commands/quick-validator.md \
         prompts/opencode/commands/change-auditor.md prompts/opencode/commands/ultrareview.md \
         prompts/opencode/commands/ultrareview-lite.md prompts/opencode/commands/widereview.md \
         prompts/opencode/commands/refactor.md prompts/opencode/commands/plan-review.md \
         prompts/opencode/commands/pr-reviewer-only.md; do
  [ -f "$f" ] && cp "$f" ~/.config/opencode/commands/
done

# Copy agent definitions to agent/
for f in prompts/opencode/agent/frontier-worker.md \
         prompts/opencode/agent/worker-general.md prompts/opencode/agent/worker-explore.md \
         prompts/opencode/agent/github-librarian.md prompts/opencode/agent/docs-research.md \
         prompts/opencode/agent/walkthrough.md prompts/opencode/agent/oracle.md; do
  [ -f "$f" ] && cp "$f" ~/.config/opencode/agent/
done

# Copy helper scripts and Gemini prompt assets used by subagents
cp prompts/opencode/bin/* ~/.config/opencode/bin/
chmod +x ~/.config/opencode/bin/*

# Copy and edit config (⚠️ NEVER commit with real API key)
cp prompts/opencode/opencode.json.example ~/.config/opencode/opencode.json
```

**⚠️ Security Warning**: Edit `~/.config/opencode/opencode.json` and replace `YOUR_XIAOMI_API_KEY_HERE` with your actual API key. **Do not commit this file.**

**Note**: `github-librarian` requires `gh` to be installed and authenticated. `docs-research` works best when `websearch` is available, which OpenCode enables when using the OpenCode provider or when `OPENCODE_ENABLE_EXA=1` is set.

See [Opencode GPT-5.5 Worker Setup](#opencode-gpt-55-worker-setup-primary-agent-architecture) for architecture details.
</details>

<details>
<summary>Pi</summary>

```bash
mkdir -p ~/.pi/agent/prompts
cp prompts/pi/*.md ~/.pi/agent/prompts/
```
</details>

<details>
<summary>Warp</summary>

```bash
mkdir -p ~/.warp/workflows
cp prompts/warp/*.yaml ~/.warp/workflows/
```

Open Warp Command Palette or Workflow Search, select the workflow, and run it in Agent Mode.
</details>

<details>
<summary>Antigravity</summary>

```bash
mkdir -p ~/Library/Application\ Support/Antigravity/User/prompts
cp prompts/antigravity/*.md ~/Library/Application\ Support/Antigravity/User/prompts/
```
</details>

<details>
<summary>agy (Antigravity CLI)</summary>

```bash
for skill_dir in prompts/agy/*/; do
  skill_name=$(basename "$skill_dir")
  mkdir -p ~/.gemini/antigravity-cli/skills/$skill_name
  cp -r "$skill_dir"* ~/.gemini/antigravity-cli/skills/$skill_name/
done
```
</details>

<details>
<summary>Copilot CLI</summary>

```bash
mkdir -p ~/.copilot/agents
cp prompts/copilot-cli/*.md ~/.copilot/agents/
# Rename files to .agent.md format
for f in ~/.copilot/agents/*.md; do mv "$f" "${f%.md}.agent.md"; done
```
</details>

<details>
<summary>Amp</summary>

```bash
mkdir -p ~/.config/agents/skills
cp -r prompts/amp/* ~/.config/agents/skills/
```
</details>

<details>
<summary>Gemini CLI</summary>

```bash
for skill_dir in prompts/gemini/*/; do
  gemini skills install "$skill_dir" --scope user --consent
done
```
</details>

<details>
<summary>Grok CLI (grok)</summary>

```bash
for skill_dir in prompts/grok/*/; do
  skill_name=$(basename "$skill_dir")
  mkdir -p ~/.grok/skills/$skill_name
  cp -r "$skill_dir"* ~/.grok/skills/$skill_name/
done
```
</details>

<details>
<summary>Droid</summary>

```bash
mkdir -p ~/.factory/droids ~/.factory/skills ~/.config/opencode/bin
cp prompts/droid/droids/*.md ~/.factory/droids/
cp -r prompts/droid/skills/* ~/.factory/skills/
cp prompts/opencode/bin/opencode-gh-librarian ~/.config/opencode/bin/
chmod +x ~/.config/opencode/bin/opencode-gh-librarian
```

**Droids:** `oracle` (deep reasoning), `gemini-3-1-pro-reviewer` (Gemini 3.1 Pro read-only review), `github-librarian` (remote GitHub research), `docs-research` (official docs/API research), `walkthrough` (architecture walkthroughs with Mermaid diagrams)

**Skills:** `oracle`, `pr-reviewer`, `pr-reviewer-only`, `predict-issues`, `ultrareview`, `widereview`

The shipped `oracle` droid uses Factory's built-in GPT-5.5 with `reasoningEffort: high`. For BYOK, change `~/.factory/droids/oracle.md` to `model: custom:<configured-model-name>`. A ChatGPT Plus/Pro browser subscription is not a CLI/API credential for Droid.
</details>

<details>
<summary>Kilo Code</summary>

```bash
mkdir -p ~/.kilocode/prompts
cp prompts/kilocode/*.md ~/.kilocode/prompts/
```
</details>

<details>
<summary>Cursor</summary>

```bash
mkdir -p ~/.cursor/commands
cp prompts/cursor/*.md ~/.cursor/commands/
```
</details>

<details>
<summary>Cline</summary>

```bash
mkdir -p ~/Documents/Cline/Rules
cp prompts/cline/*.md ~/Documents/Cline/Rules/
```
</details>

<details>
<summary>cmd (Command Code)</summary>

```bash
for skill_dir in prompts/cmd/*/; do
  skill_name=$(basename "$skill_dir")
  mkdir -p ~/.commandcode/skills/$skill_name
  cp -r "$skill_dir"* ~/.commandcode/skills/$skill_name/
done
```
</details>

<details>
<summary>Windsurf</summary>

```bash
for skill_dir in prompts/windsurf/*/; do
  skill_name=$(basename "$skill_dir")
  mkdir -p ~/.codeium/windsurf/skills/$skill_name
  cp "$skill_dir"* ~/.codeium/windsurf/skills/$skill_name/
done
```
</details>

### Ubuntu/Linux

<details>
<summary>Claude Code</summary>

```bash
mkdir -p ~/.claude/commands
cp prompts/claude/*.md ~/.claude/commands/
```
</details>

<details>
<summary>Codex</summary>

```bash
for file in prompts/codex/*.md; do
  skill_name="$(basename "$file" .md)"
  mkdir -p "$HOME/.codex/skills/$skill_name"
  cp "$file" "$HOME/.codex/skills/$skill_name/SKILL.md"
done

cat >> ~/.codex/config.toml <<'EOF'

[model_providers.ccapi]
name = "ccapi"
base_url = "https://api-direct.ccapi.us/v1"
env_key = "CCAPI_API_KEY"
wire_api = "responses"
EOF

cat > ~/.codex/ccapi.config.toml <<'EOF'
model_provider = "ccapi"
model = "gpt-5.5"
EOF
```
</details>

<details>
<summary>OpenCode (GPT-5.5 Worker Architecture)</summary>

```bash
# Create directories
mkdir -p ~/.config/opencode/commands
mkdir -p ~/.config/opencode/agent
mkdir -p ~/.config/opencode/bin

# Copy workflow prompts to commands/
for f in prompts/opencode/commands/review.md prompts/opencode/commands/deslop.md \
         prompts/opencode/commands/mission-scrutiny.md prompts/opencode/commands/milestone-validator.md \
         prompts/opencode/commands/pr-reviewer.md prompts/opencode/commands/create-pr.md \
         prompts/opencode/commands/cp.md \
         prompts/opencode/commands/spec-compiler.md prompts/opencode/commands/quick-validator.md \
         prompts/opencode/commands/change-auditor.md prompts/opencode/commands/ultrareview.md \
         prompts/opencode/commands/ultrareview-lite.md prompts/opencode/commands/widereview.md \
         prompts/opencode/commands/refactor.md prompts/opencode/commands/plan-review.md \
         prompts/opencode/commands/pr-reviewer-only.md; do
  [ -f "$f" ] && cp "$f" ~/.config/opencode/commands/
done

# Copy agent definitions to agent/
for f in prompts/opencode/agent/frontier-worker.md \
         prompts/opencode/agent/worker-general.md prompts/opencode/agent/worker-explore.md \
         prompts/opencode/agent/github-librarian.md prompts/opencode/agent/docs-research.md \
         prompts/opencode/agent/walkthrough.md prompts/opencode/agent/oracle.md; do
  [ -f "$f" ] && cp "$f" ~/.config/opencode/agent/
done

# Copy helper scripts and Gemini prompt assets used by subagents
cp prompts/opencode/bin/* ~/.config/opencode/bin/
chmod +x ~/.config/opencode/bin/*

# Copy and edit config (⚠️ NEVER commit with real API key)
cp prompts/opencode/opencode.json.example ~/.config/opencode/opencode.json
```

**⚠️ Security Warning**: Edit `~/.config/opencode/opencode.json` and replace `YOUR_XIAOMI_API_KEY_HERE` with your actual API key. **Do not commit this file.**

**Note**: `github-librarian` requires `gh` to be installed and authenticated. `docs-research` works best when `websearch` is available, which OpenCode enables when using the OpenCode provider or when `OPENCODE_ENABLE_EXA=1` is set.

See [Opencode GPT-5.5 Worker Setup](#opencode-gpt-55-worker-setup-primary-agent-architecture) for architecture details.
</details>

<details>
<summary>Pi</summary>

```bash
mkdir -p ~/.pi/agent/prompts
cp prompts/pi/*.md ~/.pi/agent/prompts/
```
</details>

<details>
<summary>Warp</summary>

```bash
mkdir -p ${XDG_DATA_HOME:-$HOME/.local/share}/warp-terminal/workflows
cp prompts/warp/*.yaml ${XDG_DATA_HOME:-$HOME/.local/share}/warp-terminal/workflows/
```

Open Warp Command Palette or Workflow Search, select the workflow, and run it in Agent Mode.
</details>

<details>
<summary>Antigravity</summary>

```bash
mkdir -p ~/.antigravity/prompts
cp prompts/antigravity/*.md ~/.antigravity/prompts/
```
</details>

<details>
<summary>agy (Antigravity CLI)</summary>

```bash
for skill_dir in prompts/agy/*/; do
  skill_name=$(basename "$skill_dir")
  mkdir -p ~/.gemini/antigravity-cli/skills/$skill_name
  cp -r "$skill_dir"* ~/.gemini/antigravity-cli/skills/$skill_name/
done
```
</details>

<details>
<summary>Copilot CLI</summary>

```bash
mkdir -p ~/.copilot/agents
cp prompts/copilot-cli/*.md ~/.copilot/agents/
for f in ~/.copilot/agents/*.md; do mv "$f" "${f%.md}.agent.md"; done
```
</details>

<details>
<summary>Amp</summary>

```bash
mkdir -p ~/.config/agents/skills
cp -r prompts/amp/* ~/.config/agents/skills/
```
</details>

<details>
<summary>Gemini CLI</summary>

```bash
for skill_dir in prompts/gemini/*/; do
  gemini skills install "$skill_dir" --scope user --consent
done
```
</details>

<details>
<summary>Grok CLI (grok)</summary>

```bash
for skill_dir in prompts/grok/*/; do
  skill_name=$(basename "$skill_dir")
  mkdir -p ~/.grok/skills/$skill_name
  cp -r "$skill_dir"* ~/.grok/skills/$skill_name/
done
```
</details>

<details>
<summary>Droid</summary>

```bash
mkdir -p ~/.factory/droids ~/.factory/skills ~/.config/opencode/bin
cp prompts/droid/droids/*.md ~/.factory/droids/
cp -r prompts/droid/skills/* ~/.factory/skills/
cp prompts/opencode/bin/opencode-gh-librarian ~/.config/opencode/bin/
chmod +x ~/.config/opencode/bin/opencode-gh-librarian
```

**Droids:** `oracle` (deep reasoning), `gemini-3-1-pro-reviewer` (Gemini 3.1 Pro read-only review), `github-librarian` (remote GitHub research), `docs-research` (official docs/API research), `walkthrough` (architecture walkthroughs with Mermaid diagrams)

**Skills:** `oracle`, `pr-reviewer`, `pr-reviewer-only`, `predict-issues`, `ultrareview`, `widereview`

The shipped `oracle` droid uses Factory's built-in GPT-5.5 with `reasoningEffort: high`. For BYOK, change `~/.factory/droids/oracle.md` to `model: custom:<configured-model-name>`. A ChatGPT Plus/Pro browser subscription is not a CLI/API credential for Droid.
</details>

<details>
<summary>Kilo Code</summary>

```bash
mkdir -p ~/.kilocode/prompts
cp prompts/kilocode/*.md ~/.kilocode/prompts/
```
</details>

<details>
<summary>Cursor</summary>

```bash
mkdir -p ~/.cursor/commands
cp prompts/cursor/*.md ~/.cursor/commands/
```
</details>

<details>
<summary>Cline</summary>

```bash
mkdir -p ~/Documents/Cline/Rules
cp prompts/cline/*.md ~/Documents/Cline/Rules/
```
</details>

<details>
<summary>cmd (Command Code)</summary>

```bash
for skill_dir in prompts/cmd/*/; do
  skill_name=$(basename "$skill_dir")
  mkdir -p ~/.commandcode/skills/$skill_name
  cp -r "$skill_dir"* ~/.commandcode/skills/$skill_name/
done
```
</details>

<details>
<summary>Windsurf</summary>

```bash
for skill_dir in prompts/windsurf/*/; do
  skill_name=$(basename "$skill_dir")
  mkdir -p ~/.codeium/windsurf/skills/$skill_name
  cp "$skill_dir"* ~/.codeium/windsurf/skills/$skill_name/
done
```
</details>

## Workflow Details

### refactor

Analyzes your codebase for refactoring opportunities:

1. **Gathers context**: High-churn files, TODO/FIXME markers, large files
2. **Detects issues**: Code duplication, long functions, god classes, dead code, deep nesting
3. **Assesses severity**: 🔴 High | 🟠 Medium | 🟡 Low
4. **Calculates priority**: `Severity × (1/Effort)`
5. **Reports quick wins**: High severity + low effort items first

### review

Reviews uncommitted changes:

1. **Gets changes**: `git diff HEAD`, staged changes
2. **Checks for issues**: Logic errors, edge cases, type safety, security
3. **Checks for regressions**: Breaking API changes, removed functionality
4. **Optimizes**: Finds redundant code, duplicate logic, performance issues
5. **Fixes simple issues** automatically (≤5 straightforward fixes)

### ultrareview

⚠️ **Uses 2 high-tier models simultaneously** — use for critical reviews only.

Runs parallel code reviews using **GPT 5.5** (via OpenCode) AND **Gemini 3.1 Pro Preview** (via Gemini CLI) simultaneously, then consolidates:

1. **Launch parallel reviews**: Both models review the same changes concurrently
2. **Consolidate findings**:
   - 🔴 **Consensus Critical**: Issues found by BOTH models
   - 🟠 **Model Exclusive**: Issues found by only one model with high confidence
   - 🟡 **Lower Confidence**: Findings with medium/low confidence
   - ⚠️ **Divergent Assessments**: Models disagree — human review recommended
3. **Never auto-resolves conflicts**: Both perspectives shown when models disagree
4. **Graceful fallback**: If one model fails, returns results from the other
5. **Robust Gemini execution**: OpenCode ships an `opencode-gemini-review` helper that deterministically builds the shared `git diff -U40 HEAD` bundle, splits large reviews on file boundaries, retries failed chunks per file, and records machine-readable status in `summary.json`

**Benefits**: Catches issues each model might miss, surfaces conflicting interpretations that need human attention.

### ultrareview-lite

Lower-cost dual-model variant of `ultrareview`.

Runs parallel code reviews using **MiMo v2.5 Pro** (via OpenCode) AND **Gemini 3 Flash Preview** (via Gemini CLI), then consolidates using the same consensus/exclusive/divergent reporting structure.

1. **Launch parallel reviews**: Both models review the same `git diff -U40 HEAD` bundle
2. **Consolidate findings** with identical severity-preserving rules from `ultrareview`
3. **Use helper-managed Gemini execution**: deterministic bundle generation, chunking, retries, and `summary.json` status/failure metadata
4. **Graceful fallback and partial reporting**: if Gemini lane is partial or unavailable, report `failure_reason` and proceed with available results
5. **Lower operating cost** than `ultrareview` by replacing GPT 5.5 with MiMo in the OpenCode lane

### cc (Claude CLI)

Execute **Claude Code CLI** commands and code reviews from OpenCode:

1. **Direct CLI access**: Run `claude -p` commands with proper flag handling
2. **Code review mode**: Helper script for comprehensive reviews with artifact capture
3. **Tool control**: Configure `--allowedTools`, `--permission-mode`, `--bare` mode
4. **Structured output**: JSON responses for programmatic use
5. **Multi-step workflows**: Continue conversations across prompts

Requires Claude CLI installed and authenticated.

### imagegen-grok

Generates and edits images using **xAI Grok Imagine** (OpenCode only):

1. **Text-to-image**: Calls `https://api.x.ai/v1/images/generations` with `grok-imagine-image-quality`
2. **Image editing**: Calls `https://api.x.ai/v1/images/edits` with public image URLs or base64 data URIs
3. **Local output**: Requests `b64_json` output and writes image files immediately because xAI URLs are temporary
4. **Format choices**: Guides aspect ratio, resolution, and variation count based on the requested asset

Grok Imagine is reachable two ways from OpenCode: a raw `XAI_API_KEY` (required for the curl workflow in the skill), or a SuperGrok subscription signed in through OpenCode (resolves the `xai/grok-imagine-image-quality` model without axiaomi API key, but the curl path doesn't use it). Also requires `curl`, `jq`, and `python3` for the direct-API path.

### imagegen-google

Generates and edits images using **Google Nano Banana Pro** (`gemini-3-pro-image-preview`) via the Vertex AI Express mode of the `google-genai` SDK. Shipped to every supported harness (OpenCode subagent, Claude command, Codex skill, Warp workflow, Amp/Gemini/Windsurf/Droid skills, etc.):

1. **Text-to-image**: `client.models.generate_content` with `response_modalities=["IMAGE"]` and an `ImageConfig` aspect ratio
2. **Image editing / composition**: Passes up to 14 reference images as inline `Part`s alongside the prompt
3. **Local output**: Writes the returned `inline_data.data` bytes directly to disk
4. **Format choices**: Guides aspect ratio and variation count, leans on Nano Banana Pro's strong in-image text rendering

Requires `GOOGLE_API_KEY` (a Vertex AI Express key, prefix `AQ.`), `python3`, and the `google-genai` package.

### pr-reviewer

Addresses PR review feedback:

1. **Fetches comments** from GitHub PR via GraphQL
2. **Identifies reviewers**: Distinguishes bots vs humans
3. **Summarizes issues** in a table grouped by severity
4. **Addresses issues**: Human feedback takes priority over bots
5. **Commits and pushes** with summary of changes

### create-pr

Creates a PR from current changes:

1. **Creates feature branch** if on main/master
2. **Generates conventional commit** message
3. **Creates PR** with auto-generated title and description
4. **Reports result** with PR URL and summary

### cp

Commits current work and pushes to origin:

1. **Inspects the diff** to choose meaningful commit boundaries
2. **Commits in focused, conventional-commit slices** (splitting unrelated changes)
3. **Pushes explicitly** — sets upstream on the first push, otherwise runs `git push`
4. **Reports the commit(s)** and confirms the push completed

### deslop

Analyzes code for quality issues using established software engineering principles:

1. **Starts with a quick scan**: repo shape, validation commands, and risky generated/public areas
2. **Uses principles selectively**: applies KISS, YAGNI, SOLID, DRY, and related guidance where the evidence supports it
3. **Builds a cleanup ledger**: `Implement now` vs `Needs human review` vs `Defer to refactor`
4. **Implements only high-confidence cleanup** when the user wants changes, not broad redesigns
5. **Verifies results** and reports what changed, what was deferred, and why

*Based on [deslop](https://github.com/Theta-Tech-AI/llm-public-utils/blob/production/slash_commands/deslop.md) by Theta Tech AI.*

## Requirements

- **Git** for version control operations
- **GitHub CLI (`gh`)** for PR operations and `github-librarian`
- **OpenCode `webfetch`** for `docs-research`
- **OpenCode `websearch`** for best `docs-research` discovery results when URLs are not provided
- **Gemini CLI (`gemini`)** plus `gemini login` for `ultrareview` and `ultrareview-lite` secondary review lanes
- **`XAI_API_KEY`** *(or a SuperGrok subscription signed into OpenCode — note the curl workflow still needs the raw API key)*, `curl`, `jq`, and `python3` for OpenCode `imagegen-grok`
- **`GOOGLE_API_KEY`** (Vertex AI Express), `python3`, and `google-genai` for OpenCode `imagegen-google`
- **`ZENMUX_API_KEY`**, **`NVIDIA_API_KEY`**, and **Node.js** to run `bin/zenmux-throttle-proxy` when using rate-limited ZenMux or Nvidia models through the local throttle proxy
- The respective coding agent installed and configured

## Example OpenCode Prompts

- `In github.com/cli/cli, find where auth token resolution happens`
- `Use official docs to verify how SvelteKit remote functions work before changing our implementation`
- `Walk me through how authentication works in this repo and include a Mermaid diagram`
- `Compare our caching layer with owner/repo's implementation before proposing changes`
- `Show me recent commits affecting src/auth.ts in owner/repo`

## Contributing

1. Fork this repository
2. Add or modify prompts in `prompts/<agent>/`
3. Test with the target agent
4. Submit a pull request

## License

MIT
