#!/usr/bin/env python3
"""Count ChatGPT/Codex subscription token usage from Codex CLI session
rollouts and Hermes agent state, and estimate API cost based on per-model
pricing.

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
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------

HOME = os.path.expanduser("~")
DEFAULT_CODEX_SESSION_DIR = os.path.join(HOME, ".codex", "sessions")
DEFAULT_HERMES_DB = os.path.join(HOME, ".hermes", "state.db")

# ---------------------------------------------------------------------------
# Pricing (USD per 1M tokens, OpenAI list API rates)
# ---------------------------------------------------------------------------

PRICING = {
    "gpt-5.5":      {"in": 5.00, "cache": 0.50, "out": 30.00},
    "gpt-5.6-sol":  {"in": 5.00, "cache": 0.50, "out": 30.00},
    "gpt-5.6-luna": {"in": 1.00, "cache": 0.10, "out": 6.00},
    "gpt-5.6-terra":{"in": 2.50, "cache": 0.25, "out": 15.00},
}

# Fallback pricing for unknown models (use gpt-5.6-sol as conservative default)
DEFAULT_PRICING = PRICING["gpt-5.6-sol"]

# Hermes billing providers that route through the ChatGPT/Codex subscription
CODEX_BILLING_PROVIDERS = {"openai-codex"}


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

def load_codex_sessions(session_dir: str) -> dict[str, SessionUsage]:
    """Load token usage from Codex CLI session rollout JSONL files.

    Returns a dict mapping session_id to SessionUsage.  Sessions without
    any ``token_count`` events are omitted.
    """
    result: dict[str, SessionUsage] = {}
    pattern = os.path.join(session_dir, "**", "rollout-*.jsonl")
    for path in sorted(glob.glob(pattern, recursive=True)):
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
                            info = payload.get("info", {})
                            total_usage = info.get("total_token_usage")
                            rate_limits = payload.get("rate_limits", {})
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
        )
    return result


def load_hermes_sessions(
    db_path: str,
    all_providers: bool = False,
) -> dict[str, SessionUsage]:
    """Load token usage from the Hermes agent state database.

    Returns a dict mapping ``hermes-{session_id}-{model}`` to SessionUsage.
    Only rows with ``billing_provider = 'openai-codex'`` are included
    unless ``all_providers`` is True.
    """
    result: dict[str, SessionUsage] = {}
    if not os.path.exists(db_path):
        return result

    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        if all_providers:
            cur.execute(
                "SELECT session_id, model, billing_provider, billing_mode, "
                "input_tokens, output_tokens, cache_read_tokens, "
                "cache_write_tokens, reasoning_tokens "
                "FROM session_model_usage"
            )
        else:
            placeholders = ",".join("?" * len(CODEX_BILLING_PROVIDERS))
            cur.execute(
                f"SELECT session_id, model, billing_provider, billing_mode, "
                f"input_tokens, output_tokens, cache_read_tokens, "
                f"cache_write_tokens, reasoning_tokens "
                f"FROM session_model_usage "
                f"WHERE billing_provider IN ({placeholders})",
                list(CODEX_BILLING_PROVIDERS),
            )
        for row in cur.fetchall():
            (sid, model, provider, mode,
             inp, out, cache_read, cache_write, reasoning) = row
            # In Hermes, input_tokens and cache_read_tokens are separate
            # (input_tokens = uncached input)
            key = f"hermes-{sid}-{model}"
            result[key] = SessionUsage(
                model=model,
                uncached_input=inp,
                cached_input=cache_read,
                output=out,
                reasoning=reasoning,
                source=f"hermes:{provider}",
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

    for usage in hermes.values():
        totals = _get_totals(usage.model)
        totals.sessions += 1
        totals.uncached_input += usage.uncached_input
        totals.cached_input += usage.cached_input
        totals.output += usage.output
        totals.reasoning += usage.reasoning
        totals.sources.add(usage.source)

    return per_model


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _fmt(n: int) -> str:
    return f"{n:,}"


def compute_report(
    per_model: dict[str, ModelTotals],
    all_providers: bool = False,
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
    return {
        "models": models,
        "totals": grand,
        "pricing": PRICING,
        "all_providers": all_providers,
    }


def print_text_report(report: dict) -> None:
    """Print a human-readable cost report."""
    models = report["models"]
    grand = report["totals"]
    scope = "all providers" if report.get("all_providers") else "ChatGPT/Codex subscription"
    print("=" * 90)
    print(f"CHATGPT/CODEX TOKEN USAGE & API COST ESTIMATE ({scope})")
    print("=" * 90)
    print()
    print(f"{'Model':<16}{'Sessions':>9}  {'Uncached In':>13}{'Cached In':>13}{'Output':>11}  {'Cost (USD)':>12}")
    print("-" * 90)
    for model_key, m in models.items():
        print(f"{model_key:<16}{m['sessions']:>9}  "
              f"{_fmt(m['uncached_input']):>13}{_fmt(m['cached_input']):>13}"
              f"{_fmt(m['billable_output']):>11}  {m['cost']['total']:>11.2f}$")
    print("-" * 90)
    print(f"{'TOTAL':<16}{grand['sessions']:>9}  "
          f"{_fmt(grand['uncached_input']):>13}{_fmt(grand['cached_input']):>13}"
          f"{_fmt(grand['billable_output']):>11}  {grand['total']:>11.2f}$")
    print()
    print("Cost breakdown:")
    print(f"  Uncached input : ${grand['in_cost']:>9.2f}")
    print(f"  Cached input   : ${grand['cache_cost']:>9.2f}")
    print(f"  Output         : ${grand['out_cost']:>9.2f}")
    print(f"  TOTAL          : ${grand['total']:>9.2f}")
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Count ChatGPT/Codex subscription token usage and estimate API cost."
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
    parser.add_argument("--json", action="store_true",
                        help="Output machine-readable JSON instead of text")
    args = parser.parse_args(argv)

    codex: dict[str, SessionUsage] = {}
    if not args.no_codex and os.path.isdir(args.session_dir):
        codex = load_codex_sessions(args.session_dir)

    hermes: dict[str, SessionUsage] = {}
    if not args.no_hermes:
        hermes = load_hermes_sessions(args.hermes_db, all_providers=args.all_providers)

    per_model = merge_usage(codex, hermes)
    report = compute_report(per_model, all_providers=args.all_providers)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_text_report(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
