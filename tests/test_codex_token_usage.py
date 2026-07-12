"""Tests for scripts/codex-token-usage.py.

Uses temporary directories with fixture JSONL files and an in-memory
SQLite database to verify the loading, merging, and cost-calculation logic
without touching real Codex/Hermes data.
"""

import importlib.util
import json
import os
import sqlite3
import sys
import tempfile
from importlib.machinery import SourceFileLoader
from pathlib import Path

# Load the script as a module (hyphen in filename prevents normal import)
_script_path = Path(__file__).resolve().parent.parent / "scripts" / "codex-token-usage.py"
_loader = SourceFileLoader("codex_token_usage", str(_script_path))
_spec = importlib.util.spec_from_loader(_loader.name, _loader)
ctu = importlib.util.module_from_spec(_spec)
sys.modules["codex_token_usage"] = ctu
assert _spec.loader is not None
_spec.loader.exec_module(ctu)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _write_codex_rollout(path: Path, session_id: str, model: str,
                         input_tokens: int, cached_input_tokens: int,
                         output_tokens: int, reasoning: int = 0,
                         plan: str = "plus"):
    """Write a minimal Codex CLI rollout JSONL file.

    In Codex CLI, ``input_tokens`` includes ``cached_input_tokens``.
    """
    lines = [
        json.dumps({
            "type": "session_meta",
            "payload": {"session_id": session_id, "model_provider": "openai"},
        }),
        json.dumps({
            "type": "turn_context",
            "payload": {"turn_id": "t1", "model": model},
        }),
        json.dumps({
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "total_token_usage": {
                        "input_tokens": input_tokens,
                        "cached_input_tokens": cached_input_tokens,
                        "output_tokens": output_tokens,
                        "reasoning_output_tokens": reasoning,
                        "total_tokens": input_tokens + output_tokens,
                    },
                },
                "rate_limits": {"plan_type": plan},
            },
        }),
    ]
    path.write_text("\n".join(lines) + "\n")


def _write_codex_rollout_no_tokens(path: Path, session_id: str):
    """Write a Codex CLI rollout with no token_count events (should be skipped)."""
    path.write_text(json.dumps({
        "type": "session_meta",
        "payload": {"session_id": session_id},
    }) + "\n")


def _make_hermes_db(path: Path, rows: list[tuple]):
    """Create a Hermes state.db with session_model_usage rows.

    Each row is (session_id, model, billing_provider, billing_mode,
                 input_tokens, output_tokens, cache_read_tokens,
                 cache_write_tokens, reasoning_tokens).
    """
    con = sqlite3.connect(str(path))
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE session_model_usage (
            session_id TEXT NOT NULL,
            model TEXT NOT NULL,
            billing_provider TEXT NOT NULL DEFAULT '',
            billing_base_url TEXT NOT NULL DEFAULT '',
            billing_mode TEXT NOT NULL DEFAULT '',
            api_call_count INTEGER NOT NULL DEFAULT 0,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            cache_read_tokens INTEGER NOT NULL DEFAULT 0,
            cache_write_tokens INTEGER NOT NULL DEFAULT 0,
            reasoning_tokens INTEGER NOT NULL DEFAULT 0,
            estimated_cost_usd REAL NOT NULL DEFAULT 0,
            actual_cost_usd REAL NOT NULL DEFAULT 0,
            cost_status TEXT,
            cost_source TEXT,
            first_seen REAL,
            last_seen REAL,
            PRIMARY KEY (session_id, model, billing_provider, billing_base_url, billing_mode)
        )
    """)
    cur.executemany(
        "INSERT INTO session_model_usage "
        "(session_id, model, billing_provider, billing_mode, "
        " input_tokens, output_tokens, cache_read_tokens, "
        " cache_write_tokens, reasoning_tokens) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    con.commit()
    con.close()


# ---------------------------------------------------------------------------
# Codex CLI loader tests
# ---------------------------------------------------------------------------

def test_load_codex_sessions_basic():
    """Codex CLI loader extracts tokens from the last token_count event."""
    with tempfile.TemporaryDirectory() as d:
        sess_dir = Path(d) / "2026" / "07" / "06"
        sess_dir.mkdir(parents=True)
        _write_codex_rollout(
            sess_dir / "rollout-2026-07-06T22-56-12-019f37ee-014e-72d2-a244-d85a3764de5a.jsonl",
            "019f37ee-014e-72d2-a244-d85a3764de5a",
            "gpt-5.5",
            input_tokens=100000,
            cached_input_tokens=80000,
            output_tokens=500,
            reasoning=100,
        )
        result = ctu.load_codex_sessions(d)
        assert len(result) == 1
        usage = list(result.values())[0]
        assert usage.model == "gpt-5.5"
        # uncached = input - cached
        assert usage.uncached_input == 20000
        assert usage.cached_input == 80000
        assert usage.output == 500
        assert usage.reasoning == 100
        assert usage.source == "codex-cli"
        assert usage.plan == "plus"


def test_load_codex_sessions_skips_no_tokens():
    """Sessions without token_count events are skipped."""
    with tempfile.TemporaryDirectory() as d:
        sess_dir = Path(d) / "2026" / "07" / "06"
        sess_dir.mkdir(parents=True)
        _write_codex_rollout_no_tokens(
            sess_dir / "rollout-2026-07-06T23-03-41-abc.jsonl",
            "abc",
        )
        result = ctu.load_codex_sessions(d)
        assert len(result) == 0


def test_load_codex_sessions_multiple_token_counts():
    """The loader uses the last token_count's total_token_usage (cumulative)."""
    with tempfile.TemporaryDirectory() as d:
        sess_dir = Path(d) / "2026" / "06" / "29"
        sess_dir.mkdir(parents=True)
        path = sess_dir / "rollout-2026-06-29T18-53-50-019f1303-9935-74e1-91b9-55d6f163e4a6.jsonl"
        lines = [
            json.dumps({"type": "turn_context", "payload": {"model": "gpt-5.5"}}),
            json.dumps({
                "type": "event_msg",
                "payload": {
                    "type": "token_count",
                    "info": {"total_token_usage": {
                        "input_tokens": 10000, "cached_input_tokens": 4000,
                        "output_tokens": 100, "reasoning_output_tokens": 10,
                        "total_tokens": 10100,
                    }},
                    "rate_limits": {"plan_type": "plus"},
                },
            }),
            json.dumps({
                "type": "event_msg",
                "payload": {
                    "type": "token_count",
                    "info": {"total_token_usage": {
                        "input_tokens": 50000, "cached_input_tokens": 30000,
                        "output_tokens": 800, "reasoning_output_tokens": 50,
                        "total_tokens": 50800,
                    }},
                    "rate_limits": {"plan_type": "plus"},
                },
            }),
        ]
        path.write_text("\n".join(lines) + "\n")
        result = ctu.load_codex_sessions(d)
        usage = list(result.values())[0]
        assert usage.uncached_input == 20000  # 50000 - 30000
        assert usage.cached_input == 30000
        assert usage.output == 800
        assert usage.reasoning == 50


