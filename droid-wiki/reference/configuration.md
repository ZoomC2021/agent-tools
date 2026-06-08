# Configuration reference

OpenCode configuration structure and options.

## File location

`prompts/opencode/opencode.json.example` serves as the authoritative configuration template. The installer uses this to sync existing user configs.

## Schema

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": [],
  "provider": {},
  "model": "string",
  "default_agent": "string",
  "mode": {},
  "agent": {}
}
```

## Top-level fields

| Field | Type | Description |
|-------|------|-------------|
| `$schema` | string | JSON Schema URI for validation |
| `plugin` | string[] | Auth plugins (e.g., `opencode-antigravity-auth@1.6.0`) |
| `provider` | object | Provider configurations (openai, google, fireworks-ai) |
| `model` | string | Default model ID (e.g., `fireworks-ai/accounts/fireworks/routers/kimi-k2p6-turbo`) |
| `default_agent` | string | Default agent to use (e.g., `codex53-kimi-turbo`) |
| `mode` | object | Mode-specific model overrides (plan, build) |
| `agent` | object | Agent definitions and permissions |

## Provider configuration

### OpenAI provider

```json
"openai": {
  "options": {
    "reasoningEffort": "medium",
    "reasoningSummary": "auto",
    "textVerbosity": "medium",
    "include": ["reasoning.encrypted_content"],
    "store": false
  },
  "models": {
    "gpt-5.2-medium": {
      "name": "GPT 5.2 Medium (OAuth)",
      "limit": {
        "context": 272000,
        "output": 128000
      },
      "modalities": {
        "input": ["text", "image"],
        "output": ["text"]
      }
    }
  }
}
```

### Fireworks AI provider

```json
"fireworks-ai": {
  "options": {
    "apiKey": "YOUR_FIREWORKS_API_KEY_HERE"
  },
  "models": {
    "accounts/fireworks/routers/kimi-k2p6-turbo": {
      "name": "Kimi 2.5 Turbo (Fireworks)",
      "limit": {
        "context": 256000,
        "output": 256000
      },
      "modalities": {
        "input": ["text"],
        "output": ["text"]
      },
      "cost": {
        "input": 0.99,
        "output": 4.94,
        "cache": {
          "read": 0.16,
          "write": 0.99
        }
      }
    }
  }
}
```

### Google provider (via Antigravity)

```json
"google": {
  "models": {
    "gemini-3-pro-high": {
      "name": "Gemini 3 Pro High (Antigravity)",
      "limit": {
        "context": 1048576,
        "output": 65535
      },
      "modalities": {
        "input": ["text", "image", "pdf"],
        "output": ["text"]
      }
    }
  }
}
```

## Mode configuration

Override models for specific modes:

```json
"mode": {
  "plan": {
    "model": "openai/gpt-5.3-codex"
  },
  "build": {
    "model": "fireworks-ai/accounts/fireworks/routers/kimi-k2p6-turbo"
  }
}
```

| Mode | Purpose | Default model |
|------|---------|---------------|
| `plan` | Architecture and planning | GPT 5.3 Codex |
| `build` | Implementation and execution | Kimi 2.5 Turbo |

## Agent configuration

Each agent has the following structure:

```json
"agent_name": {
  "description": "What this agent does",
  "mode": "subagent",
  "model": "model-id",
  "hidden": true,
  "prompt": "{file:./path/to/prompt.md}",
  "permission": {
    "task": {
      "*": "deny",
      "allowed_task": "allow"
    },
    "read": "allow",
    "bash": "allow"
  }
}
```

### Permission structure

| Permission | Values | Description |
|------------|--------|-------------|
| `task` | `{"*": "deny", "task_name": "allow"}` | Task-level permissions |
| `read` | `"allow"` / `"deny"` | File read access |
| `bash` | `"allow"` / `"deny"` | Shell command execution |
| `edit` | `"allow"` / `"deny"` | File editing |
| `write` | `"allow"` / `"deny"` | File creation |

### File references

Prompts use `{file:./relative/path}` syntax to reference Markdown files:

```json
"prompt": "{file:./agent/codex53-kimi.md}"
```

The path is relative to `prompts/opencode/`.

## Validation

Validate configuration changes:

```bash
# Check JSON syntax
jq -e . prompts/opencode/opencode.json.example >/dev/null

# Verify all file references resolve
jq -r '.. | strings | select(test("^\\{file:[^}]+\\}$")) | capture("^\\{file:(?<p>[^}]+)\\}$").p' \
  prompts/opencode/opencode.json.example | sort -u | while read ref; do
    [ -f "prompts/opencode/${ref#./}" ] || echo "MISS $ref"
  done
```

## See also

- [Data models](data-models.md) — Execution contracts and data structures
- [Agent targets](../agent-targets/opencode.md) — OpenCode-specific features
