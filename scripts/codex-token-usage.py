#!/usr/bin/env python3
"""Count ChatGPT/Codex subscription token usage from Codex CLI session
rollouts and Hermes agent state, and compute the implied API value — what
the same tokens would cost at full provider API rates.

This lets you see how much value your ChatGPT/Codex subscription delivers
by comparing the included usage against equivalent pay-as-you-go API pricing.

ChatGPT/Codex subscription usage is tracked in two places on this machine:

1. **Codex CLI sessions** — JSONL rollout files under
   ``~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl``, one per CLI session.
   Each file contains ``token_count`` event messages whose final
   ``total_token_usage`` block holds cumulative ``input_tokens``,
   ``cached_input_tokens``, ``output_tokens``, and
   ``reasoning_output_tokens``.  The model is read from ``turn_context``
   events; the subscription plan from ``rate_limits``.

2. **Hermes agent state** — the SQLite database at
   ``~/.hermes/state.db`` has a ``session_model_usage`` table with
   per-session per-model token counts (``input_tokens``,
   ``cache_read_tokens``, ``output_tokens``, ``reasoning_tokens``) and a
   ``billing_provider`` column.  Only rows with
   ``billing_provider = 'openai-codex'`` are counted (these route through
   the ChatGPT/Codex subscription endpoint at ``chatgpt.com/backend-api/codex``).

In Codex CLI rollouts, ``input_tokens`` **includes** cached tokens, so
uncached input = ``input_tokens - cached_input_tokens``.  In Hermes,
``input_tokens`` and ``cache_read_tokens`` are separate columns.
Reasoning tokens are billed at the output rate in both sources.

Usage::

    scripts/codex-token-usage.py                # full report
    scripts/codex-token-usage.py --json         # machine-readable JSON
    scripts/codex-token-usage.py --no-codex     # Hermes only
    scripts/codex-token-usage.py --no-hermes    # Codex CLI only
    scripts/codex-token-usage.py --all-providers # include non-Codex Hermes providers
    scripts/codex-token-usage.py --since 2026-07-13            # only sessions on/after date
    scripts/codex-token-usage.py --since 2026-07-13 --until 2026-07-13  # single day
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------

HOME = os.path.expanduser("~")
DEFAULT_CODEX_SESSION_DIR = os.path.join(HOME, ".codex", "sessions")
DEFAULT_HERMES_DB = os.path.join(HOME, ".hermes", "state.db")

# ---------------------------------------------------------------------------
# Pricing (USD per 1M tokens, list API rates)
# ---------------------------------------------------------------------------

PRICING = {
    # OpenAI frontier / professional
    "gpt-5.5":              {"in": 5.00, "cache": 0.50, "out": 30.00},
    "gpt-5.6-sol":          {"in": 5.00, "cache": 0.50, "out": 30.00},
    "gpt-5.6-luna":         {"in": 1.00, "cache": 0.10, "out": 6.00},
    "gpt-5.6-terra":        {"in": 2.50, "cache": 0.25, "out": 15.00},
    # OpenAI older / coding models
    "gpt-5.4":              {"in": 2.50, "cache": 0.25, "out": 15.00},
    "gpt-5.4-mini":         {"in": 0.75, "cache": 0.075,"out": 4.50},
    "gpt-5.3-codex-spark":  {"in": 1.75, "cache": 0.175,"out": 14.00},
    # Third-party (via Hermes)
    "MiniMax-M3":           {"in": 0.60, "cache": 0.12, "out": 2.40},
}

# Fallback for models without known API pricing: bill at zero
DEFAULT_PRICING = {"in": 0.0, "cache": 0.0, "out": 0.0}

# Hermes billing providers that route through the ChatGPT/Codex subscription
CODEX_BILLING_PROVIDERS = {"openai-codex"}

# Human-readable subscription names for billing providers
PROVIDER_DISPLAY_NAMES = {
    "openai-codex": "ChatGPT Plus/Pro",
    "xai-oauth": "X Premium+/SuperGrok",
}


# ---------------------------------------------------------------------------
# Date filtering helpers
# ---------------------------------------------------------------------------

def _parse_date(s: str) -> str:
    """Validate and normalize a YYYY-MM-DD date string."""
    datetime.strptime(s, "%Y-%m-%d")
    return s


def _date_to_epoch(d: str) -> float:
    """Convert YYYY-MM-DD to unix epoch at start-of-day UTC."""
    return datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()


# rollout-YYYY-MM-DDT... filename prefix
_ROLLOUT_DATE_RE = re.compile(r"rollout-(\d{4}-\d{2}-\d{2})T")


def _rollout_date(path: str) -> Optional[str]:
    """Extract the YYYY-MM-DD date from a rollout filename, or None."""
    m = _ROLLOUT_DATE_RE.search(os.path.basename(path))
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SessionUsage:
    """Token usage for a single session from one source."""
    model: str = "unknown"
    uncached_input: int = 0
    cached_input: int = 0
    output: int = 0        # excludes reasoning
    reasoning: int = 0
    source: str = ""       # "codex-cli" or "hermes"
    plan: str = ""         # subscription plan (e.g. "plus", "pro")
    provider: str = ""     # billing provider (e.g. "openai-codex", "xai-oauth")


@dataclass
class ModelTotals:
    """Aggregated totals for one model."""
    model: str = ""
    sessions: int = 0
    uncached_input: int = 0
    cached_input: int = 0
    output: int = 0        # excludes reasoning
    reasoning: int = 0
    sources: set[str] = field(default_factory=set)
    providers: set[str] = field(default_factory=set)

    @property
    def billable_output(self) -> int:
        """Output tokens billed at the output rate (output + reasoning)."""
        return self.output + self.reasoning

    @property
    def total_input(self) -> int:
        return self.uncached_input + self.cached_input

    def cost(self, pricing: dict[str, dict[str, float]]) -> dict[str, float]:
        p = pricing.get(self.model, DEFAULT_PRICING)
        in_cost = self.uncached_input / 1_000_000 * p["in"]
        cache_cost = self.cached_input / 1_000_000 * p["cache"]
        out_cost = self.billable_output / 1_000_000 * p["out"]
        return {
            "input": in_cost,
            "cached": cache_cost,
            "output": out_cost,
            "total": in_cost + cache_cost + out_cost,
        }


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_codex_sessions(
    session_dir: str,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> dict[str, SessionUsage]:
    """Load token usage from Codex CLI session rollout JSONL files.

    Returns a dict mapping session_id to SessionUsage.  Sessions without
    any ``token_count`` events are omitted.  When ``since``/``until`` are
    provided (YYYY-MM-DD), only sessions dated within that inclusive
    range are loaded (date parsed from the rollout filename).
    """
    result: dict[str, SessionUsage] = {}
    pattern = os.path.join(session_dir, "**", "rollout-*.jsonl")
    for path in sorted(glob.glob(pattern, recursive=True)):
        if since or until:
            fdate = _rollout_date(path)
            if fdate is None:
                continue  # can't date-filter undated files
            if since and fdate < since:
                continue
            if until and fdate > until:
                continue
        sid = os.path.basename(path)
        # Strip rollout- prefix and split timestamp from UUID
        # rollout-2026-06-29T18-53-50-019f1303-...-....jsonl
        if sid.startswith("rollout-"):
            sid = sid[len("rollout-"):]
        if sid.endswith(".jsonl"):
            sid = sid[:-len(".jsonl")]
        # The UUID is the last part after the timestamp
        # Try to extract it: timestamp ends at first UUID-like segment
        parts = sid.split("-", 3)  # split into date, time, seconds, rest
        if len(parts) >= 4:
            sid = parts[3]  # the UUID part

        model = "unknown"
        plan = ""
        total_usage = None

        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    ptype = entry.get("type", "")

                    # Extract model from turn_context events
                    if ptype == "turn_context":
                        m = entry.get("payload", {}).get("model", "")
                        if m:
                            model = m

                    # Extract plan from token_count rate_limits
                    if ptype == "event_msg":
                        payload = entry.get("payload", {})
                        if payload.get("type") == "token_count":
                            info = payload.get("info") or {}
                            total_usage = info.get("total_token_usage")
                            rate_limits = payload.get("rate_limits") or {}
                            plan = rate_limits.get("plan_type", plan)
        except OSError:
            continue

        if total_usage is None:
            continue  # no token_count events in this session

        # In Codex CLI, input_tokens includes cached_input_tokens
        raw_input = total_usage.get("input_tokens", 0)
        cached = total_usage.get("cached_input_tokens", 0)
        uncached = max(raw_input - cached, 0)
        output = total_usage.get("output_tokens", 0)
        reasoning = total_usage.get("reasoning_output_tokens", 0)

        result[f"codex-{sid}"] = SessionUsage(
            model=model,
            uncached_input=uncached,
            cached_input=cached,
            output=output,
            reasoning=reasoning,
            source="codex-cli",
            plan=plan,
            provider="openai-codex",
        )
    return result


def load_hermes_sessions(
    db_path: str,
    all_providers: bool = False,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> dict[str, SessionUsage]:
    """Load token usage from the Hermes agent state database.

    Returns a dict mapping
    ``hermes-{session_id}-{model}-{billing_provider}-{billing_base_url}-{billing_mode}-{task}``
    to SessionUsage.  Only rows with ``billing_provider = 'openai-codex'``
    are included unless ``all_providers`` is True.  When ``since``/``until``
    are provided (YYYY-MM-DD), only rows with ``last_seen`` within that
    inclusive range are loaded.
    """
    result: dict[str, SessionUsage] = {}
    if not os.path.exists(db_path):
        return result

    # Build optional date filter on last_seen (unix epoch REAL)
    date_conditions: list[str] = []
    date_params: list = []
    if since:
        date_conditions.append("last_seen >= ?")
        date_params.append(_date_to_epoch(since))
    if until:
        # end of day: +86400 seconds
        date_conditions.append("last_seen < ?")
        date_params.append(_date_to_epoch(until) + 86400)

    date_clause = ""
    if date_conditions:
        date_clause = " AND " + " AND ".join(date_conditions)

    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        if all_providers:
            cur.execute(
                "SELECT session_id, model, billing_provider, billing_base_url, "
                "billing_mode, task, "
                "input_tokens, output_tokens, cache_read_tokens, "
                "cache_write_tokens, reasoning_tokens "
                "FROM session_model_usage WHERE 1=1" + date_clause,
                date_params,
            )
        else:
            placeholders = ",".join("?" * len(CODEX_BILLING_PROVIDERS))
            cur.execute(
                f"SELECT session_id, model, billing_provider, billing_base_url, "
                f"billing_mode, task, "
                f"input_tokens, output_tokens, cache_read_tokens, "
                f"cache_write_tokens, reasoning_tokens "
                f"FROM session_model_usage "
                f"WHERE billing_provider IN ({placeholders})"
                f"{date_clause}",
                list(CODEX_BILLING_PROVIDERS) + date_params,
            )
        for row in cur.fetchall():
            (sid, model, provider, base_url, mode, task,
             inp, out, cache_read, cache_write, reasoning) = row
            # In Hermes, input_tokens and cache_read_tokens are separate
            # (input_tokens = uncached input)
            key = f"hermes-{sid}-{model}-{provider}-{base_url}-{mode}-{task}"
            result[key] = SessionUsage(
                model=model,
                uncached_input=inp,
                cached_input=cache_read,
                output=out,
                reasoning=reasoning,
                source=f"hermes:{provider}",
                provider=provider,
            )
        con.close()
    except sqlite3.Error:
        pass
    return result


# ---------------------------------------------------------------------------
# Merge logic
# ---------------------------------------------------------------------------

def merge_usage(
    codex: dict[str, SessionUsage],
    hermes: dict[str, SessionUsage],
) -> dict[str, ModelTotals]:
    """Merge Codex CLI and Hermes session usage into per-model totals."""
    per_model: dict[str, ModelTotals] = {}

    def _get_totals(key: str) -> ModelTotals:
        if key not in per_model:
            per_model[key] = ModelTotals(model=key)
        return per_model[key]

    for usage in codex.values():
        totals = _get_totals(usage.model)
        totals.sessions += 1
        totals.uncached_input += usage.uncached_input
        totals.cached_input += usage.cached_input
        totals.output += usage.output
        totals.reasoning += usage.reasoning
        totals.sources.add(usage.source)
        if usage.provider:
            totals.providers.add(usage.provider)

    for usage in hermes.values():
        totals = _get_totals(usage.model)
        totals.sessions += 1
        totals.uncached_input += usage.uncached_input
        totals.cached_input += usage.cached_input
        totals.output += usage.output
        totals.reasoning += usage.reasoning
        totals.sources.add(usage.source)
        if usage.provider:
            totals.providers.add(usage.provider)

    return per_model


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _fmt(n: int) -> str:
    return f"{n:,}"


def compute_report(
    per_model: dict[str, ModelTotals],
    all_providers: bool = False,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> dict:
    """Compute the full report dict (for JSON output)."""
    models = {}
    grand = {
        "sessions": 0, "uncached_input": 0, "cached_input": 0,
        "output": 0, "reasoning": 0,
        "in_cost": 0.0, "cache_cost": 0.0, "out_cost": 0.0, "total": 0.0,
    }

    # Sort models: known pricing models first (in PRICING order), then unknown
    model_keys = sorted(per_model.keys(), key=lambda k: (
        list(PRICING.keys()).index(k) if k in PRICING else len(PRICING) + 1,
        k,
    ))

    for model_key in model_keys:
        totals = per_model[model_key]
        cost = totals.cost(PRICING)
        models[model_key] = {
            "sessions": totals.sessions,
            "uncached_input": totals.uncached_input,
            "cached_input": totals.cached_input,
            "output": totals.output,
            "reasoning": totals.reasoning,
            "billable_output": totals.billable_output,
            "sources": sorted(totals.sources),
            "providers": sorted(totals.providers),
            "cost": cost,
        }
        grand["sessions"] += totals.sessions
        grand["uncached_input"] += totals.uncached_input
        grand["cached_input"] += totals.cached_input
        grand["output"] += totals.output
        grand["reasoning"] += totals.reasoning
        grand["in_cost"] += cost["input"]
        grand["cache_cost"] += cost["cached"]
        grand["out_cost"] += cost["output"]
        grand["total"] += cost["total"]

    grand["billable_output"] = grand["output"] + grand["reasoning"]
    grand["total_input"] = grand["uncached_input"] + grand["cached_input"]

    # Build subscription value summary — implied API cost per billing provider
    sub_summary = _build_subscription_value(per_model)

    return {
        "models": models,
        "totals": grand,
        "subscription_value": sub_summary,
        "pricing": PRICING,
        "all_providers": all_providers,
        "since": since,
        "until": until,
        "notes": [
            "Implied API cost is what the same tokens would cost at full provider API rates.",
            "Subscription usage is included in your ChatGPT/Codex plan at no per-token cost.",
            "The gap between implied API cost and $0 actual cost is the value delivered by your subscription.",
        ],
    }


def _build_subscription_value(
    per_model: dict[str, ModelTotals],
) -> list[dict[str, Any]]:
    """Summarise implied API value by billing provider."""
    by_provider: dict[str, dict[str, Any]] = {}

    def _get(key: str) -> dict[str, Any]:
        if key not in by_provider:
            by_provider[key] = {
                "provider": key,
                "display_name": PROVIDER_DISPLAY_NAMES.get(key, key),
                "sessions": 0,
                "total_input": 0,
                "output": 0,
                "implied_api_cost": 0.0,
            }
        return by_provider[key]

    for totals in per_model.values():
        cost = totals.cost(PRICING)
        providers = totals.providers or {"openai-codex"}
        for provider in providers:
            entry = _get(provider)
            entry["sessions"] += totals.sessions
            entry["total_input"] += totals.total_input
            entry["output"] += totals.billable_output
            entry["implied_api_cost"] += cost["total"]

    return sorted(by_provider.values(), key=lambda x: x["implied_api_cost"], reverse=True)


def print_text_report(report: dict) -> None:
    """Print a human-readable cost report."""
    models = report["models"]
    grand = report["totals"]
    scope = "all providers" if report.get("all_providers") else "ChatGPT/Codex subscription"
    date_range = ""
    if report.get("since") or report.get("until"):
        lo = report.get("since") or "begin"
        hi = report.get("until") or "now"
        date_range = f"  [{lo} .. {hi}]"
    print("=" * 90)
    print(f"CHATGPT/CODEX TOKEN USAGE & IMPLIED API VALUE ({scope}){date_range}")
    print("=" * 90)
    print()
    print(f"{'Model':<16}{'Sessions':>9}  {'Uncached In':>13}{'Cached In':>13}{'Output':>11}  {'Implied Cost':>13}")
    print("-" * 90)
    for model_key, m in models.items():
        print(f"{model_key:<16}{m['sessions']:>9}  "
              f"{_fmt(m['uncached_input']):>13}{_fmt(m['cached_input']):>13}"
              f"{_fmt(m['billable_output']):>11}  {m['cost']['total']:>12.2f}$")
    print("-" * 90)
    print(f"{'TOTAL':<16}{grand['sessions']:>9}  "
          f"{_fmt(grand['uncached_input']):>13}{_fmt(grand['cached_input']):>13}"
          f"{_fmt(grand['billable_output']):>11}  {grand['total']:>12.2f}$")
    print()
    print("Implied API cost breakdown (what these tokens would cost at full API rates):")
    print(f"  Uncached input : ${grand['in_cost']:>9.2f}")
    print(f"  Cached input   : ${grand['cache_cost']:>9.2f}")
    print(f"  Output         : ${grand['out_cost']:>9.2f}")
    print(f"  TOTAL          : ${grand['total']:>9.2f}")
    print()

    # Subscription value summary
    sub_value = report.get("subscription_value", [])
    if sub_value:
        print("=" * 90)
        print("SUBSCRIPTION VALUE SUMMARY")
        print("=" * 90)
        print(f"{'Subscription':<24}{'Sessions':>9}  {'Implied API Cost':>16}  {'Actual Paid':>12}")
        print("-" * 90)
        for entry in sub_value:
            print(f"{entry['display_name']:<24}{entry['sessions']:>9}  "
                  f"${entry['implied_api_cost']:>14.2f}  {'$0.00':>12}")
        total_implied = sum(e["implied_api_cost"] for e in sub_value)
        print("-" * 90)
        print(f"{'TOTAL':<24}{'':>9}  ${total_implied:>14.2f}")
        print()
        print(f"Total subscription value: ${total_implied:.2f} in implied API costs")
        print(f"Actual per-token cost:    $0.00 (included in your subscription)")
        print()

    if grand["reasoning"] > 0:
        print(f"Reasoning tokens: {_fmt(grand['reasoning'])} (included in billable output)")
    print()
    print("Pricing used (per 1M tokens, OpenAI list API rates):")
    for model_key, p in PRICING.items():
        print(f"  {model_key:<15} input ${p['in']:.2f}  cached ${p['cache']:.2f}  output ${p['out']:.2f}")
    if grand["total_input"] > 0:
        cache_pct = grand["cached_input"] / grand["total_input"] * 100
        print(f"\n{cache_pct:.1f}% of input tokens were cache hits.")
    print()
    for note in report.get("notes", []):
        print(f"Note: {note}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Count ChatGPT/Codex subscription token usage and compute implied API value."
    )
    parser.add_argument("--session-dir", default=DEFAULT_CODEX_SESSION_DIR,
                        help="Codex CLI sessions directory (default: %(default)s)")
    parser.add_argument("--hermes-db", default=DEFAULT_HERMES_DB,
                        help="Hermes state.db path (default: %(default)s)")
    parser.add_argument("--no-codex", action="store_true",
                        help="Skip Codex CLI session processing (Hermes only)")
    parser.add_argument("--no-hermes", action="store_true",
                        help="Skip Hermes processing (Codex CLI only)")
    parser.add_argument("--all-providers", action="store_true",
                        help="Include all Hermes billing providers, not just openai-codex")
    parser.add_argument("--since", type=_parse_date, metavar="YYYY-MM-DD",
                        help="Only count sessions on/after this date")
    parser.add_argument("--until", type=_parse_date, metavar="YYYY-MM-DD",
                        help="Only count sessions on/before this date")
    parser.add_argument("--json", action="store_true",
                        help="Output machine-readable JSON instead of text")
    args = parser.parse_args(argv)

    codex: dict[str, SessionUsage] = {}
    if not args.no_codex and os.path.isdir(args.session_dir):
        codex = load_codex_sessions(args.session_dir, since=args.since, until=args.until)

    hermes: dict[str, SessionUsage] = {}
    if not args.no_hermes:
        hermes = load_hermes_sessions(args.hermes_db, all_providers=args.all_providers,
                                      since=args.since, until=args.until)

    per_model = merge_usage(codex, hermes)
    report = compute_report(per_model, all_providers=args.all_providers,
                            since=args.since, until=args.until)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_text_report(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