# ---------------------------------------------------------------------------
# Hermes loader tests
# ---------------------------------------------------------------------------

def test_load_hermes_sessions_filters_codex_provider():
    """Only openai-codex billing_provider rows are loaded by default."""
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "state.db"
        _make_hermes_db(db, [
            ("s1", "gpt-5.5", "openai-codex", "subscription_included",
             1000, 500, 5000, 0, 100),
            ("s2", "grok-composer-2.5-fast", "xai-oauth", "",
             2000, 300, 1000, 0, 0),
        ])
        result = ctu.load_hermes_sessions(str(db))
        assert len(result) == 1
        usage = list(result.values())[0]
        assert usage.model == "gpt-5.5"
        assert usage.uncached_input == 1000
        assert usage.cached_input == 5000
        assert usage.output == 500
        assert usage.reasoning == 100


def test_load_hermes_sessions_all_providers():
    """--all-providers includes non-Codex billing providers."""
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "state.db"
        _make_hermes_db(db, [
            ("s1", "gpt-5.5", "openai-codex", "subscription_included",
             1000, 500, 5000, 0, 100),
            ("s2", "grok-composer-2.5-fast", "xai-oauth", "",
             2000, 300, 1000, 0, 0),
        ])
        result = ctu.load_hermes_sessions(str(db), all_providers=True)
        assert len(result) == 2


def test_load_hermes_sessions_missing_db():
    """Missing DB file returns empty dict."""
    result = ctu.load_hermes_sessions("/nonexistent/path.db")
    assert result == {}


def test_load_hermes_sessions_multi_model_session():
    """A session with multiple models produces multiple entries."""
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "state.db"
        _make_hermes_db(db, [
            ("s1", "gpt-5.5", "openai-codex", "subscription_included",
             1000, 500, 5000, 0, 100),
            ("s1", "gpt-5.6-sol", "openai-codex", "subscription_included",
             2000, 800, 10000, 0, 200),
        ])
        result = ctu.load_hermes_sessions(str(db))
        assert len(result) == 2
        models = sorted(u.model for u in result.values())
        assert models == ["gpt-5.5", "gpt-5.6-sol"]


# ---------------------------------------------------------------------------
# Merge and cost tests
# ---------------------------------------------------------------------------

