#!/usr/bin/env python3
"""Count Devin token usage from CLI transcripts and Desktop ACP events, and
estimate API cost based on per-model pricing.

Devin stores token usage in two places:

1. **CLI transcripts** — JSON files under
   ``~/.local/share/devin/cli/transcripts/``, one per session, with a
   ``final_metrics`` block containing ``total_prompt_tokens``,
   ``total_completion_tokens``, ``total_cached_tokens``, and ``total_steps``.

2. **Desktop ACP events** — NDJSON files under
   ``~/Library/Application Support/Devin/User/acp-events/`` (macOS), one per
   Desktop session, containing ``usage_update`` events with per-step
   ``cognition.ai/inputTokens``, ``cognition.ai/outputTokens``, and
   ``cognition.ai/cachedReadTokens``.

The Desktop app runs the ``devin-cli`` binary as its backend, but its sessions
are tracked separately from CLI-launched sessions.  Both sources must be
merged to get the full picture.  ACP sessions are matched to the SQLite
sessions database (``~/.local/share/devin/cli/sessions.db``) by title to
determine the model, since ACP events don't carry model metadata.

Usage::

    scripts/devin-token-usage.py                # full report
    scripts/devin-token-usage.py --json         # machine-readable JSON
    scripts/devin-token-usage.py --no-acp       # CLI transcripts only
    scripts/devin-token-usage.py --no-db        # skip DB model lookup
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
DEFAULT_TRANSCRIPT_DIR = os.path.join(HOME, ".local", "share", "devin", "cli", "transcripts")
DEFAULT_ACP_DIR = os.path.join(HOME, "Library", "Application Support", "Devin", "User", "acp-events")
DEFAULT_DB_PATH = os.path.join(HOME, ".local", "share", "devin", "cli", "sessions.db")

# ---------------------------------------------------------------------------
# Pricing (USD per 1M tokens, list API rates)
# ---------------------------------------------------------------------------

PRICING = {
    "GLM-5.2":   {"in": 1.40, "cache": 0.26, "out": 4.40},
    "GPT-5.5":   {"in": 5.00, "cache": 0.50, "out": 30.00},
    "Kimi K2.7": {"in": 0.95, "cache": 0.19, "out": 4.00},
}

# Map DB model identifiers to pricing keys.
# ``adaptive`` routes to GLM-5.2 by default per ~/.config/devin/config.json.
MODEL_MAP = {
    "glm-5-2": "GLM-5.2",
    "gpt-5-5-low": "GPT-5.5",
    "gpt-5-5": "GPT-5.5",
    "kimi-k2-7": "Kimi K2.7",
    "adaptive": "GLM-5.2",
}

# CLI transcript model_name -> pricing key
TRANSCRIPT_MODEL_MAP = {
    "GLM-5.2": "GLM-5.2",
    "GPT-5.5": "GPT-5.5",
    "Kimi K2.7": "Kimi K2.7",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SessionUsage:
    """Token usage for a single session."""
    model: str = "unknown"
    prompt: int = 0
    completion: int = 0
    cached: int = 0
    source: str = ""  # "cli" or "acp"


@dataclass
class ModelTotals:
    """Aggregated totals for one model."""
    model: str = ""
    sessions: int = 0
    prompt: int = 0
    completion: int = 0
    cached: int = 0

    @property
    def uncached(self) -> int:
        return self.prompt - self.cached

    def cost(self, pricing: dict[str, dict[str, float]]) -> dict[str, float]:
        p = pricing.get(self.model, {"in": 0, "cache": 0, "out": 0})
        in_cost = self.uncached / 1_000_000 * p["in"]
        cache_cost = self.cached / 1_000_000 * p["cache"]
        out_cost = self.completion / 1_000_000 * p["out"]
        return {
            "input": in_cost,
            "cached": cache_cost,
            "output": out_cost,
            "total": in_cost + cache_cost + out_cost,
        }


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_cli_transcripts(transcript_dir: str) -> dict[str, SessionUsage]:
    """Load token usage from CLI transcript JSON files.

    Returns a dict mapping session_id to SessionUsage.
    """
    result: dict[str, SessionUsage] = {}
    for path in sorted(glob.glob(os.path.join(transcript_dir, "*.json"))):
        try:
            with open(path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        metrics = data.get("final_metrics")
        if not metrics:
            continue
        sid = data.get("session_id", os.path.basename(path).replace(".json", ""))
        model_name = data.get("agent", {}).get("model_name", "unknown")
        model_key = TRANSCRIPT_MODEL_MAP.get(model_name, model_name)
        result[sid] = SessionUsage(
            model=model_key,
            prompt=metrics.get("total_prompt_tokens", 0),
            completion=metrics.get("total_completion_tokens", 0),
            cached=metrics.get("total_cached_tokens", 0),
            source="cli",
        )
    return result


def load_acp_events(acp_dir: str) -> dict[str, SessionUsage]:
    """Load token usage from Desktop ACP event NDJSON files.

    Each ``usage_update`` event carries per-step token counts.  Input and
    cached tokens are cumulative (the last update has the total); output
    tokens are per-step and must be summed.

    Returns a dict mapping file UUID to SessionUsage.  Sessions without any
    ``usage_update`` events are omitted.
    """
    result: dict[str, SessionUsage] = {}
    for path in sorted(glob.glob(os.path.join(acp_dir, "*.ndjson"))):
        fid = os.path.basename(path).replace(".ndjson", "")
        usages: list[tuple[int, int, int]] = []
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    notification = event.get("notification", {})
                    if notification.get("sessionUpdate") != "usage_update":
                        continue
                    meta = notification.get("_meta", {})
                    usages.append((
                        meta.get("cognition.ai/inputTokens", 0),
                        meta.get("cognition.ai/outputTokens", 0),
                        meta.get("cognition.ai/cachedReadTokens", 0),
                    ))
        except OSError:
            continue
        if not usages:
            continue
        last_input, _, last_cached = usages[-1]
        total_output = sum(u[1] for u in usages)
        result[fid] = SessionUsage(
            model="unknown",  # resolved later via DB
            prompt=last_input,
            completion=total_output,
            cached=last_cached,
            source="acp",
        )
    return result


def load_acp_titles(acp_dir: str) -> dict[str, str]:
    """Extract session titles from ACP event files.

    Returns a dict mapping file UUID to title string.
    """
    result: dict[str, str] = {}
    for path in sorted(glob.glob(os.path.join(acp_dir, "*.ndjson"))):
        fid = os.path.basename(path).replace(".ndjson", "")
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    notification = event.get("notification", {})
                    if notification.get("sessionUpdate") == "session_info_update":
                        title = notification.get("title", "")
                        if title:
                            result[fid] = title
                        break
        except OSError:
            continue
    return result


def load_db_sessions(db_path: str) -> tuple[dict[str, dict], dict[str, dict]]:
    """Load session metadata from the Devin CLI SQLite database.

    Returns two dicts:
    - ``by_id``: session_id -> {model, title}
    - ``by_title``: title -> {id, model}
    """
    by_id: dict[str, dict] = {}
    by_title: dict[str, dict] = {}
    if not os.path.exists(db_path):
        return by_id, by_title
    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("SELECT id, model, title FROM sessions")
        for sid, model, title in cur.fetchall():
            entry = {"model": model, "title": title}
            by_id[sid] = entry
            if title:
                by_title[title] = {"id": sid, "model": model}
        con.close()
    except sqlite3.Error:
        pass
    return by_id, by_title


# ---------------------------------------------------------------------------
# Merge logic
# ---------------------------------------------------------------------------

def merge_usage(
    cli: dict[str, SessionUsage],
    acp: dict[str, SessionUsage],
    acp_titles: dict[str, str],
    db_by_title: dict[str, dict],
) -> dict[str, ModelTotals]:
    """Merge CLI and ACP session usage into per-model totals.

    ACP sessions are matched to DB sessions by title to resolve the model.
    Sessions present in both sources are counted once (CLI takes priority
    since its transcripts carry the model name directly).
    """
    per_model: dict[str, ModelTotals] = {}

    def _get_totals(key: str) -> ModelTotals:
        if key not in per_model:
            per_model[key] = ModelTotals(model=key)
        return per_model[key]

    # CLI sessions
    for sid, usage in cli.items():
        totals = _get_totals(usage.model)
        totals.sessions += 1
        totals.prompt += usage.prompt
        totals.completion += usage.completion
        totals.cached += usage.cached

    # ACP sessions — resolve model via DB title match
    cli_session_ids = set(cli.keys())
    for fid, usage in acp.items():
        title = acp_titles.get(fid, "")
        db_match = db_by_title.get(title, {})
        db_id = db_match.get("id")

        # Skip if this ACP session maps to a CLI session we already counted
        if db_id and db_id in cli_session_ids:
            continue

        raw_model = db_match.get("model", "glm-5-2")  # default to GLM-5.2
        model_key = MODEL_MAP.get(raw_model, "GLM-5.2")
        totals = _get_totals(model_key)
        totals.sessions += 1
        totals.prompt += usage.prompt
        totals.completion += usage.completion
        totals.cached += usage.cached

    return per_model


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def compute_report(per_model: dict[str, ModelTotals]) -> dict:
    """Compute the full report dict (for JSON output)."""
    models = {}
    grand = {"sessions": 0, "prompt": 0, "completion": 0, "cached": 0,
             "in_cost": 0.0, "cache_cost": 0.0, "out_cost": 0.0, "total": 0.0}
    for model_key in ["GLM-5.2", "GPT-5.5", "Kimi K2.7"]:
        totals = per_model.get(model_key)
        if not totals:
            continue
        cost = totals.cost(PRICING)
        models[model_key] = {
            "sessions": totals.sessions,
            "uncached_input": totals.uncached,
            "cached_input": totals.cached,
            "output": totals.completion,
            "cost": cost,
        }
        grand["sessions"] += totals.sessions
        grand["prompt"] += totals.prompt
        grand["completion"] += totals.completion
        grand["cached"] += totals.cached
        grand["in_cost"] += cost["input"]
        grand["cache_cost"] += cost["cached"]
        grand["out_cost"] += cost["output"]
        grand["total"] += cost["total"]

    grand["uncached_input"] = grand["prompt"] - grand["cached"]
    return {"models": models, "totals": grand, "pricing": PRICING}


def print_text_report(report: dict) -> None:
    """Print a human-readable cost report."""
    models = report["models"]
    grand = report["totals"]
    print("=" * 90)
    print("DEVIN TOKEN USAGE & API COST ESTIMATE")
    print("=" * 90)
    print()
    print(f"{'Model':<12}{'Sessions':>9}  {'Uncached In':>13}{'Cached In':>13}{'Output':>11}  {'Cost (USD)':>12}")
    print("-" * 90)
    for model_key in ["GLM-5.2", "GPT-5.5", "Kimi K2.7"]:
        m = models.get(model_key)
        if not m:
            continue
        print(f"{model_key:<12}{m['sessions']:>9}  {m['uncached_input']:>13,}{m['cached_input']:>13,}{m['output']:>11,}  {m['cost']['total']:>11.2f}$")
    print("-" * 90)
    print(f"{'TOTAL':<12}{grand['sessions']:>9}  {grand['uncached_input']:>13,}{grand['cached']:>13,}{grand['completion']:>11,}  {grand['total']:>11.2f}$")
    print()
    print("Cost breakdown:")
    print(f"  Uncached input : ${grand['in_cost']:>9.2f}")
    print(f"  Cached input   : ${grand['cache_cost']:>9.2f}")
    print(f"  Output         : ${grand['out_cost']:>9.2f}")
    print(f"  TOTAL          : ${grand['total']:>9.2f}")
    print()
    print("Pricing used (per 1M tokens, list API rates):")
    for model_key, p in PRICING.items():
        print(f"  {model_key:<11} input ${p['in']:.2f}  cached ${p['cache']:.2f}  output ${p['out']:.2f}")
    if grand["prompt"] > 0:
        cache_pct = grand["cached"] / grand["prompt"] * 100
        print(f"\n{cache_pct:.1f}% of input tokens were cache hits.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Count Devin token usage and estimate API cost."
    )
    parser.add_argument("--transcript-dir", default=DEFAULT_TRANSCRIPT_DIR,
                        help="CLI transcript directory (default: %(default)s)")
    parser.add_argument("--acp-dir", default=DEFAULT_ACP_DIR,
                        help="Desktop ACP events directory (default: %(default)s)")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH,
                        help="Devin CLI sessions.db path (default: %(default)s)")
    parser.add_argument("--no-acp", action="store_true",
                        help="Skip ACP event processing (CLI transcripts only)")
    parser.add_argument("--no-db", action="store_true",
                        help="Skip DB model lookup (ACP sessions default to GLM-5.2)")
    parser.add_argument("--json", action="store_true",
                        help="Output machine-readable JSON instead of text")
    args = parser.parse_args(argv)

    cli = load_cli_transcripts(args.transcript_dir)

    acp: dict[str, SessionUsage] = {}
    acp_titles: dict[str, str] = {}
    if not args.no_acp and os.path.isdir(args.acp_dir):
        acp = load_acp_events(args.acp_dir)
        acp_titles = load_acp_titles(args.acp_dir)

    _, db_by_title = ({}, {}) if args.no_db else load_db_sessions(args.db_path)

    per_model = merge_usage(cli, acp, acp_titles, db_by_title)
    report = compute_report(per_model)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_text_report(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
