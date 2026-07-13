"""Focused subprocess tests for the Claude provider launchers."""

import json
import os
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
PROVIDER_VARS = {
    "agentrouter": ("claude-agentrouter.sh", "AGENT_ROUTER_TOKEN", "claude-sonnet-4-6", "https://agentrouter.org/"),
    "bai": ("claude-bai.sh", "BAI_API_KEY", "claude-opus-4.8", "https://api.b.ai"),
    "xiaomi": ("claude-xiaomi.sh", "XIAOMI_API_KEY", "mimo-v2.5-pro", "https://token-plan-ams.xiaomimimo.com/anthropic"),
}
CONTROLLED_VARS = {
    "AGENT_ROUTER_TOKEN", "BAI_API_KEY", "XIAOMI_API_KEY", "MIMO_API_KEY",
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_MODEL",
    "CLAUDE_MODEL", "ANTHROPIC_BASE_URL",
}


@pytest.fixture
def fake_claude(tmp_path):
    binary = tmp_path / "claude"
    binary.write_text("""#!/usr/bin/env python3
import json, os, sys
print(json.dumps({
    "args": sys.argv[1:],
    "api_key": os.environ.get("ANTHROPIC_API_KEY"),
    "auth_token": os.environ.get("ANTHROPIC_AUTH_TOKEN"),
    "model": os.environ.get("ANTHROPIC_MODEL"),
    "base_url": os.environ.get("ANTHROPIC_BASE_URL"),
}))
""")
    binary.chmod(0o755)
    return tmp_path


def run_launcher(provider, fake_path, extra_env=None, args=()):
    script, _, _, _ = PROVIDER_VARS[provider]
    env = {key: value for key, value in os.environ.items() if key not in CONTROLLED_VARS}
    env["PATH"] = f"{fake_path}:{env.get('PATH', '')}"
    env.update(extra_env or {})
    return subprocess.run(
        [str(SCRIPTS / script), *args], env=env, text=True,
        capture_output=True, check=False,
    )


@pytest.mark.parametrize("provider", PROVIDER_VARS)
def test_preferred_credential_is_normalized_and_defaults_are_used(provider, fake_claude):
    _, preferred_var, default_model, default_url = PROVIDER_VARS[provider]
    result = run_launcher(provider, fake_claude, {
        preferred_var: "preferred", "ANTHROPIC_API_KEY": "old-api", "ANTHROPIC_AUTH_TOKEN": "old-auth",
    })

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["api_key"] == payload["auth_token"] == "preferred"
    assert payload["model"] == default_model
    assert payload["base_url"] == default_url
    assert payload["args"][:3] == ["--dangerously-skip-permissions", "--model", default_model]


def test_xiaomi_mimo_credential_precedes_anthropic_fallback(fake_claude):
    result = run_launcher("xiaomi", fake_claude, {"MIMO_API_KEY": "mimo", "ANTHROPIC_API_KEY": "fallback"})
    payload = json.loads(result.stdout)
    assert payload["api_key"] == payload["auth_token"] == "mimo"


@pytest.mark.parametrize("fallback", ["ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"])
def test_anthropic_credential_fallback_is_normalized(fallback, fake_claude):
    result = run_launcher("bai", fake_claude, {fallback: "fallback"})
    payload = json.loads(result.stdout)
    assert payload["api_key"] == payload["auth_token"] == "fallback"


def test_overrides_and_arguments_are_forwarded(fake_claude):
    result = run_launcher("agentrouter", fake_claude, {
        "AGENT_ROUTER_TOKEN": "token", "ANTHROPIC_MODEL": "custom-model",
        "CLAUDE_MODEL": "ignored", "ANTHROPIC_BASE_URL": "https://custom.example",
    }, ("-p", "hello world", "--model", "argument-model"))
    payload = json.loads(result.stdout)
    assert payload["model"] == "custom-model"
    assert payload["base_url"] == "https://custom.example"
    assert payload["args"] == [
        "--dangerously-skip-permissions", "--model", "custom-model",
        "-p", "hello world", "--model", "argument-model",
    ]


def test_help_does_not_require_credentials_or_claude(tmp_path):
    result = run_launcher("xiaomi", tmp_path, args=("--help",))
    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert "XIAOMI_API_KEY" in result.stdout
    assert "--dangerously-skip-permissions" in result.stdout


@pytest.mark.parametrize("provider", PROVIDER_VARS)
def test_missing_credential_reports_provider_error(provider, fake_claude):
    result = run_launcher(provider, fake_claude)
    assert result.returncode == 1
    assert "error: set " in result.stderr


def test_missing_claude_is_reported(tmp_path):
    result = run_launcher("bai", tmp_path, {"BAI_API_KEY": "token", "PATH": "/usr/bin:/bin"})
    assert result.returncode == 1
    assert result.stderr == "error: claude not found on PATH\n"