def test_merge_usage_combines_sources():
    """Merge correctly combines Codex CLI and Hermes sessions."""
    codex = {
        "c1": ctu.SessionUsage(
            model="gpt-5.5", uncached_input=1000, cached_input=5000,
            output=100, reasoning=50, source="codex-cli",
        ),
    }
    hermes = {
        "h1": ctu.SessionUsage(
            model="gpt-5.5", uncached_input=2000, cached_input=10000,
            output=200, reasoning=100, source="hermes:openai-codex",
        ),
        "h2": ctu.SessionUsage(
            model="gpt-5.6-sol", uncached_input=500, cached_input=2000,
            output=50, reasoning=25, source="hermes:openai-codex",
        ),
    }
    per_model = ctu.merge_usage(codex, hermes)
    assert per_model["gpt-5.5"].sessions == 2
    assert per_model["gpt-5.5"].uncached_input == 3000
    assert per_model["gpt-5.5"].cached_input == 15000
    assert per_model["gpt-5.5"].output == 300
    assert per_model["gpt-5.5"].reasoning == 150
    assert per_model["gpt-5.6-sol"].sessions == 1
    assert per_model["gpt-5.6-sol"].uncached_input == 500


def test_model_totals_cost():
    """Cost calculation uses uncached input, cached input, and billable output."""
    totals = ctu.ModelTotals(
        model="gpt-5.5",
        sessions=1,
        uncached_input=1_000_000,
        cached_input=2_000_000,
        output=100_000,
        reasoning=50_000,
    )
    cost = totals.cost(ctu.PRICING)
    # gpt-5.5: in=$5, cache=$0.50, out=$30 per 1M
    assert abs(cost["input"] - 5.00) < 0.01
    assert abs(cost["cached"] - 1.00) < 0.01
    # billable output = 100K + 50K = 150K → 0.15M * $30 = $4.50
    assert abs(cost["output"] - 4.50) < 0.01
    assert abs(cost["total"] - 10.50) < 0.01


def test_model_totals_cost_luna():
    """gpt-5.6-luna uses cheaper pricing."""
    totals = ctu.ModelTotals(
        model="gpt-5.6-luna",
        sessions=1,
        uncached_input=1_000_000,
        cached_input=2_000_000,
        output=100_000,
        reasoning=50_000,
    )
    cost = totals.cost(ctu.PRICING)
    # luna: in=$1, cache=$0.10, out=$6 per 1M
    assert abs(cost["input"] - 1.00) < 0.01
    assert abs(cost["cached"] - 0.20) < 0.01
    assert abs(cost["output"] - 0.90) < 0.01
    assert abs(cost["total"] - 2.10) < 0.01


def test_model_totals_cost_older_models():
    """gpt-5.4, gpt-5.4-mini, and gpt-5.3-codex-spark use their own rates."""
    # gpt-5.4: in=$2.50, cache=$0.25, out=$15
    t54 = ctu.ModelTotals(model="gpt-5.4", uncached_input=1_000_000,
                          cached_input=1_000_000, output=100_000, reasoning=0)
    c54 = t54.cost(ctu.PRICING)
    assert abs(c54["input"] - 2.50) < 0.01
    assert abs(c54["cached"] - 0.25) < 0.01
    assert abs(c54["output"] - 1.50) < 0.01

    # gpt-5.4-mini: in=$0.75, cache=$0.075, out=$4.50
    t54m = ctu.ModelTotals(model="gpt-5.4-mini", uncached_input=1_000_000,
                           cached_input=1_000_000, output=100_000, reasoning=0)
    c54m = t54m.cost(ctu.PRICING)
    assert abs(c54m["input"] - 0.75) < 0.01
    assert abs(c54m["cached"] - 0.075) < 0.01
    assert abs(c54m["output"] - 0.45) < 0.01

    # gpt-5.3-codex-spark: in=$1.75, cache=$0.175, out=$14
    tspark = ctu.ModelTotals(model="gpt-5.3-codex-spark",
                             uncached_input=1_000_000, cached_input=1_000_000,
                             output=100_000, reasoning=0)
    cspark = tspark.cost(ctu.PRICING)
    assert abs(cspark["input"] - 1.75) < 0.01
    assert abs(cspark["cached"] - 0.175) < 0.01
    assert abs(cspark["output"] - 1.40) < 0.01


def test_model_totals_cost_minimax_m3():
    """MiniMax-M3 uses its own list rates."""
    t = ctu.ModelTotals(model="MiniMax-M3", uncached_input=1_000_000,
                        cached_input=1_000_000, output=100_000, reasoning=0)
    c = t.cost(ctu.PRICING)
    assert abs(c["input"] - 0.60) < 0.01
    assert abs(c["cached"] - 0.12) < 0.01
    assert abs(c["output"] - 0.24) < 0.01


