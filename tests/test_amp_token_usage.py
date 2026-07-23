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
    assert parsed == {
        "display": "$0.72 (free)",
        "amount_usd": 0.72,
        "bucket": "free",
        "billing_route": "amp-credits",
        "free_amount": 0.72,
        "paid_amount": 0.0,
    }


def test_parse_amp_display_cost_split():
    """Split costs like '$9.42 (free) + $1.66' are parsed correctly."""
    parsed = atu.parse_amp_display_cost("$9.42 (free) + $1.66\nDetails: ...")
    assert parsed["amount_usd"] == 11.08
    assert parsed["billing_route"] == "amp-credits"
    assert parsed["free_amount"] == 9.42
    assert parsed["paid_amount"] == 1.66


def test_parse_amp_display_cost_unavailable():
    """Subscription-routed threads show 'unavailable' with no Amp credit cost."""
    parsed = atu.parse_amp_display_cost("Usage information is currently unavailable for this thread.\nDetails: ...")
    assert parsed["amount_usd"] is None
    assert parsed["billing_route"] == "subscription"


def test_parse_amp_display_cost_paid_only():
    """Paid-only costs (no '(free)' bucket) route to amp-credits."""
    parsed = atu.parse_amp_display_cost("$0.11\nDetails: ...")
    assert parsed["amount_usd"] == 0.11
    assert parsed["billing_route"] == "amp-credits"
    assert parsed["free_amount"] == 0.0
    assert parsed["paid_amount"] == 0.11


def test_provider_for_model():
    assert atu.provider_for_model("gpt-5.6-sol") == "OpenAI"
    assert atu.provider_for_model("accounts/fireworks/models/glm-5p2") == "Fireworks"
    assert atu.provider_for_model("grok-4.5") == "xAI"
    assert atu.provider_for_model("claude-fable-5") == "Anthropic"
    assert atu.provider_for_model("gpt-5.4-2026-03-05") == "OpenAI"
    assert atu.provider_for_model("unknown-model") == "Unknown"


def test_compute_report_billing_routes():
    """Report includes billing route summary with subscription-eligibility-based routing."""
    thread = atu.thread_usage_from_export(_export_payload())  # gpt-5.5 → OpenAI → ChatGPT
    thread.amp_cost = {
        "display": "$5.00 (free)",
        "amount_usd": 5.0,
        "bucket": "free",
        "billing_route": "amp-credits",
        "free_amount": 5.0,
        "paid_amount": 0.0,
    }
    report = atu.compute_report([thread], atu.load_pricing(None))
    routes = report["billing_routes"]
    # gpt-5.5 is OpenAI → subscription route (ChatGPT), even though amp-credits was reported
    sub_routes = [r for r in routes if r["route"] == "subscription"]
    assert len(sub_routes) == 1
    assert sub_routes[0]["provider"] == "ChatGPT Plus/Pro"
    assert sub_routes[0]["threads"] == 1
    assert sub_routes[0]["implied_api_cost"] > 0
    # Amp cost is ancillary, not amp_credit_cost
    assert sub_routes[0]["amp_ancillary_cost"] == 5.0
    assert sub_routes[0]["amp_credit_cost"] == 0.0
    assert sub_routes[0]["unpriced_models"] == []


def test_billing_routes_track_unpriced_models():
    """Threads with unpriced models are tracked so amp_credit > implied is explainable."""
    payload = _export_payload()
    for msg in payload["messages"]:
        if isinstance(msg, dict) and "usage" in msg:
            msg["usage"]["model"] = "some-unpriced-model"
    thread = atu.thread_usage_from_export(payload)
    thread.amp_cost = {
        "display": "$2.00",
        "amount_usd": 2.0,
        "bucket": None,
        "billing_route": "amp-credits",
        "free_amount": 0.0,
        "paid_amount": 2.0,
    }
    report = atu.compute_report([thread], atu.load_pricing(None))
    routes = report["billing_routes"]
    # Unknown provider → no subscription → amp-credits route
    amp_route = [r for r in routes if r["route"] == "amp-credits"][0]
    assert amp_route["unpriced_models"] == ["some-unpriced-model"]
    assert amp_route["implied_api_cost"] == 0.0
    assert amp_route["amp_credit_cost"] == 2.0


def test_amp_credits_route_for_non_openai():
    """Non-subscription models (e.g. GLM/Fireworks) route to amp-credits."""
    payload = _export_payload()
    for msg in payload["messages"]:
        if isinstance(msg, dict) and "usage" in msg:
            msg["usage"]["model"] = "accounts/fireworks/models/glm-5p2"
    thread = atu.thread_usage_from_export(payload)
    thread.amp_cost = {
        "display": "$0.50 (free)",
        "amount_usd": 0.50,
        "bucket": "free",
        "billing_route": "amp-credits",
        "free_amount": 0.50,
        "paid_amount": 0.0,
    }
    report = atu.compute_report([thread], atu.load_pricing(None))
    routes = report["billing_routes"]
    # GLM/Fireworks has no linked subscription → amp-credits
    amp_routes = [r for r in routes if r["route"] == "amp-credits"]
    assert len(amp_routes) == 1
    assert amp_routes[0]["threads"] == 1
    assert amp_routes[0]["implied_api_cost"] > 0
    assert amp_routes[0]["amp_credit_cost"] == 0.50
    assert amp_routes[0]["unpriced_models"] == []


