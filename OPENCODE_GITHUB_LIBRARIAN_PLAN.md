# OpenCode GitHub Librarian Plan

## Summary

This document defines an implementation plan for a new OpenCode subagent, `github-librarian`, that provides remote GitHub code research similar in intent to Amp's Librarian.

The goal is not to reproduce Amp's backend exactly. The goal is to add a practical, reliable remote-repository research workflow that fits this repository's existing OpenCode architecture:

- `codex53-kimi` remains the orchestrator.
- `kimi-explore` remains the local workspace read-only discovery worker.
- `github-librarian` becomes the remote GitHub read-only discovery worker.
- `oracle` remains the deep reasoning escalation path.

This plan covers implementation through `v2`.

## Product Definition

### What `github-librarian` should do

`github-librarian` should answer questions about remote GitHub repositories without cloning them into the user's workspace and without making any code changes.

It should be able to:

- inspect public GitHub repositories
- inspect private GitHub repositories accessible through `gh` authentication
- work against the repository's default branch by default
- read targeted files from a remote repository
- search broadly across a remote repository's code
- explain architecture, flows, patterns, and module relationships
- compare local code with upstream or reference implementations

### What `github-librarian` should not do in v1/v2

It should not:

- modify local workspace files
- clone repositories into the workspace
- create or mutate git state in the workspace
- push, fork, open PRs, or write to remote repositories
- attempt to support Bitbucket or GitHub Enterprise in v1/v2
- claim full parity with Amp's Librarian implementation

## Why This Fits The Existing Architecture

The current OpenCode setup already has a clean separation between:

- orchestration: `prompts/opencode/codex53-kimi.md`
- local discovery: `prompts/opencode/kimi-explore.md`
- deep reasoning: `prompts/opencode/oracle.md`
- concrete GitHub API usage: `prompts/opencode/pr-reviewer.md`

The missing piece is remote repository research. `github-librarian` fills that gap without changing the rest of the architecture.

## Scope By Version

## v1: Remote Default-Branch Research

`v1` introduces a reliable read-only remote research path for GitHub repositories.

Capabilities:

- resolve repository metadata and default branch
- fetch single files from the default branch
- download a temporary snapshot of the default branch
- search snapshot contents locally with `rg`
- produce structured research reports with file paths and line references
- support public and private repositories through `gh`

Non-goals for v1:

- commit history analysis
- blame-style authorship analysis
- arbitrary branch selection
- caching
- cross-host support

## v2: History-Aware Research

`v2` extends the same subagent with lightweight history support while remaining read-only.

Capabilities:

- summarize recent commits for a repo or path
- inspect commit history for a specific file or directory
- answer "when did this change" style questions
- include commit references in reports when relevant
- correlate current file contents with recent change history

Non-goals for v2:

- full git blame reproduction
- branch graph analysis
- PR review thread analysis
- cross-repository indexing
- long-lived persistent cache

## Recommended Technical Approach

## Core Principle

Use the smallest mechanism that is reliable enough for serious code research.

The recommended implementation is:

- `gh api` for metadata and targeted GitHub REST calls
- temporary tarball snapshots for broad code search
- a small installed Bash helper to wrap the transport details
- a new subagent prompt to control behavior and output

This is intentionally simpler than clone-based or MCP-based designs.

## Why Not Make `gh search code` The Backbone

`gh search code` is useful but should not be the primary data path.

Reasons:

- GitHub CLI documents that it still uses legacy code search behavior.
- Search results may differ from what users see on github.com.
- It is not enough for architecture walkthroughs or broad multi-file inspection by itself.

It can be added later as an optimization, but not as the foundation.

## Why Not Use Shallow Clone

Shallow clone is not the right default mechanism for v1/v2.

Problems:

- introduces `.git` state
- increases accidental mutation surface
- is heavier than necessary for read-only analysis
- complicates cleanup and temp directory handling

For default-branch research, tarball snapshots are safer and simpler.

## Why A Small Helper Script Is Worth It

The helper script keeps GitHub transport logic out of the prompt and makes behavior deterministic.

Benefits:

- reuses the existing `gh` auth model already assumed elsewhere in the repo
- keeps prompts shorter and easier to maintain
- centralizes default-branch resolution and archive handling
- avoids repeating brittle shell snippets inside markdown prompts
- fits the current install model in `scripts/install.sh`

## v1 Architecture

## New Subagent

Add a new subagent prompt file:

- `prompts/opencode/github-librarian.md`

This agent should:

- use the same model family as `kimi-explore`
- be read-only
- allow `bash` only for helper usage and local read-only shell tools
- explicitly prohibit edits, writes, clones, pushes, and workspace mutation
- return detailed research reports

Suggested frontmatter:

