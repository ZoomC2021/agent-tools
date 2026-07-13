#!/usr/bin/env python3
"""Count Amp thread token usage from ``amp threads export`` payloads.

Amp exposes account and display-cost information directly:

    amp usage
    amp threads usage <thread-id>

For token-level analysis, ``amp threads export <thread-id>`` includes a
``usage`` object on assistant messages.  This script aggregates those usage
objects by thread and model, either from live Amp CLI exports or from saved
JSON export files.

Usage::

    scripts/amp-token-usage.py
    scripts/amp-token-usage.py --limit 250 --include-archived
    scripts/amp-token-usage.py --thread T-...
    scripts/amp-token-usage.py --export thread.json --json
    scripts/amp-token-usage.py --amp-costs
"""

from __future__ import annotations

import argparse
import concurrent.futures
import glob
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any, Optional

# USD per 1M tokens. These are best-effort local estimates for models this
# repo already tracks. Use --pricing-file to override or add model prices.
DEFAULT_PRICING = {
    "gpt-5.5": {"input": 5.00, "cache_read": 0.50, "output": 30.00},
    "GPT-5.5": {"input": 5.00, "cache_read": 0.50, "output": 30.00},
    "gpt-5.6-sol": {"input": 5.00, "cache_read": 0.50, "output": 30.00},
    "gpt-5.6-luna": {"input": 1.00, "cache_read": 0.10, "output": 6.00},
    "gpt-5.6-terra": {"input": 2.50, "cache_read": 0.25, "output": 15.00},
    "gpt-5.4": {"input": 2.50, "cache_read": 0.25, "output": 15.00},
    "gpt-5.4-mini": {"input": 0.75, "cache_read": 0.075, "output": 4.50},
    "gpt-5.3-codex-spark": {"input": 1.75, "cache_read": 0.175, "output": 14.00},
    "MiniMax-M3": {"input": 0.60, "cache_read": 0.12, "output": 2.40},
    "GLM-5.2": {"input": 1.40, "cache_read": 0.26, "output": 4.40},
    "Kimi K2.7": {"input": 0.95, "cache_read": 0.19, "output": 4.00},
}


@dataclass
class UsageEvent:
    """One Amp assistant-message usage record."""

    model: str = "unknown"
    timestamp: str = ""
    input_tokens: int = 0
    total_input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    max_input_tokens: int = 0


@dataclass
class ThreadUsage:
    """Token usage extracted from one exported Amp thread."""

    thread_id: str
    title: str = ""
    created: str = ""
    updated: str = ""
    message_count: int = 0
    source: str = ""
    events: list[UsageEvent] = field(default_factory=list)
    amp_cost: Optional[dict[str, Any]] = None

    @property
    def calls(self) -> int:
        return len(self.events)

    @property
    def total_input_tokens(self) -> int:
        return sum(event.total_input_tokens for event in self.events)

    @property
    def output_tokens(self) -> int:
        return sum(event.output_tokens for event in self.events)

    @property
    def cache_read_input_tokens(self) -> int:
        return sum(event.cache_read_input_tokens for event in self.events)

    @property
    def cache_creation_input_tokens(self) -> int:
        return sum(event.cache_creation_input_tokens for event in self.events)

    @property
    def billable_input_tokens(self) -> int:
        return max(self.total_input_tokens - self.cache_read_input_tokens, 0)


@dataclass
class ModelTotals:
    """Aggregated totals for one model."""

    model: str
    thread_ids: set[str] = field(default_factory=set)
    calls: int = 0
    input_tokens: int = 0
    total_input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    max_input_tokens: int = 0
    first_timestamp: str = ""
    last_timestamp: str = ""

    @property
    def threads(self) -> int:
        return len(self.thread_ids)

    @property
    def billable_input_tokens(self) -> int:
        return max(self.total_input_tokens - self.cache_read_input_tokens, 0)

    @property
    def cache_read_pct(self) -> float:
        if self.total_input_tokens == 0:
            return 0.0
        return self.cache_read_input_tokens / self.total_input_tokens * 100

    def cost(self, pricing: dict[str, dict[str, float]]) -> Optional[dict[str, float]]:
        price = pricing_for_model(self.model, pricing)
        if not price:
            return None
        input_cost = self.billable_input_tokens / 1_000_000 * price["input"]
        cache_read_cost = self.cache_read_input_tokens / 1_000_000 * price["cache_read"]
        output_cost = self.output_tokens / 1_000_000 * price["output"]
        return {
            "input": input_cost,
            "cache_read": cache_read_cost,
            "output": output_cost,
            "total": input_cost + cache_read_cost + output_cost,
        }