def test_model_totals_cost_unknown_model():
    """Unknown models with no API pricing are billed at zero."""
    totals = ctu.ModelTotals(
        model="unknown-model",
        sessions=1,
        uncached_input=1_000_000,
        cached_input=0,
        output=0,
        reasoning=0,
    )
    cost = totals.cost(ctu.PRICING)
    # DEFAULT_PRICING is zero for all categories
    assert cost["input"] == 0.0
    assert cost["cached"] == 0.0
    assert cost["output"] == 0.0
    assert cost["total"] == 0.0


def test_billable_output_includes_reasoning():
    """billable_output = output + reasoning."""
    totals = ctu.ModelTotals(
        model="gpt-5.5", output=1000, reasoning=500,
    )
    assert totals.billable_output == 1500


# ---------------------------------------------------------------------------
# Report tests
# ---------------------------------------------------------------------------

def test_compute_report_structure():
    """Report has expected top-level keys and model entries."""
    per_model = {
        "gpt-5.5": ctu.ModelTotals(
            model="gpt-5.5", sessions=2,
            uncached_input=1000, cached_input=5000,
            output=100, reasoning=50,
        ),
    }
    report = ctu.compute_report(per_model)
    assert "models" in report
    assert "totals" in report
    assert "pricing" in report
    assert "gpt-5.5" in report["models"]
    assert report["totals"]["sessions"] == 2
    assert report["totals"]["billable_output"] == 150
    assert report["totals"]["total_input"] == 6000


def test_compute_report_grand_totals():
    """Grand totals sum across all models."""
    per_model = {
        "gpt-5.5": ctu.ModelTotals(
            model="gpt-5.5", sessions=1,
            uncached_input=1000, cached_input=5000,
            output=100, reasoning=50,
        ),
        "gpt-5.6-sol": ctu.ModelTotals(
            model="gpt-5.6-sol", sessions=2,
            uncached_input=2000, cached_input=10000,
            output=200, reasoning=100,
        ),
    }
    report = ctu.compute_report(per_model)
    assert report["totals"]["sessions"] == 3
    assert report["totals"]["uncached_input"] == 3000
    assert report["totals"]["cached_input"] == 15000
    assert report["totals"]["output"] == 300
    assert report["totals"]["reasoning"] == 150
    assert report["totals"]["billable_output"] == 450


# ---------------------------------------------------------------------------
# End-to-end test
# ---------------------------------------------------------------------------

def test_end_to_end_with_fixtures():
    """Full pipeline: Codex CLI rollouts + Hermes DB → merged report."""
    with tempfile.TemporaryDirectory() as d:
        # Codex CLI sessions
        codex_dir = Path(d) / "codex" / "sessions"
        s1_dir = codex_dir / "2026" / "07" / "06"
        s1_dir.mkdir(parents=True)
        _write_codex_rollout(
            s1_dir / "rollout-2026-07-06T22-56-12-aaa-bbb-ccc-ddd-eee.jsonl",
            "aaa-bbb-ccc-ddd-eee",
            "gpt-5.5",
            input_tokens=200000,
            cached_input_tokens=150000,
            output_tokens=1000,
            reasoning=200,
        )

        # Hermes DB
        db_path = Path(d) / "hermes" / "state.db"
        db_path.parent.mkdir(parents=True)
        _make_hermes_db(db_path, [
            ("h1", "gpt-5.5", "openai-codex", "subscription_included",
             500000, 5000, 5000000, 0, 1000),
            ("h2", "gpt-5.6-sol", "openai-codex", "subscription_included",
             1000000, 10000, 10000000, 0, 2000),
            ("h3", "grok-composer-2.5-fast", "xai-oauth", "",
             999, 99, 999, 0, 0),  # should be filtered out
        ])

        codex = ctu.load_codex_sessions(str(codex_dir))
        hermes = ctu.load_hermes_sessions(str(db_path))
        per_model = ctu.merge_usage(codex, hermes)
        report = ctu.compute_report(per_model)

        # gpt-5.5: 1 Codex + 1 Hermes = 2 sessions
        assert report["models"]["gpt-5.5"]["sessions"] == 2
        # Codex: uncached=50K, cached=150K, out=1000, reason=200
        # Hermes: uncached=500K, cached=5M, out=5000, reason=1000
        assert report["models"]["gpt-5.5"]["uncached_input"] == 550000
        assert report["models"]["gpt-5.5"]["cached_input"] == 5150000
        assert report["models"]["gpt-5.5"]["billable_output"] == 7200

        # gpt-5.6-sol: 1 Hermes session
        assert report["models"]["gpt-5.6-sol"]["sessions"] == 1
        assert report["models"]["gpt-5.6-sol"]["uncached_input"] == 1000000

        # Grok should be filtered out
        assert "grok-composer-2.5-fast" not in report["models"]

        # Grand totals
        assert report["totals"]["sessions"] == 3
