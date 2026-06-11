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
| `provider` | object | Provider configurations (openai, google, xiaomi) |
| `model` | string | Default model ID (e.g., `xiaomi/mimo-v2.5-pro`) |
| `default_agent` | string | Default agent to use (e.g., `gpt55-mimo-turbo`) |
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

### Xiaomi provider

```json
"xiaomi": {
  "options": {
    "apiKey": "YOUR_XIAOMI_API_KEY_HERE",
    "baseURL": "https://token-plan-ams.xiaomimimo.com/v1"
  },
  "models": {
    "mimo-v2.5-pro": {
      "name": "MiMo v2.5 Pro (Xiaomi)",
      "limit": {
        "context": 1000000,
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
    "model": "openai/gpt-5.5"
  },
  "build": {
    "model": "xiaomi/mimo-v2.5-pro"
  }
}
```

| Mode | Purpose | Default model |
|------|---------|---------------|
| `plan` | Architecture and planning | GPT 5.5 Low |
| `build` | Implementation and execution | MiMo v2.5 Pro |

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
"prompt": "{file:./agent/gpt55-mimo.md}"
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