def _as_int(value: Any) -> int:
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return 0
    return 0


def usage_event_from_dict(data: dict[str, Any]) -> UsageEvent:
    """Convert an Amp ``usage`` object into a normalized UsageEvent."""
    input_tokens = _as_int(data.get("inputTokens"))
    cache_read = _as_int(data.get("cacheReadInputTokens"))
    cache_creation = _as_int(data.get("cacheCreationInputTokens"))
    output_tokens = _as_int(data.get("outputTokens"))
    total_input = _as_int(data.get("totalInputTokens"))
    if total_input == 0:
        total_input = input_tokens + cache_read + cache_creation
    return UsageEvent(
        model=str(data.get("model") or "unknown"),
        timestamp=str(data.get("timestamp") or ""),
        input_tokens=input_tokens,
        total_input_tokens=total_input,
        output_tokens=output_tokens,
        cache_read_input_tokens=cache_read,
        cache_creation_input_tokens=cache_creation,
        max_input_tokens=_as_int(data.get("maxInputTokens")),
    )


def thread_usage_from_export(data: dict[str, Any], source: str = "") -> ThreadUsage:
    """Extract ThreadUsage from a parsed ``amp threads export`` payload."""
    messages = data.get("messages", [])
    if not isinstance(messages, list):
        messages = []
    thread_id = str(data.get("id") or os.path.basename(source) or "unknown")
    thread = ThreadUsage(
        thread_id=thread_id,
        title=str(data.get("title") or ""),
        created=str(data.get("created") or ""),
        updated=str(data.get("updatedAt") or data.get("updated") or ""),
        message_count=len(messages),
        source=source,
    )
    for message in messages:
        if not isinstance(message, dict):
            continue
        usage = message.get("usage")
        if isinstance(usage, dict):
            thread.events.append(usage_event_from_dict(usage))
    return thread


