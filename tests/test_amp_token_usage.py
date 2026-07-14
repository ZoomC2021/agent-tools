"""Tests for scripts/amp-token-usage.py."""

import importlib.util
import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from importlib.machinery import SourceFileLoader
from pathlib import Path

_script_path = Path(__file__).resolve().parent.parent / "scripts" / "amp-token-usage.py"
_loader = SourceFileLoader("amp_token_usage", str(_script_path))
_spec = importlib.util.spec_from_loader(_loader.name, _loader)
atu = importlib.util.module_from_spec(_spec)
sys.modules["amp_token_usage"] = atu
assert _spec.loader is not None
_spec.loader.exec_module(atu)


def _export_payload(thread_id: str = "T-1", title: str = "Thread") -> dict:
    return {
        "id": thread_id,
        "title": title,
        "created": "2026-07-07T00:00:00.000Z",
        "updatedAt": "2026-07-07T01:00:00.000Z",
        "messages": [
            {"role": "user", "content": "hello"},
            {
                "role": "assistant",
                "usage": {
                    "model": "gpt-5.5",
                    "timestamp": "2026-07-07T00:01:00.000Z",
                    "inputTokens": 100,
                    "totalInputTokens": 1000,
                    "outputTokens": 50,
                    "cacheReadInputTokens": 500,
                    "cacheCreationInputTokens": 400,
                    "maxInputTokens": 272000,
                },
            },
            {
                "role": "assistant",
                "usage": {
                    "model": "gpt-5.5",
                    "timestamp": "2026-07-07T00:02:00.000Z",
                    "inputTokens": 0,
                    "totalInputTokens": 1600,
                    "outputTokens": 80,
                    "cacheReadInputTokens": 1200,
                    "cacheCreationInputTokens": 0,
                    "maxInputTokens": 272000,
                },
            },
        ],
    }


