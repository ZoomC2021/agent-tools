"""Tests for scripts/all-token-usage.py.

Tests the normalization, aggregation, and reporting logic without
making SSH connections or running external scripts.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

# Load the script as a module (hyphen in filename prevents normal import)
_script_path = Path(__file__).resolve().parent.parent / "scripts" / "all-token-usage.py"
_loader = SourceFileLoader("all_token_usage", str(_script_path))
_spec = importlib.util.spec_from_loader(_loader.name, _loader)
atu = importlib.util.module_from_spec(_spec)
sys.modules["all_token_usage"] = atu
assert _spec.loader is not None
_spec.loader.exec_module(atu)


# ---------------------------------------------------------------------------
# Normalization tests
# ---------------------------------------------------------------------------

class TestNormalizeLocalCodex:
    def test_basic_conversion(self):
        report = {
            "models": {
                "gpt-5.5": {
                    "sessions": 10,
                    "uncached_input": 1000,
                    "cached_input": 5000,
                    "output": 500,
                    "reasoning": 100,
                    "providers": ["openai-codex"],
                },
                "grok-4.5": {
                    "sessions": 5,
                    "uncached_input": 2000,
                    "cached_input": 3000,
                    "output": 800,
                    "reasoning": 0,
                    "providers": ["xai-oauth"],
                },
            }
        }
        entries = atu.normalize_local_codex(report)
        assert len(entries) == 2
        e0 = next(e for e in entries if e.model == "gpt-5.5")
        assert e0.machine == "local"
        assert e0.source == "codex-cli+hermes"
        assert e0.billing_provider == "openai-codex"
        assert e0.uncached_input == 1000
        assert e0.cached_input == 5000
        assert e0.output == 500
        assert e0.reasoning == 100
        assert e0.sessions == 10

    def test_empty_report(self):
        entries = atu.normalize_local_codex({"models": {}})
        assert entries == []

    def test_missing_providers(self):
        report = {"models": {"gpt-5.5": {"sessions": 1, "uncached_input": 10,
                                         "cached_input": 0, "output": 5,
                                         "reasoning": 0}}}
        entries = atu.normalize_local_codex(report)
        assert entries[0].billing_provider == "unknown"


class TestNormalizeLocalAmp:
    def test_basic_conversion(self):
        report = {
            "models": {
                "gpt-5.5": {
                    "threads": 20,
                    "input_tokens": 0,
                    "total_input_tokens": 250000,
                    "billable_input_tokens": 50000,
                    "cache_read_input_tokens": 200000,
                    "output_tokens": 10000,
                },
                "claude-fable-5": {
                    "threads": 3,
                    "input_tokens": 0,
                    "total_input_tokens": 6000,
                    "billable_input_tokens": 5000,
                    "cache_read_input_tokens": 1000,
                    "output_tokens": 2000,
                },
            }
        }
        entries = atu.normalize_local_amp(report)
        assert len(entries) == 2
        e0 = next(e for e in entries if e.model == "gpt-5.5")
        assert e0.source == "amp"
        assert e0.billing_provider == "openai-codex"
        assert e0.uncached_input == 50000   # billable_input_tokens
        assert e0.cached_input == 200000    # cache_read_input_tokens
        assert e0.output == 10000
        assert e0.reasoning == 0
        assert e0.sessions == 20
        e1 = next(e for e in entries if e.model == "claude-fable-5")
        assert e1.billing_provider == "amp-credits"

    def test_unknown_model_provider(self):
        report = {"models": {"some-unknown-model": {
            "threads": 1, "input_tokens": 0,
            "total_input_tokens": 100, "billable_input_tokens": 100,
            "cache_read_input_tokens": 0, "output_tokens": 50}}}
        entries = atu.normalize_local_amp(report)
        assert entries[0].billing_provider == "unknown"
        assert entries[0].uncached_input == 100


class TestNormalizeRemoteHermes:
    def test_basic_conversion(self):
        rows = [
            {"session_id": "s1", "model": "gpt-5.5", "billing_provider": "openai-codex",
             "billing_base_url": "", "billing_mode": "", "task": "",
             "input_tokens": 1000, "output_tokens": 500,
             "cache_read_tokens": 5000, "cache_write_tokens": 0,
             "reasoning_tokens": 100},
            {"session_id": "s2", "model": "grok-4.5", "billing_provider": "xai-oauth",
             "billing_base_url": "", "billing_mode": "", "task": "",
             "input_tokens": 2000, "output_tokens": 800,
             "cache_read_tokens": 3000, "cache_write_tokens": 0,
             "reasoning_tokens": 0},
        ]
        entries = atu.normalize_remote_hermes("hetzner", rows)
        assert len(entries) == 2
        assert entries[0].machine == "hetzner"
        assert entries[0].source == "hermes"
        assert entries[0].billing_provider == "openai-codex"
        assert entries[0].uncached_input == 1000
        assert entries[0].cached_input == 5000

    def test_empty_rows(self):
        entries = atu.normalize_remote_hermes("host", [])
        assert entries == []

    def test_custom_provider(self):
        rows = [{"session_id": "s1", "model": "MiniMax-M3",
                 "billing_provider": "custom",
                 "billing_base_url": "", "billing_mode": "", "task": "",
                 "input_tokens": 100, "output_tokens": 50,
                 "cache_read_tokens": 0, "cache_write_tokens": 0,
                 "reasoning_tokens": 0}]
        entries = atu.normalize_remote_hermes("host", rows)
        assert entries[0].billing_provider == "custom"


class TestNormalizeOpenclaw:
    def test_basic_conversion(self):
        report = {
            "sessions": [
                {"model": "gpt-5.6-luna", "modelProvider": "openai",
                 "inputTokens": 1867, "outputTokens": 169},
                {"model": "grok-4.5", "modelProvider": "xai",
                 "inputTokens": 5000, "outputTokens": 1000},
            ]
        }
        entries = atu.normalize_openclaw("hetzner", report)
        assert len(entries) == 2
        assert entries[0].machine == "hetzner"
        assert entries[0].source == "openclaw"
        assert entries[0].billing_provider == "openai-codex"
        assert entries[0].uncached_input == 1867
        assert entries[0].cached_input == 0

    def test_skip_null_tokens(self):
        report = {
            "sessions": [
                {"model": "gpt-5.6-luna", "modelProvider": "openai",
                 "inputTokens": None, "outputTokens": None},
                {"model": "gpt-5.5", "modelProvider": "openai",
                 "inputTokens": 0, "outputTokens": 0},
                {"model": "gpt-5.5", "modelProvider": "openai",
                 "inputTokens": 100, "outputTokens": 50},
            ]
        }
        entries = atu.normalize_openclaw("host", report)
        assert len(entries) == 1
        assert entries[0].uncached_input == 100

    def test_unknown_provider(self):
        report = {"sessions": [
            {"model": "mimo-v2.5-pro", "modelProvider": "xiaomi",
             "inputTokens": 500, "outputTokens": 100}]}
        entries = atu.normalize_openclaw("host", report)
        assert entries[0].billing_provider == "xiaomi"


# ---------------------------------------------------------------------------
# Aggregation tests
# ---------------------------------------------------------------------------

class TestAggregateModels:
    def test_merges_same_model(self):
        entries = [
            atu.UsageEntry("local", "hermes", "gpt-5.5", "openai-codex",
                           uncached_input=1000, cached_input=500, output=200),
            atu.UsageEntry("hetzner", "hermes", "gpt-5.5", "openai-codex",
                           uncached_input=2000, cached_input=1000, output=300),
        ]
        per_model = atu.aggregate_models(entries)
        assert len(per_model) == 1
        agg = per_model["gpt-5.5"]
        assert agg.sessions == 2
        assert agg.uncached_input == 3000
        assert agg.cached_input == 1500
        assert agg.output == 500

    def test_separate_models(self):
        entries = [
            atu.UsageEntry("local", "hermes", "gpt-5.5", "openai-codex",
                           uncached_input=1000, output=200),
            atu.UsageEntry("local", "hermes", "grok-4.5", "xai-oauth",
                           uncached_input=2000, output=300),
        ]
        per_model = atu.aggregate_models(entries)
        assert len(per_model) == 2

    def test_cost_calculation(self):
        entries = [
            atu.UsageEntry("local", "hermes", "gpt-5.5", "openai-codex",
                           uncached_input=1_000_000, cached_input=0, output=0),
        ]
        per_model = atu.aggregate_models(entries)
        cost = per_model["gpt-5.5"].cost()
        assert cost["input"] == 5.00  # $5/1M input
        assert cost["total"] == 5.00

    def test_unpriced_model(self):
        entries = [
            atu.UsageEntry("local", "hermes", "unknown-model", "",
                           uncached_input=100000, output=10000),
        ]
        per_model = atu.aggregate_models(entries)
        assert not per_model["unknown-model"].is_priced
        assert per_model["unknown-model"].cost()["total"] == 0.0


class TestProviderCost:
    def test_groups_by_provider(self):
        entries = [
            atu.UsageEntry("local", "hermes", "gpt-5.5", "openai-codex",
                           uncached_input=1_000_000, output=0),
            atu.UsageEntry("hetzner", "hermes", "gpt-5.5", "openai-codex",
                           uncached_input=2_000_000, output=0),
            atu.UsageEntry("local", "hermes", "grok-4.5", "xai-oauth",
                           uncached_input=1_000_000, output=0),
        ]
        result = atu.provider_cost(entries)
        assert "openai-codex" in result
        assert "xai-oauth" in result
        # gpt-5.5 at $5/1M: 3M input = $15
        assert result["openai-codex"]["cost"] == 15.0
        # grok-4.5 at $2/1M: 1M input = $2
        assert result["xai-oauth"]["cost"] == 2.0

    def test_empty_entries(self):
        result = atu.provider_cost([])
        assert result == {}


# ---------------------------------------------------------------------------
# JSON report tests
# ---------------------------------------------------------------------------

class TestJsonReport:
    def test_basic_structure(self):
        mc = atu.MachineCollection(machine="local")
        mc.entries = [
            atu.UsageEntry("local", "codex-cli+hermes", "gpt-5.5", "openai-codex",
                           uncached_input=1_000_000, output=100_000),
        ]
        report = atu.compute_json_report([mc])
        assert "machines" in report
        assert len(report["machines"]) == 1
        assert report["machines"][0]["machine"] == "local"
        assert "grand_total_implied_api_cost" in report
        assert "by_provider" in report
        assert "openai-codex" in report["by_provider"]

    def test_openclaw_cross_reference(self):
        mc = atu.MachineCollection(machine="hetzner")
        mc.entries = [
            atu.UsageEntry("hetzner", "hermes", "gpt-5.5", "openai-codex",
                           uncached_input=1_000_000, output=100_000),
        ]
        mc.openclaw_entries = [
            atu.UsageEntry("hetzner", "openclaw", "gpt-5.5", "openai-codex",
                           uncached_input=500_000, output=50_000),
        ]
        report = atu.compute_json_report([mc])
        assert "openclaw_cross_reference" in report["machines"][0]
        # OpenClaw should NOT be in the grand total
        assert report["grand_total_implied_api_cost"] == 5.0 + 3.0  # 1M in + 100K out

    def test_errors_preserved(self):
        mc = atu.MachineCollection(machine="hetzner")
        mc.errors = ["hermes: connection refused"]
        report = atu.compute_json_report([mc])
        assert report["machines"][0]["errors"] == ["hermes: connection refused"]

    def test_multiple_machines(self):
        mc1 = atu.MachineCollection(machine="local")
        mc1.entries = [atu.UsageEntry("local", "hermes", "gpt-5.5", "openai-codex",
                                      uncached_input=1_000_000)]
        mc2 = atu.MachineCollection(machine="hetzner")
        mc2.entries = [atu.UsageEntry("hetzner", "hermes", "gpt-5.5", "openai-codex",
                                      uncached_input=2_000_000)]
        report = atu.compute_json_report([mc1, mc2])
        assert len(report["machines"]) == 2
        # Total: 3M input at $5/1M = $15
        assert report["grand_total_implied_api_cost"] == 15.0


# ---------------------------------------------------------------------------
# Pricing completeness tests
# ---------------------------------------------------------------------------

class TestPricing:
    def test_known_models_priced(self):
        for model in ["gpt-5.5", "gpt-5.6-sol", "gpt-5.6-luna", "grok-4.5",
                       "claude-fable-5", "MiniMax-M3"]:
            assert model in atu.PRICING, f"{model} missing from PRICING"

    def test_remote_models_priced(self):
        """Models found on remote machines should have pricing entries."""
        for model in ["grok-4.3", "grok-composer-2.5-fast",
                       "accounts/fireworks/routers/kimi-k2p6-turbo",
                       "mimo-v2.5", "mimo-v2.5-pro"]:
            assert model in atu.PRICING, f"{model} missing from PRICING"

    def test_pricing_keys_consistent(self):
        for model, p in atu.PRICING.items():
            assert "in" in p, f"{model} missing 'in' key"
            assert "cache" in p, f"{model} missing 'cache' key"
            assert "out" in p, f"{model} missing 'out' key"

    def test_model_to_provider_covers_priced_models(self):
        """All priced models should have a provider mapping."""
        for model in atu.PRICING:
            if model in atu.DEFAULT_PRICING:
                continue
            assert model in atu.MODEL_TO_PROVIDER, \
                f"{model} in PRICING but not in MODEL_TO_PROVIDER"