def load_export_file(path: str) -> ThreadUsage:
    """Load one saved ``amp threads export`` JSON file."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not an Amp thread export object")
    return thread_usage_from_export(data, source=path)


def load_export_dir(path: str) -> list[ThreadUsage]:
    """Load every ``*.json`` export under a directory."""
    threads: list[ThreadUsage] = []
    for export_path in sorted(glob.glob(os.path.join(path, "*.json"))):
        threads.append(load_export_file(export_path))
    return threads


def run_amp_json(amp_bin: str, args: list[str]) -> Any:
    """Run an Amp command and parse stdout as JSON."""
    proc = subprocess.run(
        [amp_bin, *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        message = proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}"
        raise RuntimeError(f"amp {' '.join(args)} failed: {message}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"amp {' '.join(args)} did not return valid JSON") from exc


def run_amp_text(amp_bin: str, args: list[str]) -> str:
    """Run an Amp command and return stdout."""
    proc = subprocess.run(
        [amp_bin, *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        message = proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}"
        raise RuntimeError(f"amp {' '.join(args)} failed: {message}")
    return proc.stdout


def list_amp_thread_ids(amp_bin: str, limit: int, include_archived: bool) -> list[str]:
    """Return thread IDs from ``amp threads list --json``."""
    args = ["threads", "list", "--limit", str(limit), "--json"]
    if include_archived:
        args.append("--include-archived")
    data = run_amp_json(amp_bin, args)
    if isinstance(data, dict):
        rows = data.get("threads", [])
    else:
        rows = data
    if not isinstance(rows, list):
        raise RuntimeError("amp threads list returned an unexpected shape")
    ids: list[str] = []
    for row in rows:
        if isinstance(row, dict) and row.get("id"):
            ids.append(str(row["id"]))
    return ids


def export_amp_thread(amp_bin: str, thread_id: str) -> ThreadUsage:
    """Fetch one live Amp thread export."""
    data = run_amp_json(amp_bin, ["threads", "export", thread_id])
    if not isinstance(data, dict):
        raise RuntimeError(f"amp threads export {thread_id} returned an unexpected shape")
    return thread_usage_from_export(data, source=f"amp:{thread_id}")


def parse_amp_display_cost(text: str) -> Optional[dict[str, Any]]:
    """Parse the first line of ``amp threads usage`` output."""
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if not first_line:
        return None
    match = re.search(r"\$([0-9]+(?:\.[0-9]+)?)", first_line)
    bucket_match = re.search(r"\(([^)]+)\)", first_line)
    return {
        "display": first_line,
        "amount_usd": float(match.group(1)) if match else None,
        "bucket": bucket_match.group(1) if bucket_match else None,
    }


def fetch_amp_display_cost(amp_bin: str, thread_id: str) -> Optional[dict[str, Any]]:
    """Fetch Amp credit cost for one thread."""
    text = run_amp_text(amp_bin, ["threads", "usage", thread_id])
    return parse_amp_display_cost(text)


def normalize_pricing_entry(entry: dict[str, Any]) -> dict[str, float]:
    """Accept both this script's keys and Devin script's in/cache/out keys."""
    return {
        "input": float(entry.get("input", entry.get("in", 0.0))),
        "cache_read": float(entry.get("cache_read", entry.get("cache", 0.0))),
        "output": float(entry.get("output", entry.get("out", 0.0))),
    }


def load_pricing(path: Optional[str]) -> dict[str, dict[str, float]]:
    pricing = {model: normalize_pricing_entry(values) for model, values in DEFAULT_PRICING.items()}
    if not path:
        return pricing
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("pricing file must be a JSON object keyed by model")
    for model, values in data.items():
        if not isinstance(values, dict):
            raise ValueError(f"pricing for {model} must be an object")
        pricing[str(model)] = normalize_pricing_entry(values)
    return pricing


def pricing_for_model(model: str, pricing: dict[str, dict[str, float]]) -> Optional[dict[str, float]]:
    if model in pricing:
        return pricing[model]
    lower_model = model.lower()
    for key, value in pricing.items():
        if key.lower() == lower_model:
            return value
    # Dated model variants, e.g. "gpt-5.4-2026-03-05" -> "gpt-5.4"
    base = re.sub(r"-\d{4}-\d{2}-\d{2}$", "", model)
    if base != model and base in pricing:
        return pricing[base]
    lower_base = base.lower()
    if lower_base != lower_model:
        for key, value in pricing.items():
            if key.lower() == lower_base:
                return value
    return None


def aggregate_by_model(threads: list[ThreadUsage]) -> dict[str, ModelTotals]:
    per_model: dict[str, ModelTotals] = {}
    for thread in threads:
        for event in thread.events:
            totals = per_model.setdefault(event.model, ModelTotals(model=event.model))
            totals.thread_ids.add(thread.thread_id)
            totals.calls += 1
            totals.input_tokens += event.input_tokens
            totals.total_input_tokens += event.total_input_tokens
            totals.output_tokens += event.output_tokens
            totals.cache_read_input_tokens += event.cache_read_input_tokens
            totals.cache_creation_input_tokens += event.cache_creation_input_tokens
            totals.max_input_tokens = max(totals.max_input_tokens, event.max_input_tokens)
            if event.timestamp:
                if not totals.first_timestamp or event.timestamp < totals.first_timestamp:
                    totals.first_timestamp = event.timestamp
                if event.timestamp > totals.last_timestamp:
                    totals.last_timestamp = event.timestamp
    return per_model


def _thread_to_json(thread: ThreadUsage) -> dict[str, Any]:
    models = sorted({event.model for event in thread.events})
    return {
        "id": thread.thread_id,
        "title": thread.title,
        "created": thread.created,
        "updated": thread.updated,
        "message_count": thread.message_count,
        "calls": thread.calls,
        "models": models,
        "total_input_tokens": thread.total_input_tokens,
        "billable_input_tokens": thread.billable_input_tokens,
        "cache_read_input_tokens": thread.cache_read_input_tokens,
        "cache_creation_input_tokens": thread.cache_creation_input_tokens,
        "output_tokens": thread.output_tokens,
        "amp_cost": thread.amp_cost,
        "source": thread.source,
    }


def _model_to_json(totals: ModelTotals, pricing: dict[str, dict[str, float]]) -> dict[str, Any]:
    return {
        "threads": totals.threads,
        "calls": totals.calls,
        "input_tokens": totals.input_tokens,
        "total_input_tokens": totals.total_input_tokens,
        "billable_input_tokens": totals.billable_input_tokens,
        "cache_read_input_tokens": totals.cache_read_input_tokens,
        "cache_creation_input_tokens": totals.cache_creation_input_tokens,
        "output_tokens": totals.output_tokens,
        "max_input_tokens": totals.max_input_tokens,
        "cache_read_pct": totals.cache_read_pct,
        "first_timestamp": totals.first_timestamp,
        "last_timestamp": totals.last_timestamp,
        "estimated_cost": totals.cost(pricing),
    }


def compute_report(threads: list[ThreadUsage], pricing: dict[str, dict[str, float]]) -> dict[str, Any]:
    per_model = aggregate_by_model(threads)
    model_rows = {
        model: _model_to_json(totals, pricing)
        for model, totals in sorted(per_model.items(), key=lambda item: item[0].lower())
    }
    totals = ModelTotals(model="TOTAL")
    for thread in threads:
        if thread.events:
            totals.thread_ids.add(thread.thread_id)
        for event in thread.events:
            totals.calls += 1
            totals.input_tokens += event.input_tokens
            totals.total_input_tokens += event.total_input_tokens
            totals.output_tokens += event.output_tokens
            totals.cache_read_input_tokens += event.cache_read_input_tokens
            totals.cache_creation_input_tokens += event.cache_creation_input_tokens
            totals.max_input_tokens = max(totals.max_input_tokens, event.max_input_tokens)

    amp_cost_total = 0.0
    amp_cost_count = 0
    for thread in threads:
        amount = (thread.amp_cost or {}).get("amount_usd")
        if isinstance(amount, (int, float)):
            amp_cost_total += float(amount)
            amp_cost_count += 1

    return {
        "models": model_rows,
        "threads": sorted(
            (_thread_to_json(thread) for thread in threads),
            key=lambda row: (row["total_input_tokens"] + row["output_tokens"]),
            reverse=True,
        ),
        "totals": {
            "threads": totals.threads,
            "calls": totals.calls,
            "input_tokens": totals.input_tokens,
            "total_input_tokens": totals.total_input_tokens,
            "billable_input_tokens": totals.billable_input_tokens,
            "cache_read_input_tokens": totals.cache_read_input_tokens,
            "cache_creation_input_tokens": totals.cache_creation_input_tokens,
            "output_tokens": totals.output_tokens,
            "cache_read_pct": totals.cache_read_pct,
            "amp_cost_threads": amp_cost_count,
            "amp_cost_total_usd": amp_cost_total if amp_cost_count else None,
        },
        "pricing": pricing,
        "notes": [
            "Estimated API costs use local pricing assumptions and are separate from Amp credits.",
            "Amp thread usage cost reflects Amp credits only and excludes direct customer-managed provider billing.",
        ],
    }


def _fmt_int(value: int) -> str:
    return f"{value:,}"


def _fmt_cost(value: Optional[dict[str, float]]) -> str:
    if not value:
        return "-"
    return f"${value['total']:.2f}"


def print_text_report(report: dict[str, Any]) -> None:
    print("=" * 104)
    print("AMP TOKEN USAGE")
    print("=" * 104)
    print()
    print(f"{'Model':<24}{'Threads':>8}{'Calls':>8}  {'Billable In':>13}{'Cache Read':>13}{'Output':>11}  {'Cache %':>8}  {'Est. Cost':>10}")
    print("-" * 104)
    for model, row in sorted(
        report["models"].items(),
        key=lambda item: item[1]["total_input_tokens"] + item[1]["output_tokens"],
        reverse=True,
    ):
        print(
            f"{model:<24}{row['threads']:>8}{row['calls']:>8}  "
            f"{_fmt_int(row['billable_input_tokens']):>13}"
            f"{_fmt_int(row['cache_read_input_tokens']):>13}"
            f"{_fmt_int(row['output_tokens']):>11}  "
            f"{row['cache_read_pct']:>7.1f}%  "
            f"{_fmt_cost(row['estimated_cost']):>10}"
        )
    totals = report["totals"]
    print("-" * 104)
    print(
        f"{'TOTAL':<24}{totals['threads']:>8}{totals['calls']:>8}  "
        f"{_fmt_int(totals['billable_input_tokens']):>13}"
        f"{_fmt_int(totals['cache_read_input_tokens']):>13}"
        f"{_fmt_int(totals['output_tokens']):>11}  "
        f"{totals['cache_read_pct']:>7.1f}%"
    )
    if totals["amp_cost_total_usd"] is not None:
        print(f"\nAmp display cost total: ${totals['amp_cost_total_usd']:.2f} across {totals['amp_cost_threads']} threads")
    print()
    print("Top threads by token volume:")
    for thread in report["threads"][:10]:
        label = thread["title"] or thread["id"]
        models = ",".join(thread["models"]) if thread["models"] else "-"
        token_total = thread["total_input_tokens"] + thread["output_tokens"]
        cost = f"  {thread['amp_cost']['display']}" if thread.get("amp_cost") else ""
        print(f"  {_fmt_int(token_total):>13} tokens  {thread['id']}  {models}  {label[:80]}{cost}")
    print()
    for note in report["notes"]:
        print(f"Note: {note}")


def collect_threads(args: argparse.Namespace) -> list[ThreadUsage]:
    threads: list[ThreadUsage] = []
    for export_path in args.exports:
        threads.append(load_export_file(export_path))
    for export_dir in args.export_dirs:
        threads.extend(load_export_dir(export_dir))

    live_thread_ids = list(args.threads)
    if not threads and not live_thread_ids:
        live_thread_ids = list_amp_thread_ids(args.amp_bin, args.limit, args.include_archived)

    # Fetch live thread exports concurrently. Each ``amp threads export`` is an
    # independent network round-trip, so a bounded thread pool speeds this up
    # substantially without overwhelming the Amp API. Errors for individual
    # threads are reported on stderr but do not abort the whole run.
    if live_thread_ids:
        max_workers = max(1, min(args.concurrency, len(live_thread_ids)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_id = {
                executor.submit(export_amp_thread, args.amp_bin, tid): tid
                for tid in live_thread_ids
            }
            for future in concurrent.futures.as_completed(future_to_id):
                tid = future_to_id[future]
                try:
                    threads.append(future.result())
                except (RuntimeError, OSError, json.JSONDecodeError) as exc:
                    print(f"warning: export {tid} failed: {exc}", file=sys.stderr)

    deduped: dict[str, ThreadUsage] = {}
    for thread in threads:
        key = thread.thread_id or thread.source
        deduped[key] = thread

    result = list(deduped.values())
    if args.amp_costs:
        cost_ids = [t.thread_id for t in result if t.thread_id]
        if cost_ids:
            max_workers = max(1, min(args.concurrency, len(cost_ids)))
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_thread = {
                    executor.submit(fetch_amp_display_cost, args.amp_bin, tid): t
                    for t, tid in zip(result, cost_ids)
                }
                for future in concurrent.futures.as_completed(future_to_thread):
                    thread = future_to_thread[future]
                    try:
                        thread.amp_cost = future.result()
                    except RuntimeError as exc:
                        print(f"warning: amp threads usage {thread.thread_id} failed: {exc}", file=sys.stderr)
    return result


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Count Amp token usage from live threads or saved amp threads export JSON."
    )
    parser.add_argument("--thread", dest="threads", action="append", default=[],
                        help="Amp thread ID or URL to export and analyze; repeatable")
    parser.add_argument("--export", dest="exports", action="append", default=[],
                        help="Saved amp threads export JSON file; repeatable")
    parser.add_argument("--export-dir", dest="export_dirs", action="append", default=[],
                        help="Directory of saved *.json thread exports; repeatable")
    parser.add_argument("--limit", type=int, default=100,
                        help="Maximum live threads to list when no --thread/--export is provided")
    parser.add_argument("--include-archived", action="store_true",
                        help="Include archived threads when listing live Amp threads")
    parser.add_argument("--amp-bin", default="amp",
                        help="Amp executable path (default: %(default)s)")
    parser.add_argument("--amp-costs", action="store_true",
                        help="Also call amp threads usage for each thread and include Amp credit cost")
    parser.add_argument("--concurrency", type=int, default=8,
                        help="Max parallel amp threads export/usage calls (default: %(default)s)")
    parser.add_argument("--pricing-file",
                        help="JSON pricing override keyed by model, values per 1M tokens")
    parser.add_argument("--json", action="store_true",
                        help="Output machine-readable JSON instead of text")
    args = parser.parse_args(argv)

    try:
        pricing = load_pricing(args.pricing_file)
        threads = collect_threads(args)
        report = compute_report(threads, pricing)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_text_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