def _write_export(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_thread_usage_from_export_extracts_usage_events():
    thread = atu.thread_usage_from_export(_export_payload(), source="fixture")
    assert thread.thread_id == "T-1"
    assert thread.title == "Thread"
    assert thread.message_count == 3
    assert thread.calls == 2
    assert thread.total_input_tokens == 2600
    assert thread.cache_read_input_tokens == 1700
    assert thread.cache_creation_input_tokens == 400
    assert thread.output_tokens == 130
    assert thread.billable_input_tokens == 900


def test_usage_event_falls_back_when_total_input_missing():
    event = atu.usage_event_from_dict({
        "model": "x",
        "inputTokens": 10,
        "cacheReadInputTokens": 20,
        "cacheCreationInputTokens": 30,
        "outputTokens": 5,
    })
    assert event.total_input_tokens == 60
    assert event.output_tokens == 5


def test_load_export_file_rejects_non_object_json():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "bad.json"
        path.write_text("[]", encoding="utf-8")
        try:
            atu.load_export_file(str(path))
        except ValueError as exc:
            assert "not an Amp thread export object" in str(exc)
        else:
            raise AssertionError("expected ValueError")


def test_aggregate_by_model_counts_distinct_threads():
    first = atu.thread_usage_from_export(_export_payload("T-1", "One"))
    second_payload = _export_payload("T-2", "Two")
    second_payload["messages"][1]["usage"]["model"] = "GLM-5.2"
    second_payload["messages"][2]["usage"]["model"] = "GLM-5.2"
    second = atu.thread_usage_from_export(second_payload)
    per_model = atu.aggregate_by_model([first, second])
    assert per_model["gpt-5.5"].threads == 1
    assert per_model["gpt-5.5"].calls == 2
    assert per_model["gpt-5.5"].total_input_tokens == 2600
    assert per_model["GLM-5.2"].threads == 1
    assert per_model["GLM-5.2"].output_tokens == 130


def test_compute_report_includes_cost_estimates():
    thread = atu.thread_usage_from_export(_export_payload())
    report = atu.compute_report([thread], atu.load_pricing(None))
    model = report["models"]["gpt-5.5"]
    assert report["totals"]["threads"] == 1
    assert report["totals"]["calls"] == 2
    assert model["estimated_cost"]["total"] > 0
    assert model["cache_read_pct"] > 60


def test_parse_amp_display_cost():
    parsed = atu.parse_amp_display_cost("$0.72 (free)\nDetails: https://example.test")
    assert parsed == {"display": "$0.72 (free)", "amount_usd": 0.72, "bucket": "free"}


def test_load_pricing_accepts_devin_style_keys():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "pricing.json"
        path.write_text(json.dumps({"custom/model": {"in": 2, "cache": 0.2, "out": 8}}), encoding="utf-8")
        pricing = atu.load_pricing(str(path))
        assert pricing["custom/model"] == {"input": 2.0, "cache_read": 0.2, "output": 8.0}


def test_main_json_output_from_export_file():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "thread.json"
        _write_export(path, _export_payload())
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = atu.main(["--export", str(path), "--json"])
        assert rc == 0
        data = json.loads(buf.getvalue())
        assert data["models"]["gpt-5.5"]["calls"] == 2
        assert data["threads"][0]["id"] == "T-1"


def test_main_export_dir_loads_json_files():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_export(root / "one.json", _export_payload("T-1", "One"))
        _write_export(root / "two.json", _export_payload("T-2", "Two"))
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = atu.main(["--export-dir", str(root), "--json"])
        data = json.loads(buf.getvalue())
        assert rc == 0
        assert data["totals"]["threads"] == 2
        assert data["models"]["gpt-5.5"]["calls"] == 4


def test_main_returns_error_for_missing_export():
    rc = atu.main(["--export", "/nonexistent/thread.json", "--json"])
    assert rc == 2


def test_pricing_for_model_matches_dated_variant():
    pricing = atu.load_pricing(None)
    assert atu.pricing_for_model("gpt-5.4-2026-03-05", pricing) == pricing["gpt-5.4"]
    assert atu.pricing_for_model("gpt-5.5-2026-04-23", pricing) == pricing["gpt-5.5"]
    assert atu.pricing_for_model("gpt-5.6-sol", pricing) == pricing["gpt-5.6-sol"]
    assert atu.pricing_for_model("claude-opus-4-6", pricing) is None


def test_live_thread_list_uses_injected_amp_json(monkeypatch):
    calls = []

    def fake_run_amp_json(amp_bin, args):
        calls.append((amp_bin, args))
        return [{"id": "T-1"}, {"id": "T-2"}]

    monkeypatch.setattr(atu, "run_amp_json", fake_run_amp_json)
    ids = atu.list_amp_thread_ids("amp-test", 2, True)
    assert ids == ["T-1", "T-2"]
    assert calls == [("amp-test", ["threads", "list", "--limit", "2", "--json", "--include-archived"])]


# ---------------------------------------------------------------------------
# Date filter tests
# ---------------------------------------------------------------------------

def test_list_amp_thread_ids_since_filter(monkeypatch):
    """--since filters out threads updated before the given date."""
    def fake_run_amp_json(amp_bin, args):
        return [
            {"id": "T-old", "updated": "2026-07-10T10:00:00.000Z"},
            {"id": "T-new", "updated": "2026-07-13T10:00:00.000Z"},
        ]
    monkeypatch.setattr(atu, "run_amp_json", fake_run_amp_json)
    ids = atu.list_amp_thread_ids("amp", 100, False, since="2026-07-13")
    assert ids == ["T-new"]


def test_list_amp_thread_ids_until_filter(monkeypatch):
    """--until filters out threads updated after the given date."""
    def fake_run_amp_json(amp_bin, args):
        return [
            {"id": "T-old", "updated": "2026-07-10T10:00:00.000Z"},
            {"id": "T-new", "updated": "2026-07-13T10:00:00.000Z"},
        ]
    monkeypatch.setattr(atu, "run_amp_json", fake_run_amp_json)
    ids = atu.list_amp_thread_ids("amp", 100, False, until="2026-07-10")
    assert ids == ["T-old"]


def test_list_amp_thread_ids_date_range(monkeypatch):
    """--since + --until selects only threads within the inclusive range."""
    def fake_run_amp_json(amp_bin, args):
        return [
            {"id": "T-09", "updated": "2026-07-09T10:00:00.000Z"},
            {"id": "T-10", "updated": "2026-07-10T10:00:00.000Z"},
            {"id": "T-11", "updated": "2026-07-11T10:00:00.000Z"},
            {"id": "T-12", "updated": "2026-07-12T10:00:00.000Z"},
        ]
    monkeypatch.setattr(atu, "run_amp_json", fake_run_amp_json)
    ids = atu.list_amp_thread_ids("amp", 100, False, since="2026-07-10", until="2026-07-11")
    assert ids == ["T-10", "T-11"]


def test_thread_in_date_range_uses_updated_field():
    """_thread_in_date_range checks the thread's updated timestamp."""
    thread = atu.ThreadUsage(
        thread_id="T-1", updated="2026-07-13T10:00:00.000Z",
        created="2026-07-13T09:00:00.000Z",
    )
    since_e = atu._date_to_epoch("2026-07-13")
    until_e = atu._date_to_epoch("2026-07-13") + 86400
    assert atu._thread_in_date_range(thread, since_e, until_e) is True
    # Outside range
    assert atu._thread_in_date_range(thread, atu._date_to_epoch("2026-07-14"), None) is False


def test_thread_in_date_range_falls_back_to_event_timestamp():
    """When updated/created are missing, fall back to last event timestamp."""
    thread = atu.ThreadUsage(thread_id="T-1")
    thread.events.append(atu.UsageEvent(timestamp="2026-07-13T10:00:00.000Z"))
    since_e = atu._date_to_epoch("2026-07-13")
    until_e = atu._date_to_epoch("2026-07-13") + 86400
    assert atu._thread_in_date_range(thread, since_e, until_e) is True


def test_main_since_filter_on_export_file():
    """--since filters threads loaded from export files by updated date."""
    with tempfile.TemporaryDirectory() as tmp:
        old_payload = _export_payload("T-old", "Old")
        old_payload["updatedAt"] = "2026-07-10T10:00:00.000Z"
        new_payload = _export_payload("T-new", "New")
        new_payload["updatedAt"] = "2026-07-13T10:00:00.000Z"
        _write_export(Path(tmp) / "old.json", old_payload)
        _write_export(Path(tmp) / "new.json", new_payload)
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = atu.main(["--export-dir", str(tmp), "--since", "2026-07-13", "--json"])
        assert rc == 0
        data = json.loads(buf.getvalue())
        assert data["totals"]["threads"] == 1
        assert data["threads"][0]["id"] == "T-new"
        assert data["since"] == "2026-07-13"


# ---------------------------------------------------------------------------
# Pricing table tests
# ---------------------------------------------------------------------------

def test_default_pricing_includes_gpt_5_6_models():
    """The expanded pricing table includes gpt-5.6-sol and related models."""
    pricing = atu.load_pricing(None)
    assert "gpt-5.6-sol" in pricing
    assert pricing["gpt-5.6-sol"] == {"input": 5.00, "cache_read": 0.50, "output": 30.00}
    assert "gpt-5.6-luna" in pricing
    assert pricing["gpt-5.6-luna"]["output"] == 6.00
    assert "gpt-5.6-terra" in pricing
    assert "gpt-5.4" in pricing
    assert "gpt-5.4-mini" in pricing
    assert "gpt-5.3-codex-spark" in pricing
    assert "MiniMax-M3" in pricing


def test_gpt_5_6_sol_cost_estimated():
    """gpt-5.6-sol usage now produces a non-null estimated cost."""
    payload = _export_payload()
    for msg in payload["messages"]:
        if isinstance(msg, dict) and "usage" in msg:
            msg["usage"]["model"] = "gpt-5.6-sol"
    thread = atu.thread_usage_from_export(payload)
    report = atu.compute_report([thread], atu.load_pricing(None))
    model = report["models"]["gpt-5.6-sol"]
    assert model["estimated_cost"] is not None
    assert model["estimated_cost"]["total"] > 0