def test_openai_subscription_route_even_with_amp_cost():
    """OpenAI threads route to ChatGPT subscription even when Amp shows a dollar cost.

    The Amp dollar amount is ancillary overhead (tool calls, web search),
    not per-token LLM cost. The LLM tokens went through the linked ChatGPT
    subscription.
    """
    thread = atu.thread_usage_from_export(_export_payload())
    thread.amp_cost = {
        "display": "$0.44 (free)",
        "amount_usd": 0.44,
        "bucket": "free",
        "billing_route": "amp-credits",
        "free_amount": 0.44,
        "paid_amount": 0.0,
    }
    report = atu.compute_report([thread], atu.load_pricing(None))
    routes = report["billing_routes"]
    # OpenAI → ChatGPT subscription, regardless of amp threads usage output
    sub_routes = [r for r in routes if r["route"] == "subscription"]
    assert len(sub_routes) == 1
    assert sub_routes[0]["provider"] == "ChatGPT Plus/Pro"
    assert sub_routes[0]["amp_ancillary_cost"] == 0.44
    # No amp-credits route
    amp_routes = [r for r in routes if r["route"] == "amp-credits"]
    assert len(amp_routes) == 0


def test_xai_subscription_route():
    """xAI models route to X Premium+/SuperGrok subscription."""
    payload = _export_payload()
    for msg in payload["messages"]:
        if isinstance(msg, dict) and "usage" in msg:
            msg["usage"]["model"] = "grok-4.5"
    thread = atu.thread_usage_from_export(payload)
    thread.amp_cost = {
        "display": "Usage information is currently unavailable for this thread.",
        "amount_usd": None,
        "bucket": None,
        "billing_route": "subscription",
        "free_amount": None,
        "paid_amount": None,
    }
    report = atu.compute_report([thread], atu.load_pricing(None))
    routes = report["billing_routes"]
    sub_routes = [r for r in routes if r["route"] == "subscription"]
    assert len(sub_routes) == 1
    assert sub_routes[0]["provider"] == "X Premium+/SuperGrok"


def test_mixed_provider_thread_routes_to_amp_credits():
    """A thread mixing subscription-eligible and non-subscription models routes to amp-credits."""
    payload = _export_payload()
    # First event: gpt-5.5 (OpenAI/ChatGPT), second: GLM (Fireworks/no subscription)
    payload["messages"][1]["usage"]["model"] = "gpt-5.5"
    payload["messages"][2]["usage"]["model"] = "accounts/fireworks/models/glm-5p2"
    thread = atu.thread_usage_from_export(payload)
    thread.amp_cost = {
        "display": "$3.00 (free)",
        "amount_usd": 3.0,
        "bucket": "free",
        "billing_route": "amp-credits",
        "free_amount": 3.0,
        "paid_amount": 0.0,
    }
    report = atu.compute_report([thread], atu.load_pricing(None))
    routes = report["billing_routes"]
    # Mixed providers → can't attribute to one subscription → amp-credits
    amp_routes = [r for r in routes if r["route"] == "amp-credits"]
    assert len(amp_routes) == 1
    assert amp_routes[0]["amp_credit_cost"] == 3.0


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


def test_glm_5p2_pricing_matches_alias():
    """The Amp model identifier accounts/fireworks/models/glm-5p2 resolves to GLM-5.2 pricing."""
    pricing = atu.load_pricing(None)
    price = atu.pricing_for_model("accounts/fireworks/models/glm-5p2", pricing)
    assert price is not None
    assert price["input"] == 1.40
    assert price["output"] == 4.40


def test_grok_4_5_pricing():
    """grok-4.5 has API pricing ($2/$0.50/$6 per 1M)."""
    pricing = atu.load_pricing(None)
    assert "grok-4.5" in pricing
    price = atu.pricing_for_model("grok-4.5", pricing)
    assert price is not None
    assert price["input"] == 2.00
    assert price["cache_read"] == 0.50
    assert price["output"] == 6.00


def test_claude_fable_5_pricing():
    """claude-fable-5 has API pricing ($10/$1/$50 per 1M)."""
    pricing = atu.load_pricing(None)
    assert "claude-fable-5" in pricing
    price = atu.pricing_for_model("claude-fable-5", pricing)
    assert price is not None
    assert price["input"] == 10.00
    assert price["cache_read"] == 1.00
    assert price["output"] == 50.00
