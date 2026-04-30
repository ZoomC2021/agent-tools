# Glossary

Terms and concepts used throughout the agent-tools repository.

## Core concepts

**Codex53-Kimi**
The primary orchestrator architecture using GPT-5.3-Codex for planning and routing, with Fireworks Kimi K2.5 Turbo subagents for execution. Defined in `prompts/opencode/agent/codex53-kimi.md`.

**Execution Contract**
A structured specification produced by `spec-compiler` before implementation work begins. Defines scope, risks, success criteria, and validation steps.

**Mission-scrutiny**
A workflow for long-running, multi-step tasks that front-loads scrutiny, decomposes work into milestones, and sets validation cadence.

**Ultrareview**
Parallel dual-model code review using GPT 5.4 (OpenCode) AND Gemini 3.1 Pro Preview (Gemini CLI) simultaneously, with consolidated findings.

## Agent types

**Orchestrator**
Primary agent that plans, sequences, and verifies work. Delegates implementation to subagents. In OpenCode: `codex53-kimi` or `codex53-kimi-turbo`.

**Subagent**
Specialized agent for specific tasks (research, implementation, review). Has restricted permissions and is marked `hidden: true` in config.

**Mode**
Agent operating mode: `primary` (user-facing), `subagent` (delegated), or `plan`/`build` (workflow phases).

## Workflow terms

**Deslop**
Code quality audit workflow. Named after the open-source deslop utility. Analyzes code against software engineering principles (KISS, YAGNI, SOLID, DRY).

**Handoff**
Workflow that generates context for continuing work in a new session. Captures current state and pending tasks.

**Oracle**
Deep reasoning subagent using GPT-5.4 with high reasoning effort. Consulted for complex problems after consecutive failures.

## Technical terms

**{file:...} references**
Syntax in `opencode.json.example` for file path resolution. OpenCode expands these to file contents at runtime.

**Deterministic routing**
Keyword-based routing where specific triggers always map to the same agent. Prevents routing ambiguity.

**Intent verbalization**
Safety gate where the orchestrator states its routing reasoning aloud before proceeding, allowing users to catch misroutes.

**Turn-local intent reset**
Rule that reclassifies intent from the current message only, never carrying "implementation mode" from prior conversation turns.

## Project-specific

**Agent target**
A specific AI coding agent platform (e.g., claude, codex, cursor, pi). Each has its own directory under `prompts/`.

**Workflow prompt**
A Markdown file defining a reusable command/workflow. Stored in `prompts/<agent>/commands/` or `prompts/<agent>/`.

**Agent definition**
A Markdown file with frontmatter defining an agent's model, permissions, and behavior. Stored in `prompts/opencode/agent/`.

**SKILL.md**
Format used by Windsurf, Amp, and Gemini CLI for skill definitions. Contains metadata and prompt content.
