#!/usr/bin/env python3
"""Aggregate token usage and implied API value across local and remote machines.

Collects token usage from:
- Local: Codex CLI + Hermes (via codex-token-usage.py --all-providers --json)
         and Amp (via amp-token-usage.py --json --amp-costs)
- Remote hosts (via SSH): Hermes state.db and OpenClaw sessions

Produces a consolidated report showing per-machine, per-source, per-model,
and per-billing-provider breakdowns of implied API value — what the same
tokens would cost at full pay-as-you-go API rates.

Hermes is the primary token source on each machine (it tracks API-level
usage with billing-provider attribution).  OpenClaw session data is shown
as a cross-reference but excluded from the grand total because OpenClaw
routes through Hermes/Codex and would double-count.

Usage::

    scripts/all-token-usage.py                            # full report
    scripts/all-token-usage.py --json                     # machine-readable JSON
    scripts/all-token-usage.py --hosts hetzner ssh.is-there.net
    scripts/all-token-usage.py --no-remote                # local only
    scripts/all-token-usage.py --no-local                 # remote only
    scripts/all-token-usage.py --no-amp                   # skip Amp
    scripts/all-token-usage.py --no-openclaw              # skip OpenClaw
    scripts/all-token-usage.py --since 2026-07-01
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from collections import defaultdict

# ---------------------------------------------------------------------------
# Pricing (USD per 1M tokens, list API rates)
# Merged from codex-token-usage.py and amp-token-usage.py, plus new models
# found on remote machines.
# ---------------------------------------------------------------------------

PRICING: dict[str, dict[str, float]] = {
    # OpenAI
    "gpt-5.5":                {"in": 5.00,  "cache": 0.50,  "out": 30.00},
    "gpt-5.6-sol":            {"in": 5.00,  "cache": 0.50,  "out": 30.00},
    "gpt-5.6-luna":           {"in": 1.00,  "cache": 0.10,  "out": 6.00},
    "gpt-5.6-terra":          {"in": 2.50,  "cache": 0.25,  "out": 15.00},
    "gpt-5.4":                {"in": 2.50,  "cache": 0.25,  "out": 15.00},
    "gpt-5.4-mini":           {"in": 0.75,  "cache": 0.075, "out": 4.50},
    "gpt-5.3-codex-spark":    {"in": 1.75,  "cache": 0.175, "out": 14.00},
    # Anthropic
    "claude-fable-5":         {"in": 10.00, "cache": 1.00,  "out": 50.00},
    # xAI
    "grok-4.5":               {"in": 2.00,  "cache": 0.50,  "out": 6.00},
    "grok-4.3":               {"in": 5.00,  "cache": 0.50,  "out": 15.00},
    "grok-composer-2.5-fast": {"in": 0.50,  "cache": 0.10,  "out": 2.00},
    # Fireworks — GLM
    "GLM-5.2":                {"in": 1.40,  "cache": 0.26,  "out": 4.40},
    "accounts/fireworks/models/glm-5p2":          {"in": 1.40, "cache": 0.26, "out": 4.40},
    # Fireworks — Kimi
    "accounts/fireworks/routers/kimi-k2p6-turbo": {"in": 0.95, "cache": 0.19, "out": 4.00},
    # MiniMax
    "MiniMax-M3":             {"in": 0.60,  "cache": 0.12,  "out": 2.40},
    # Moonshot
    "Kimi K2.7":              {"in": 0.95,  "cache": 0.19,  "out": 4.00},
    # Xiaomi MiMo — no public API pricing known
    "mimo-v2.5":              {"in": 0.0,   "cache": 0.0,   "out": 0.0},
    "mimo-v2.5-pro":          {"in": 0.0,   "cache": 0.0,   "out": 0.0},
}

DEFAULT_PRICING = {"in": 0.0, "cache": 0.0, "out": 0.0}

# Billing provider → human-readable display name
PROVIDER_DISPLAY: dict[str, str] = {
    "openai-codex": "ChatGPT Plus/Pro",
    "xai-oauth":    "X Premium+/SuperGrok",
    "custom":       "Direct API (pay-as-you-go)",
    "auto":         "Auto-routed (unknown)",
    "moa":          "Mixture-of-Agents",
    "xiaomi":       "Xiaomi",
    "amp-credits":  "Amp credits",
    "unknown":      "Unknown",
}

# Model → billing provider for sources that don't provide one (e.g. Amp)
MODEL_TO_PROVIDER: dict[str, str] = {
    "gpt-5.5":              "openai-codex",
    "gpt-5.6-sol":          "openai-codex",
    "gpt-5.6-luna":         "openai-codex",
    "gpt-5.6-terra":        "openai-codex",
    "gpt-5.4":              "openai-codex",
    "gpt-5.4-mini":         "openai-codex",
    "gpt-5.3-codex-spark":  "openai-codex",
    "grok-4.5":             "xai-oauth",
    "grok-4.3":             "xai-oauth",
    "grok-composer-2.5-fast": "xai-oauth",
    "claude-fable-5":       "amp-credits",
    "GLM-5.2":              "amp-credits",
    "accounts/fireworks/models/glm-5p2": "amp-credits",
    "accounts/fireworks/routers/kimi-k2p6-turbo": "amp-credits",
    "MiniMax-M3":           "amp-credits",
    "Kimi K2.7":            "amp-credits",
    "mimo-v2.5":            "xiaomi",
    "mimo-v2.5-pro":        "xiaomi",
}

# OpenClaw modelProvider → Hermes billing_provider
OPENCLAW_PROVIDER_MAP: dict[str, str] = {
    "openai": "openai-codex",
    "xai":    "xai-oauth",
}

DEFAULT_HOSTS = ["hetzner", "ssh.is-there.net"]
DEFAULT_SSH_TIMEOUT = 30

# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def _parse_date(s: str) -> str:
    datetime.strptime(s, "%Y-%m-%d")
    return s

def _date_to_epoch(d: str) -> float:
    return datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class UsageEntry:
    """Normalized token usage from any source on any machine."""
    machine: str
    source: str            # "codex-cli+hermes", "amp", "hermes", "openclaw"
    model: str
    billing_provider: str = ""
    uncached_input: int = 0
    cached_input: int = 0
    output: int = 0        # excludes reasoning
    reasoning: int = 0
    sessions: int = 1

    @property
    def billable_output(self) -> int:
        return self.output + self.reasoning

    @property
    def total_input(self) -> int:
        return self.uncached_input + self.cached_input

    def cost(self) -> dict[str, float]:
        p = PRICING.get(self.model, DEFAULT_PRICING)
        in_cost = self.uncached_input / 1_000_000 * p["in"]
        cache_cost = self.cached_input / 1_000_000 * p["cache"]
        out_cost = self.billable_output / 1_000_000 * p["out"]
        return {"input": in_cost, "cached": cache_cost, "output": out_cost,
                "total": in_cost + cache_cost + out_cost}

    @property
    def is_priced(self) -> bool:
        return self.model in PRICING


@dataclass
class MachineCollection:
    """All usage entries from one machine."""
    machine: str
    entries: list[UsageEntry] = field(default_factory=list)
    openclaw_entries: list[UsageEntry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    # Ancillary data from amp report
    amp_billing_routes: list[dict] = field(default_factory=list)
    amp_ancillary_cost: float = 0.0


def _fmt(n: int) -> str:
    return f"{n:,}"

def _fmt_cost(v: float) -> str:
    return f"${v:,.2f}"

# ---------------------------------------------------------------------------
# Remote collection via SSH
# ---------------------------------------------------------------------------

_HERMES_QUERY = r'''
import sqlite3, json, os, sys
db = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.hermes/state.db")
if not os.path.exists(db):
    print(json.dumps([]))
    sys.exit(0)
con = sqlite3.connect("file:" + db + "?mode=ro", uri=True)
cur = con.cursor()
date_conds = []
date_params = []
since = sys.argv[2] if len(sys.argv) > 2 else None
until = sys.argv[3] if len(sys.argv) > 3 else None
if since:
    from datetime import datetime, timezone
    epoch = datetime.strptime(since, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
    date_conds.append("last_seen >= ?")
    date_params.append(epoch)
if until:
    from datetime import datetime, timezone
    epoch = datetime.strptime(until, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() + 86400
    date_conds.append("last_seen < ?")
    date_params.append(epoch)
clause = (" AND " + " AND ".join(date_conds)) if date_conds else ""
cur.execute(
    "SELECT session_id, model, billing_provider, billing_base_url, "
    "billing_mode, task, input_tokens, output_tokens, "
    "cache_read_tokens, cache_write_tokens, reasoning_tokens "
    "FROM session_model_usage WHERE 1=1" + clause,
    date_params)
rows = []
for r in cur.fetchall():
    rows.append({
        "session_id": r[0], "model": r[1], "billing_provider": r[2],
        "billing_base_url": r[3], "billing_mode": r[4], "task": r[5],
        "input_tokens": r[6], "output_tokens": r[7],
        "cache_read_tokens": r[8], "cache_write_tokens": r[9],
        "reasoning_tokens": r[10],
    })
con.close()
print(json.dumps(rows))
'''


def collect_remote_hermes(
    host: str, db_path: str = "~/.hermes/state.db",
    since: Optional[str] = None, until: Optional[str] = None,
    timeout: int = DEFAULT_SSH_TIMEOUT,
) -> list[dict]:
    """SSH to host and query Hermes state.db, return list of row dicts."""
    args = ["python3", "-", db_path]
    if since:
        args.append(since)
    if until:
        args.append(until)
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
           host, " ".join(args)]
    result = subprocess.run(
        cmd, input=_HERMES_QUERY, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"SSH exit {result.returncode}")
    return json.loads(result.stdout)


def collect_remote_openclaw(
    host: str, timeout: int = DEFAULT_SSH_TIMEOUT,
) -> dict:
    """SSH to host and run openclaw sessions --json --all-agents --limit all."""
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", host,
           "openclaw sessions --json --all-agents --limit all"]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"SSH exit {result.returncode}")
    return json.loads(result.stdout)


# ---------------------------------------------------------------------------
# Local collection (subprocess)
# ---------------------------------------------------------------------------

def _script_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def collect_local_codex(since: Optional[str] = None,
                        until: Optional[str] = None) -> dict:
    """Run codex-token-usage.py --all-providers --json and return parsed JSON."""
    cmd = [sys.executable, os.path.join(_script_dir(), "codex-token-usage.py"),
           "--all-providers", "--json"]
    if since:
        cmd += ["--since", since]
    if until:
        cmd += ["--until", until]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"exit {result.returncode}")
    return json.loads(result.stdout)


def collect_local_amp(since: Optional[str] = None,
                      until: Optional[str] = None) -> dict:
    """Run amp-token-usage.py --json --amp-costs and return parsed JSON."""
    cmd = [sys.executable, os.path.join(_script_dir(), "amp-token-usage.py"),
           "--json", "--amp-costs"]
    if since:
        cmd += ["--since", since]
    if until:
        cmd += ["--until", until]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        # Retry without --amp-costs (amp CLI might not be available)
        cmd = [sys.executable, os.path.join(_script_dir(), "amp-token-usage.py"),
               "--json"]
        if since:
            cmd += ["--since", since]
        if until:
            cmd += ["--until", until]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"exit {result.returncode}")
    return json.loads(result.stdout)


# ---------------------------------------------------------------------------
# Normalization — convert each source's JSON into UsageEntry list
# ---------------------------------------------------------------------------

def normalize_local_codex(report: dict) -> list[UsageEntry]:
    """Convert codex-token-usage.py JSON into UsageEntry objects."""
    entries = []
    for model_name, m in report.get("models", {}).items():
        providers = m.get("providers", [])
        provider = providers[0] if providers else "unknown"
        entries.append(UsageEntry(
            machine="local",
            source="codex-cli+hermes",
            model=model_name,
            billing_provider=provider,
            uncached_input=m.get("uncached_input", 0),
            cached_input=m.get("cached_input", 0),
            output=m.get("output", 0),
            reasoning=m.get("reasoning", 0),
            sessions=m.get("sessions", 0),
        ))
    return entries


def normalize_local_amp(report: dict) -> list[UsageEntry]:
    """Convert amp-token-usage.py JSON into UsageEntry objects.

    The amp report distinguishes:
    - total_input_tokens: all input tokens (uncached + cached)
    - cache_read_input_tokens: cached input tokens
    - billable_input_tokens: total_input_tokens - cache_read_input_tokens (uncached)
    - input_tokens: a subset field (often 0), NOT the uncached input

    We use billable_input_tokens as uncached input and cache_read_input_tokens
    as cached input, matching the amp script's own cost calculation.
    """
    entries = []
    for model_name, m in report.get("models", {}).items():
        provider = MODEL_TO_PROVIDER.get(model_name, "unknown")
        entries.append(UsageEntry(
            machine="local",
            source="amp",
            model=model_name,
            billing_provider=provider,
            uncached_input=m.get("billable_input_tokens", 0),
            cached_input=m.get("cache_read_input_tokens", 0),
            output=m.get("output_tokens", 0),
            reasoning=0,  # amp doesn't track reasoning separately
            sessions=m.get("threads", 0),
        ))
    return entries


def normalize_remote_hermes(host: str, rows: list[dict]) -> list[UsageEntry]:
    """Convert remote Hermes session_model_usage rows into UsageEntry objects."""
    entries = []
    for row in rows:
        entries.append(UsageEntry(
            machine=host,
            source="hermes",
            model=row.get("model", "unknown"),
            billing_provider=row.get("billing_provider", ""),
            uncached_input=row.get("input_tokens", 0),
            cached_input=row.get("cache_read_tokens", 0),
            output=row.get("output_tokens", 0),
            reasoning=row.get("reasoning_tokens", 0),
            sessions=1,
        ))
    return entries


def normalize_openclaw(host: str, report: dict) -> list[UsageEntry]:
    """Convert OpenClaw sessions JSON into UsageEntry objects."""
    entries = []
    for session in report.get("sessions", []):
        model = session.get("model") or "unknown"
        model_provider = session.get("modelProvider", "")
        provider = OPENCLAW_PROVIDER_MAP.get(model_provider, model_provider or "unknown")
        input_tokens = session.get("inputTokens") or 0
        output_tokens = session.get("outputTokens") or 0
        if input_tokens == 0 and output_tokens == 0:
            continue  # skip sessions with no token data
        entries.append(UsageEntry(
            machine=host,
            source="openclaw",
            model=model,
            billing_provider=provider,
            uncached_input=input_tokens,
            cached_input=0,  # OpenClaw doesn't report cache split
            output=output_tokens,
            reasoning=0,  # not available
            sessions=1,
        ))
    return entries


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

@dataclass
class ModelAgg:
    """Aggregated totals for one model within a group."""
    model: str = ""
    sessions: int = 0
    uncached_input: int = 0
    cached_input: int = 0
    output: int = 0
    reasoning: int = 0
    is_priced: bool = True

    @property
    def billable_output(self) -> int:
        return self.output + self.reasoning

    @property
    def total_input(self) -> int:
        return self.uncached_input + self.cached_input

    def cost(self) -> dict[str, float]:
        p = PRICING.get(self.model, DEFAULT_PRICING)
        in_cost = self.uncached_input / 1_000_000 * p["in"]
        cache_cost = self.cached_input / 1_000_000 * p["cache"]
        out_cost = self.billable_output / 1_000_000 * p["out"]
        return {"input": in_cost, "cached": cache_cost, "output": out_cost,
                "total": in_cost + cache_cost + out_cost}


def aggregate_models(entries: list[UsageEntry]) -> dict[str, ModelAgg]:
    """Aggregate entries into per-model totals."""
    per_model: dict[str, ModelAgg] = {}
    for e in entries:
        if e.model not in per_model:
            per_model[e.model] = ModelAgg(model=e.model, is_priced=e.is_priced)
        agg = per_model[e.model]
        agg.sessions += e.sessions
        agg.uncached_input += e.uncached_input
        agg.cached_input += e.cached_input
        agg.output += e.output
        agg.reasoning += e.reasoning
    return per_model


def total_cost(entries: list[UsageEntry]) -> float:
    return sum(e.cost()["total"] for e in entries)


def provider_cost(entries: list[UsageEntry]) -> dict[str, dict[str, float]]:
    """Aggregate cost by billing provider."""
    by_prov: dict[str, dict[str, float]] = defaultdict(
        lambda: {"cost": 0.0, "sessions": 0, "input": 0, "output": 0})
    for e in entries:
        prov = e.billing_provider or "unknown"
        c = e.cost()
        by_prov[prov]["cost"] += c["total"]
        by_prov[prov]["sessions"] += e.sessions
        by_prov[prov]["input"] += e.total_input
        by_prov[prov]["output"] += e.billable_output
    return dict(by_prov)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _model_table(entries: list[UsageEntry], title: str, indent: str = "") -> None:
    """Print a per-model table for a set of entries."""
    per_model = aggregate_models(entries)
    if not per_model:
        print(f"{indent}  (no data)")
        return
    print(f"{indent}  {title}")
    print(f"{indent}  {'Model':<36}{'Sessions':>9}  {'Uncached In':>13}"
          f"{'Cached In':>13}{'Output':>11}  {'Implied Cost':>13}")
    print(f"{indent}  {'-'*98}")
    for model_name in sorted(per_model, key=lambda k: -per_model[k].cost()["total"]):
        agg = per_model[model_name]
        c = agg.cost()
        marker = "" if agg.is_priced else " *"
        print(f"{indent}  {model_name:<36}{agg.sessions:>9}  "
              f"{_fmt(agg.uncached_input):>13}{_fmt(agg.cached_input):>13}"
              f"{_fmt(agg.billable_output):>11}  {c['total']:>12.2f}${marker}")
    print(f"{indent}  {'-'*98}")
    tc = total_cost(entries)
    print(f"{indent}  {'SUBTOTAL':<36}{'':>9}  {'':>13}{'':>13}{'':>11}  {tc:>12.2f}$")
    unpriced = [k for k, v in per_model.items() if not v.is_priced]
    if unpriced:
        print(f"{indent}  * no known API pricing: {', '.join(sorted(unpriced))}")


def print_text_report(collections: list[MachineCollection],
                      since: Optional[str] = None,
                      until: Optional[str] = None) -> None:
    """Print the full consolidated text report."""
    date_range = ""
    if since or until:
        lo = since or "begin"
        hi = until or "now"
        date_range = f"  [{lo} .. {hi}]"
    print("=" * 110)
    print(f"CROSS-MACHINE TOKEN USAGE & IMPLIED API VALUE{date_range}")
    print("=" * 110)
    print()

    # Per-machine breakdown
    all_primary: list[UsageEntry] = []
    all_openclaw: list[UsageEntry] = []
    for mc in collections:
        print(f"MACHINE: {mc.machine}")
        print("-" * 110)
        if mc.errors:
            for err in mc.errors:
                print(f"  ERROR: {err}")
        if not mc.entries and not mc.openclaw_entries:
            print("  (no data)")
            print()
            continue
        # Group entries by source
        by_source: dict[str, list[UsageEntry]] = defaultdict(list)
        for e in mc.entries:
            by_source[e.source].append(e)
        for source, entries in sorted(by_source.items()):
            _model_table(entries, f"Source: {source}")
            print()
        # OpenClaw cross-reference
        if mc.openclaw_entries:
            _model_table(mc.openclaw_entries, "Cross-reference: openclaw (may overlap with hermes)")
            print()
        # Amp ancillary cost
        if mc.amp_ancillary_cost > 0:
            print(f"  Amp ancillary overhead (tool execution on subscription threads): "
                  f"{_fmt_cost(mc.amp_ancillary_cost)}")
            print()
        all_primary.extend(mc.entries)
        all_openclaw.extend(mc.openclaw_entries)
        print()

    # Consolidated summary by billing provider
    print("=" * 110)
    print("CONSOLIDATED SUMMARY BY BILLING PROVIDER")
    print("=" * 110)
    prov_costs = provider_cost(all_primary)
    print(f"{'Provider':<32}{'Sessions':>9}  {'Total Input':>14}{'Output':>11}"
          f"  {'Implied API Cost':>17}")
    print("-" * 110)
    for prov_name in sorted(prov_costs, key=lambda k: -prov_costs[k]["cost"]):
        pc = prov_costs[prov_name]
        display = PROVIDER_DISPLAY.get(prov_name, prov_name)
        print(f"{display:<32}{pc['sessions']:>9}  "
              f"{_fmt(pc['input']):>14}{_fmt(pc['output']):>11}  "
              f"{_fmt_cost(pc['cost']):>16}")
    print("-" * 110)
    grand_total = sum(pc["cost"] for pc in prov_costs.values())
    print(f"{'GRAND TOTAL':<32}{'':>9}  {'':>14}{'':>11}  {_fmt_cost(grand_total):>16}")
    print()

    # Per-machine subtotal
    print("=" * 110)
    print("PER-MACHINE SUBTOTAL")
    print("=" * 110)
    for mc in collections:
        primary = total_cost(mc.entries)
        openclaw = total_cost(mc.openclaw_entries)
        line = f"  {mc.machine:<24}  {_fmt_cost(primary):>12}"
        if openclaw > 0:
            line += f"  (openclaw cross-ref: {_fmt_cost(openclaw)})"
        if mc.amp_ancillary_cost > 0:
            line += f"  + {_fmt_cost(mc.amp_ancillary_cost)} amp ancillary"
        print(line)
    print()

    # Notes
    print("=" * 110)
    print("NOTES")
    print("=" * 110)
    print("- Hermes is the primary token source on each machine; OpenClaw session")
    print("  data is shown as cross-reference and excluded from totals because")
    print("  OpenClaw routes through Hermes/Codex and would double-count.")
    print("- 'custom' billing provider = direct API calls with real per-token cost.")
    print("- 'Implied API value' = what the same tokens would cost at full")
    print("  pay-as-you-go API rates.  Subscription usage (openai-codex, xai-oauth)")
    print("  costs $0 per-token — the gap is the value delivered by your subscriptions.")
    print("- Models marked * have no known public API pricing and are billed at $0.")
    print("- Amp ancillary overhead = Amp charges for tool execution on subscription-")
    print("  routed threads, not per-token LLM cost.")
    print()


def compute_json_report(collections: list[MachineCollection],
                        since: Optional[str] = None,
                        until: Optional[str] = None) -> dict:
    """Build the full JSON report dict."""
    machines = []
    all_primary: list[UsageEntry] = []
    for mc in collections:
        by_source: dict[str, list[UsageEntry]] = defaultdict(list)
        for e in mc.entries:
            by_source[e.source].append(e)
        machine_data = {
            "machine": mc.machine,
            "sources": {},
            "openclaw_cross_reference": {},
            "errors": mc.errors,
        }
        for source, entries in sorted(by_source.items()):
            per_model = aggregate_models(entries)
            machine_data["sources"][source] = {
                model: {
                    "sessions": agg.sessions,
                    "uncached_input": agg.uncached_input,
                    "cached_input": agg.cached_input,
                    "output": agg.output,
                    "reasoning": agg.reasoning,
                    "billable_output": agg.billable_output,
                    "is_priced": agg.is_priced,
                    "implied_api_cost": agg.cost(),
                }
                for model, agg in sorted(per_model.items(),
                                         key=lambda kv: -kv[1].cost()["total"])
            }
            machine_data["sources"][source]["_subtotal"] = total_cost(entries)
        if mc.openclaw_entries:
            per_model = aggregate_models(mc.openclaw_entries)
            machine_data["openclaw_cross_reference"] = {
                model: {
                    "sessions": agg.sessions,
                    "uncached_input": agg.uncached_input,
                    "cached_input": agg.cached_input,
                    "output": agg.output,
                    "implied_api_cost": agg.cost(),
                }
                for model, agg in sorted(per_model.items(),
                                         key=lambda kv: -kv[1].cost()["total"])
            }
        if mc.amp_ancillary_cost > 0:
            machine_data["amp_ancillary_cost"] = mc.amp_ancillary_cost
        if mc.amp_billing_routes:
            machine_data["amp_billing_routes"] = mc.amp_billing_routes
        machines.append(machine_data)
        all_primary.extend(mc.entries)

    prov_costs = provider_cost(all_primary)
    by_provider = {}
    for prov_name in sorted(prov_costs, key=lambda k: -prov_costs[k]["cost"]):
        pc = prov_costs[prov_name]
        by_provider[prov_name] = {
            "display_name": PROVIDER_DISPLAY.get(prov_name, prov_name),
            "sessions": pc["sessions"],
            "total_input": pc["input"],
            "output": pc["output"],
            "implied_api_cost": pc["cost"],
        }
    grand_total = sum(pc["cost"] for pc in prov_costs.values())

    return {
        "machines": machines,
        "by_provider": by_provider,
        "grand_total_implied_api_cost": grand_total,
        "since": since,
        "until": until,
        "pricing": PRICING,
        "notes": [
            "Hermes is the primary token source; OpenClaw is cross-reference only.",
            "Implied API value = tokens × public provider list rates.",
            "Subscription usage (openai-codex, xai-oauth) costs $0 per-token.",
            "Models marked is_priced=false have no known public API pricing.",
        ],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate token usage and implied API value across local and remote machines.")
    parser.add_argument("--hosts", nargs="*", default=DEFAULT_HOSTS,
                        help="Remote SSH hosts to check (default: %(default)s)")
    parser.add_argument("--no-remote", action="store_true",
                        help="Skip all remote hosts (local only)")
    parser.add_argument("--no-local", action="store_true",
                        help="Skip local collection (remote only)")
    parser.add_argument("--no-amp", action="store_true",
                        help="Skip local Amp collection")
    parser.add_argument("--no-openclaw", action="store_true",
                        help="Skip OpenClaw collection on remote hosts")
    parser.add_argument("--no-hermes", action="store_true",
                        help="Skip Hermes collection on remote hosts")
    parser.add_argument("--since", type=_parse_date, metavar="YYYY-MM-DD",
                        help="Only count sessions on/after this date")
    parser.add_argument("--until", type=_parse_date, metavar="YYYY-MM-DD",
                        help="Only count sessions on/before this date")
    parser.add_argument("--ssh-timeout", type=int, default=DEFAULT_SSH_TIMEOUT,
                        help="SSH command timeout in seconds (default: %(default)s)")
    parser.add_argument("--json", action="store_true",
                        help="Output machine-readable JSON instead of text")
    args = parser.parse_args(argv)

    collections: list[MachineCollection] = []

    # --- Local collection ---
    if not args.no_local:
        mc = MachineCollection(machine="local")
        try:
            codex_report = collect_local_codex(since=args.since, until=args.until)
            mc.entries.extend(normalize_local_codex(codex_report))
        except Exception as exc:
            mc.errors.append(f"codex-token-usage.py: {exc}")
        if not args.no_amp:
            try:
                amp_report = collect_local_amp(since=args.since, until=args.until)
                mc.entries.extend(normalize_local_amp(amp_report))
                mc.amp_billing_routes = amp_report.get("billing_routes", [])
                for route in mc.amp_billing_routes:
                    mc.amp_ancillary_cost += route.get("amp_ancillary_cost", 0.0)
            except Exception as exc:
                mc.errors.append(f"amp-token-usage.py: {exc}")
        collections.append(mc)

    # --- Remote collection ---
    if not args.no_remote:
        for host in args.hosts:
            mc = MachineCollection(machine=host)
            if not args.no_hermes:
                try:
                    rows = collect_remote_hermes(host, since=args.since,
                                                 until=args.until,
                                                 timeout=args.ssh_timeout)
                    mc.entries.extend(normalize_remote_hermes(host, rows))
                except Exception as exc:
                    mc.errors.append(f"hermes: {exc}")
            if not args.no_openclaw:
                try:
                    oc_report = collect_remote_openclaw(host, timeout=args.ssh_timeout)
                    mc.openclaw_entries.extend(normalize_openclaw(host, oc_report))
                except Exception as exc:
                    mc.errors.append(f"openclaw: {exc}")
            collections.append(mc)

    # --- Report ---
    if args.json:
        report = compute_json_report(collections, since=args.since, until=args.until)
        print(json.dumps(report, indent=2))
    else:
        print_text_report(collections, since=args.since, until=args.until)

    return 0


if __name__ == "__main__":
    sys.exit(main())