```yaml
---
description: Read-only remote GitHub code research on default-branch snapshots
mode: subagent
model: fireworks-ai/accounts/fireworks/routers/kimi-k2p5-turbo
permission:
  task:
    '*': deny
    read: allow
    bash: allow
---
```

## New Helper

Add a helper script:

- `prompts/opencode/bin/opencode-gh-librarian`

The helper should be a small Bash script with strict shell settings:

```bash
set -euo pipefail
```

The helper should expose these commands in v1:

```bash
opencode-gh-librarian default-branch <owner/repo>
opencode-gh-librarian snapshot <owner/repo> <dest-dir>
opencode-gh-librarian cat-file <owner/repo> <path>
```

### `default-branch`

Uses:

```bash
gh api repos/<owner>/<repo> --jq .default_branch
```

Returns the default branch name.

### `snapshot`

Responsibilities:

- resolve the default branch
- download the archive for that branch
- extract it into a caller-provided temporary directory
- print the extracted root directory path

Implementation direction:

- use GitHub's tarball endpoint for the default branch
- rely on `gh api` for authenticated access to private repos
- keep all extracted contents outside the workspace root

The subagent should own temp directory creation and cleanup, for example:

```bash
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
root="$(~/.config/opencode/bin/opencode-gh-librarian snapshot cli/cli "$tmpdir")"
rg -n "token|auth" "$root"
```

### `cat-file`

Responsibilities:

- fetch raw file contents from the repository default branch
- print contents to stdout

Implementation direction:

- use the GitHub contents API through `gh api`
- resolve default branch automatically if not otherwise specified

## v1 Data Flow

1. The orchestrator detects that a request targets a remote GitHub repository.
2. It delegates to `github-librarian`.
3. `github-librarian` decides whether the task is a single-file read or a broad repo search.
4. For single-file reads, it uses `cat-file`.
5. For broad repo analysis, it creates a temp dir, obtains a snapshot, and runs local read-only tools against it.
6. It returns a structured report with path references and findings.

## v2 Architecture Additions

`v2` should extend the helper rather than introducing a second helper or a different transport layer.

Add these commands:

```bash
opencode-gh-librarian recent-commits <owner/repo> [limit]
opencode-gh-librarian file-history <owner/repo> <path> [limit]
```

### `recent-commits`

Purpose:

- provide recent default-branch commit summaries for repo-level questions

Implementation direction:

- use `gh api repos/<owner>/<repo>/commits`
- limit output to fields the subagent actually needs
- include commit SHA, author, date, and message headline

### `file-history`

Purpose:

- provide recent commits affecting a specific file or path

Implementation direction:

- use `gh api repos/<owner>/<repo>/commits?path=<path>`
- limit output size and normalize it for prompt consumption

This gives useful history context without needing a clone or full git metadata.

## Routing Changes

## Orchestrator Changes

Update `prompts/opencode/codex53-kimi.md`.

Add a new routing rule before the current generic discovery rule.

Recommended rule:

- if the request is read-only research on a remote GitHub repository, use `github-librarian`
- if the request is read-only discovery in the local workspace, use `kimi-explore`

Trigger examples for `github-librarian`:

- explicit GitHub URL like `https://github.com/owner/repo`
- explicit repo slug like `owner/repo`
- wording like `upstream repo`, `external repo`, `remote repo`, `GitHub repo`
- verbs like `find`, `search`, `inspect`, `explain`, `compare`, `research`

Also add guidance for mixed local/remote tasks:

- when a local implementation task needs upstream reference research first, use `github-librarian` before local implementation flow

## Config Changes

Update `prompts/opencode/opencode.json.example`.

Required changes:

- add `github-librarian` to orchestrator task permissions
- add an agent definition for `github-librarian`
- update architecture comments to include the new subagent
- update file placement comments to mention helper binaries if needed

## Install Changes

Update `scripts/install.sh`.

Required changes:

- continue copying prompt files to `~/.config/opencode/agent/`
- additionally copy helper scripts from `prompts/opencode/bin/` to `~/.config/opencode/bin/`
- mark helper scripts executable
- mention the helper installation location in install output

## Documentation Changes

Update `README.md`.

Required changes:

- update the OpenCode architecture diagram to include `github-librarian`
- describe the difference between `kimi-explore` and `github-librarian`
- document the helper install location
- document the `gh` dependency and auth requirement
- include example prompts

Suggested example prompts:

- `In github.com/cli/cli, find where auth token resolution happens`
- `Compare our parser with owner/repo's parser implementation`
- `Explain how routing works in github.com/anomalyco/opencode`
- `Show me recent commits affecting src/auth.ts in owner/repo`

## Subagent Behavior Requirements

`github-librarian` should follow these rules.

### Required behavior

- operate read-only
- prefer `cat-file` for narrow known-file requests
- prefer `snapshot` for broad or multi-file research
- always report which repository and default branch were analyzed
- include file paths and line numbers whenever possible
- be explicit about scope limits and access failures

### Forbidden behavior

- no edits or writes
- no `git clone`
- no `git checkout`
- no writes to workspace files
- no speculative claims unsupported by the fetched code

### BLOCKED protocol

Return `BLOCKED` if:

- the repository is inaccessible via `gh`
- the repo slug is ambiguous
- the task requires unsupported host types
- the user expects non-default-branch analysis in v1/v2

## Report Format

Use a consistent report structure.

```markdown
## Remote Research Report: <goal>

### Repository
- Repo: owner/repo
- Default branch: main

### Scope Searched
- Paths/directories:
- Patterns/questions:

### Findings
| File | Line(s) | Summary |
|------|---------|---------|

### Patterns Observed
- ...

### History Context
- ...

### Gaps / Caveats
- ...

### Summary
...
```

In `v1`, the `History Context` section can be omitted if unused. In `v2`, it should be used when commit history was consulted.

## File-Level Change Plan

## New Files

- `prompts/opencode/github-librarian.md`
- `prompts/opencode/bin/opencode-gh-librarian`

## Modified Files

- `prompts/opencode/codex53-kimi.md`
- `prompts/opencode/opencode.json.example`
- `scripts/install.sh`
- `README.md`

## v2 Optional Additional Files

No additional files should be necessary if the helper is designed to grow cleanly. `v2` should primarily be an extension of:

- `prompts/opencode/bin/opencode-gh-librarian`
- `prompts/opencode/github-librarian.md`
- `README.md`

## Implementation Order

## Phase 1: v1 Core

1. Add helper script with `default-branch`, `snapshot`, and `cat-file`.
2. Add `github-librarian` prompt.
3. Update orchestrator routing.
4. Update `opencode.json.example`.
5. Update installer.
6. Update README.
7. Run manual validation.

## Phase 2: v2 History Support

1. Extend helper with `recent-commits` and `file-history`.
2. Update prompt instructions to use history tools when relevant.
3. Update README examples and documentation.
4. Run manual validation for history-oriented prompts.

## Validation Plan

## v1 Validation

Manual checks:

1. Install the updated OpenCode assets.
2. Confirm `gh auth status` works.
3. Ask: `In github.com/cli/cli, find where auth token resolution happens`.
4. Confirm `github-librarian` is chosen.
5. Confirm result includes repo, default branch, file paths, and line numbers.
6. Ask a broader architecture prompt against a public repo.
7. Confirm temporary snapshot cleanup works.

## v2 Validation

Manual checks:

1. Ask: `Show me recent commits affecting <path> in owner/repo`.
2. Confirm `file-history` or `recent-commits` is used.
3. Confirm commit SHA, author/date, and summary are returned.
4. Ask a mixed prompt combining current code and recent history.
5. Confirm the report distinguishes between current-state findings and historical context.

## Acceptance Criteria

## v1 Acceptance Criteria

- remote GitHub research routes to `github-librarian`
- local workspace discovery still routes to `kimi-explore`
- public repositories work without extra configuration beyond `gh`
- private repositories work when `gh` auth allows access
- repo-wide search works without cloning into the workspace
- report quality is comparable to existing discovery reports

## v2 Acceptance Criteria

- `github-librarian` can answer recent-history questions for repos and files
- history data stays limited and readable
- no git clone is required
- no workspace mutation occurs
- the prompt clearly communicates current-state findings versus recent change history

## Risks And Mitigations

## Large Repositories

Risk:

- tarball snapshots may be slow for very large repositories

Mitigation:

- narrow scope in the prompt
- prefer targeted file reads when possible
- add caching only if this becomes a real bottleneck later

## Private Repository Access

Risk:

- `gh` may not be authenticated for the target repository

Mitigation:

- fail fast with a clear `BLOCKED` response
- report the exact access issue

## Tool Drift In Prompt Logic

Risk:

- prompts become inconsistent with helper behavior over time

Mitigation:

- keep helper command names stable
- keep the prompt focused on behavior, not low-level transport detail

## Overexpansion

Risk:

- `v2` grows into a general remote-git platform prematurely

Mitigation:

- restrict `v2` to lightweight history APIs only
- defer blame, branch analysis, and non-GitHub support

## Deferred Work After v2

These are explicitly out of scope for this document but are possible future directions:

- GitHub Enterprise support
- Bitbucket support
- non-default-branch analysis
- caching extracted snapshots
- blame-style authorship reporting
- PR discussion or review-thread research
- richer architecture visualization or cross-repo comparison tooling

## Final Recommendation

Implement `github-librarian` as a dedicated OpenCode subagent with a small installed Bash helper backed by `gh api` and default-branch tarball snapshots.

Ship `v1` as a dependable remote research worker.

Ship `v2` by extending the same helper with lightweight commit history support rather than introducing a new backend or a second system.
