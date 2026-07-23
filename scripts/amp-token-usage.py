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
    scripts/amp-token-usage.py --since 2026-07-13            # only threads updated on/after date
    scripts/amp-token-usage.py --since 2026-07-13 --until 2026-07-13  # single day
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
from datetime import datetime, timezone
from typing import Any, Optional

# USD per 1M tokens. These are best-effort local estimates for models this
# repo already tracks. Use --pricing-file to override or add model prices.
DEFAULT_PRICING = {
    # OpenAI
    "gpt-5.5": {"input": 5.00, "cache_read": 0.50, "output": 30.00},
    "GPT-5.5": {"input": 5.00, "cache_read": 0.50, "output": 30.00},
    "gpt-5.6-sol": {"input": 5.00, "cache_read": 0.50, "output": 30.00},
    "gpt-5.6-luna": {"input": 1.00, "cache_read": 0.10, "output": 6.00},
    "gpt-5.6-terra": {"input": 2.50, "cache_read": 0.25, "output": 15.00},
    "gpt-5.4": {"input": 2.50, "cache_read": 0.25, "output": 15.00},
    "gpt-5.4-mini": {"input": 0.75, "cache_read": 0.075, "output": 4.50},
    "gpt-5.3-codex-spark": {"input": 1.75, "cache_read": 0.175, "output": 14.00},
    # Anthropic — claude-fable-5: $10/$50 per 1M, cache read at 0.1x = $1.00
    "claude-fable-5": {"input": 10.00, "cache_read": 1.00, "output": 50.00},
    # xAI — grok-4.5: $2/$6 per 1M, cached input $0.50
    "grok-4.5": {"input": 2.00, "cache_read": 0.50, "output": 6.00},
    # Fireworks — GLM-5.2 (Amp uses the full provider path as model name)
    "GLM-5.2": {"input": 1.40, "cache_read": 0.26, "output": 4.40},
    "accounts/fireworks/models/glm-5p2": {"input": 1.40, "cache_read": 0.26, "output": 4.40},
    # MiniMax
    "MiniMax-M3": {"input": 0.60, "cache_read": 0.12, "output": 2.40},
    # Moonshot
    "Kimi K2.7": {"input": 0.95, "cache_read": 0.19, "output": 4.00},
}

# Model → provider mapping for subscription attribution.
# When amp threads usage returns "unavailable", the thread's tokens
# went through a linked third-party subscription rather than Amp credits.
MODEL_PROVIDERS = {
    # OpenAI — can route through linked ChatGPT subscription or Amp credits
    "gpt-5.5": "OpenAI",
    "gpt-5.6-sol": "OpenAI",
    "gpt-5.6-luna": "OpenAI",
    "gpt-5.6-terra": "OpenAI",
    "gpt-5.4": "OpenAI",
    "gpt-5.4-mini": "OpenAI",
    "gpt-5.3-codex-spark": "OpenAI",
    # Anthropic — Amp credits only
    "claude-fable-5": "Anthropic",
    # Fireworks — Amp credits only
    "accounts/fireworks/models/glm-5p2": "Fireworks",
    "GLM-5.2": "Fireworks",
    # xAI — can route through linked X Premium+ subscription or Amp credits
    "grok-4.5": "xAI",
    # Others — Amp credits only
    "MiniMax-M3": "MiniMax",
    "Kimi K2.7": "Moonshot",
}

# Human-readable subscription names for connected providers
SUBSCRIPTION_NAMES = {
    "OpenAI": "ChatGPT Plus/Pro",
    "xAI": "X Premium+/SuperGrok",
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


def _iso_to_epoch(s: str) -> Optional[float]:
    """Parse an ISO-8601 timestamp (e.g. 2026-07-13T04:02:15.737Z) to epoch."""
    if not s:
        return None
    try:
        # Handle trailing Z
        clean = s.replace("Z", "+00:00")
        return datetime.fromisoformat(clean).timestamp()
    except (ValueError, TypeError):
        return None


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

    def cost(self, pricing: dict[str, dict[str, float]]) -> Optional[dict[str, float]]:
        """Compute implied API cost for this thread's tokens."""
        total = {"input": 0.0, "cache_read": 0.0, "output": 0.0, "total": 0.0}
        has_pricing = False
        for event in self.events:
            price = pricing_for_model(event.model, pricing)
            if not price:
                continue
            has_pricing = True
            billable = max(event.total_input_tokens - event.cache_read_input_tokens, 0)
            total["input"] += billable / 1_000_000 * price["input"]
            total["cache_read"] += event.cache_read_input_tokens / 1_000_000 * price["cache_read"]
            total["output"] += event.output_tokens / 1_000_000 * price["output"]
        if not has_pricing:
            return None
        total["total"] = total["input"] + total["cache_read"] + total["output"]
        return total


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


def list_amp_thread_ids(
    amp_bin: str,
    limit: int,
    include_archived: bool,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> list[str]:
    """Return thread IDs from ``amp threads list --json``.

    When ``since``/``until`` are provided (YYYY-MM-DD), only threads
    whose ``updated`` field falls within the inclusive range are returned.
    """
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
    since_epoch = _date_to_epoch(since) if since else None
    until_epoch = _date_to_epoch(until) + 86400 if until else None
    ids: list[str] = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        if since_epoch or until_epoch:
            updated = _iso_to_epoch(str(row.get("updated", "")))
            if updated is None:
                continue
            if since_epoch and updated < since_epoch:
                continue
            if until_epoch and updated >= until_epoch:
                continue
        ids.append(str(row["id"]))
    return ids


def export_amp_thread(amp_bin: str, thread_id: str) -> ThreadUsage:
    """Fetch one live Amp thread export."""
    data = run_amp_json(amp_bin, ["threads", "export", thread_id])
    if not isinstance(data, dict):
        raise RuntimeError(f"amp threads export {thread_id} returned an unexpected shape")
    return thread_usage_from_export(data, source=f"amp:{thread_id}")


def parse_amp_display_cost(text: str) -> Optional[dict[str, Any]]:
    """Parse ``amp threads usage`` output into a cost dict.

    Handles these formats:
    - "$5.94 (free)" → Amp credits from free bucket
    - "$0.11" → Amp credits from paid bucket
    - "$9.42 (free) + $1.66" → split between free and paid Amp credits
    - "Usage information is currently unavailable" → routed through subscription
    """
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if not first_line:
        return None

    # Subscription-routed threads have no Amp credit cost
    if "unavailable" in first_line.lower():
        return {
            "display": first_line,
            "amount_usd": None,
            "bucket": None,
            "billing_route": "subscription",
            "free_amount": None,
            "paid_amount": None,
        }

    # Parse all dollar amounts — may be split: "$9.42 (free) + $1.66"
    amounts = re.findall(r"\$([0-9]+(?:\.[0-9]+)?)", first_line)
    if not amounts:
        return {
            "display": first_line,
            "amount_usd": None,
            "bucket": None,
            "billing_route": "unknown",
            "free_amount": None,
            "paid_amount": None,
        }

    total = sum(float(a) for a in amounts)
    bucket_match = re.search(r"\(([^)]+)\)", first_line)
    bucket = bucket_match.group(1) if bucket_match else None

    # Extract free and paid portions
    free_amount = 0.0
    paid_amount = 0.0
    if len(amounts) > 1 and "+ $" in first_line:
        free_amount = float(amounts[0])
        paid_amount = float(amounts[1])
    elif bucket == "free":
        free_amount = total
    else:
        paid_amount = total

    return {
        "display": first_line,
        "amount_usd": total,
        "bucket": bucket,
        "billing_route": "amp-credits",
        "free_amount": free_amount,
        "paid_amount": paid_amount,
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


def provider_for_model(model: str) -> str:
    """Return the provider name for a model, or 'Unknown'."""
    if model in MODEL_PROVIDERS:
        return MODEL_PROVIDERS[model]
    lower_model = model.lower()
    for key, provider in MODEL_PROVIDERS.items():
        if key.lower() == lower_model:
            return provider
    # Fuzzy matches for model variants
    if "gpt-5" in lower_model or "gpt-4" in lower_model:
        return "OpenAI"
    if "claude" in lower_model:
        return "Anthropic"
    if "grok" in lower_model:
        return "xAI"
    if "glm" in lower_model:
        return "Fireworks"
    if "minimax" in lower_model:
        return "MiniMax"
    if "kimi" in lower_model:
        return "Moonshot"
    return "Unknown"


def _thread_in_date_range(thread: ThreadUsage, since_epoch: Optional[float], until_epoch: Optional[float]) -> bool:
    """Check if a thread's updated timestamp falls within the date range."""
    if since_epoch is None and until_epoch is None:
        return True
    # Try the thread-level updated field first
    ts = _iso_to_epoch(thread.updated) or _iso_to_epoch(thread.created)
    if ts is None:
        # Fall back to the last event timestamp
        last = ""
        for event in thread.events:
            if event.timestamp and event.timestamp > last:
                last = event.timestamp
        ts = _iso_to_epoch(last)
    if ts is None:
        return False  # can't date-filter undated threads
    if since_epoch and ts < since_epoch:
        return False
    if until_epoch and ts >= until_epoch:
        return False
    return True


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


def _thread_provider(thread: ThreadUsage) -> str:
    """Infer the provider for a thread from its models."""
    providers = {provider_for_model(e.model) for e in thread.events}
    if len(providers) == 1:
        return providers.pop()
    return "Mixed"


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
        "billing_route": (thread.amp_cost or {}).get("billing_route"),
        "provider": _thread_provider(thread),
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


def _thread_has_unpriced_models(thread: ThreadUsage, pricing: dict[str, dict[str, float]]) -> bool:
    """Check if any of the thread's models lack API pricing."""
    for event in thread.events:
        if not pricing_for_model(event.model, pricing):
            return True
    return False


def _thread_unpriced_model_names(thread: ThreadUsage, pricing: dict[str, dict[str, float]]) -> set[str]:
    """Return the set of model names in the thread that lack API pricing."""
    return {
        event.model for event in thread.events
        if not pricing_for_model(event.model, pricing)
    }


def _model_has_linked_subscription(model: str) -> Optional[str]:
    """Return the subscription name if this model's provider has a linked
    third-party subscription, or None if Amp credits are the only route.

    OpenAI models can route through a linked ChatGPT Plus/Pro subscription.
    xAI models can route through a linked X Premium+/SuperGrok subscription.
    All other providers (Anthropic, Fireworks, MiniMax, Moonshot) have no
    linked subscription — Amp credits are the only route.
    """
    provider = provider_for_model(model)
    if provider in SUBSCRIPTION_NAMES:
        return SUBSCRIPTION_NAMES[provider]
    return None


def _thread_subscription_route(thread: ThreadUsage) -> Optional[str]:
    """If all models in a thread route through the same linked subscription,
    return the subscription name.  If models mix subscriptions or include
    non-subscription models, return None.
    """
    subs = {_model_has_linked_subscription(e.model) for e in thread.events if e.model != "unknown"}
    # Remove None if there are also subscription-eligible models
    if len(subs) == 1:
        return subs.pop()
    return None


def _build_billing_routes(
    threads: list[ThreadUsage],
    pricing: dict[str, dict[str, float]],
) -> list[dict[str, Any]]:
    """Summarise token usage and implied API cost by billing route and provider.

    **Route classification logic:**

    For threads where ``--amp-costs`` was used, each thread is classified
    based on whether its model(s) can route through a linked third-party
    subscription:

    - **subscription** — All models in the thread belong to a provider with a
      linked subscription (OpenAI → ChatGPT Plus/Pro, xAI → X Premium+/
      SuperGrok).  The implied API value is attributed to that subscription
      (the LLM tokens went through it at no per-token cost).  Any Amp credit
      cost shown by ``amp threads usage`` is **ancillary overhead** (tool
      execution, web search, etc.) — it is tracked separately as
      ``amp_ancillary_cost``, not as per-token LLM cost.

      This covers both cases:
      * ``amp threads usage`` returns "unavailable" (Amp confirms the thread
        is subscription-routed)
      * ``amp threads usage`` returns a small dollar amount (Amp charged for
        ancillary overhead while LLM tokens went through the subscription)

    - **amp-credits** — The thread uses models from providers with no linked
      subscription (Anthropic, Fireworks, MiniMax, Moonshot).  Amp credits
      are the only billing route, so both the implied API value and the Amp
      credit cost are real costs against Amp.

    - **unknown** — ``--amp-costs`` was not used.

    The key insight: Amp display costs for subscription-eligible models
    (OpenAI, xAI) are typically 1–5% of the implied API value — clearly
    ancillary overhead, not per-token LLM cost.  For non-subscription
    models (GLM, Claude), Amp display costs are close to the implied API
    value, confirming Amp is paying for the actual tokens.
    """
    routes: dict[str, dict[str, Any]] = {}

    def _get_route(key: str) -> dict[str, Any]:
        if key not in routes:
            routes[key] = {
                "route": key,
                "threads": 0,
                "calls": 0,
                "total_input_tokens": 0,
                "output_tokens": 0,
                "implied_api_cost": 0.0,
                "amp_credit_cost": 0.0,
                "amp_free_cost": 0.0,
                "amp_paid_cost": 0.0,
                "amp_ancillary_cost": 0.0,
                "unpriced_models": set(),
            }
        return routes[key]

    for thread in threads:
        ac = thread.amp_cost or {}
        raw_route = ac.get("billing_route") or "unknown"
        implied = thread.cost(pricing)
        implied_total = implied["total"] if implied else 0.0
        amp_amount = ac.get("amount_usd")

        # Determine route based on model subscription eligibility
        sub_name = _thread_subscription_route(thread)
        if raw_route == "unknown":
            # No --amp-costs, can't determine
            key = "unknown"
        elif sub_name:
            # All models route through a linked subscription
            key = f"subscription:{sub_name}"
        else:
            # Models with no linked subscription → Amp credits
            key = "amp-credits"

        entry = _get_route(key)
        entry["threads"] += 1
        entry["calls"] += thread.calls
        entry["total_input_tokens"] += thread.total_input_tokens
        entry["output_tokens"] += thread.output_tokens

        if implied:
            entry["implied_api_cost"] += implied_total

        if isinstance(amp_amount, (int, float)):
            if key.startswith("subscription:"):
                # Amp cost on subscription-routed threads is ancillary
                # overhead, not per-token LLM cost
                entry["amp_ancillary_cost"] += float(amp_amount)
            else:
                entry["amp_credit_cost"] += float(amp_amount)
                entry["amp_free_cost"] += float(ac.get("free_amount") or 0)
                entry["amp_paid_cost"] += float(ac.get("paid_amount") or 0)

        # Track unpriced models
        entry["unpriced_models"].update(
            _thread_unpriced_model_names(thread, pricing)
        )

    # Build sorted result with display labels
    result = []
    for key, entry in sorted(routes.items(), key=lambda x: x[1]["implied_api_cost"], reverse=True):
        if key.startswith("subscription:"):
            entry["route"] = "subscription"
            entry["provider"] = key.split(":", 1)[1]
        elif key == "amp-credits":
            entry["provider"] = "Amp credits"
        elif key == "unknown":
            entry["provider"] = "Unknown"
        # Convert unpriced_models set to sorted list for JSON
        entry["unpriced_models"] = sorted(entry["unpriced_models"])
        result.append(entry)
    return result


def compute_report(
    threads: list[ThreadUsage],
    pricing: dict[str, dict[str, float]],
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> dict[str, Any]:
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

    # Amp credit cost totals (handling split costs)
    amp_cost_total = 0.0
    amp_cost_free = 0.0
    amp_cost_paid = 0.0
    amp_cost_count = 0
    for thread in threads:
        ac = thread.amp_cost or {}
        amount = ac.get("amount_usd")
        if isinstance(amount, (int, float)):
            amp_cost_total += float(amount)
            amp_cost_free += float(ac.get("free_amount") or 0)
            amp_cost_paid += float(ac.get("paid_amount") or 0)
            amp_cost_count += 1

    # Build billing route summary
    route_summary = _build_billing_routes(threads, pricing)

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
            "amp_cost_free_usd": amp_cost_free if amp_cost_count else None,
            "amp_cost_paid_usd": amp_cost_paid if amp_cost_count else None,
        },
        "billing_routes": route_summary,
        "pricing": pricing,
        "since": since,
        "until": until,
        "notes": [
            "Implied API cost = tokens × public provider list rates — what the equivalent usage would cost via direct pay-as-you-go API calls.",
            "Subscription-routed threads: LLM tokens went through a linked third-party subscription (ChatGPT Plus/Pro, X Premium+/SuperGrok) at no per-token cost. Any Amp charge is ancillary overhead (tool execution, web search), tracked separately as amp_ancillary_cost.",
            "Amp-credits threads: models from providers with no linked subscription (Anthropic, Fireworks, MiniMax, Moonshot). Amp credits are the only route — both implied API value and Amp credit cost are real costs against Amp.",
            "Amp credit cost breakdown: 'free' = Amp Free daily credits + Megawatt included usage; 'paid' = individual credits. Megawatt ($20/month) includes $20 of agent usage.",
            "Route attribution is based on model→provider→subscription eligibility, not on amp threads usage cost-ratio heuristics. It cannot detect cases where a thread mixes subscription-routed and Amp-credited calls within the same thread.",
        ],
    }


def _fmt_int(value: int) -> str:
    return f"{value:,}"


def _fmt_cost(value: Optional[dict[str, float]]) -> str:
    if not value:
        return "-"
    return f"${value['total']:.2f}"


def print_text_report(report: dict[str, Any]) -> None:
    date_range = ""
    if report.get("since") or report.get("until"):
        lo = report.get("since") or "begin"
        hi = report.get("until") or "now"
        date_range = f"  [{lo} .. {hi}]"
    print("=" * 120)
    print(f"AMP TOKEN USAGE{date_range}")
    print("=" * 120)
    print()
    print(f"{'Model':<24}{'Provider':<14}{'Threads':>8}{'Calls':>8}  {'Billable In':>13}{'Cache Read':>13}{'Output':>11}  {'Cache %':>8}  {'Implied Cost':>12}")
    print("-" * 120)
    for model, row in sorted(
        report["models"].items(),
        key=lambda item: item[1]["total_input_tokens"] + item[1]["output_tokens"],
        reverse=True,
    ):
        provider = provider_for_model(model)
        print(
            f"{model:<24}{provider:<14}{row['threads']:>8}{row['calls']:>8}  "
            f"{_fmt_int(row['billable_input_tokens']):>13}"
            f"{_fmt_int(row['cache_read_input_tokens']):>13}"
            f"{_fmt_int(row['output_tokens']):>11}  "
            f"{row['cache_read_pct']:>7.1f}%  "
            f"{_fmt_cost(row['estimated_cost']):>12}"
        )
    totals = report["totals"]
    print("-" * 120)
    print(
        f"{'TOTAL':<24}{'':<14}{totals['threads']:>8}{totals['calls']:>8}  "
        f"{_fmt_int(totals['billable_input_tokens']):>13}"
        f"{_fmt_int(totals['cache_read_input_tokens']):>13}"
        f"{_fmt_int(totals['output_tokens']):>11}  "
        f"{totals['cache_read_pct']:>7.1f}%"
    )
    if totals["amp_cost_total_usd"] is not None:
        free_str = f" (free: ${totals.get('amp_cost_free_usd', 0):.2f}, paid: ${totals.get('amp_cost_paid_usd', 0):.2f})" if totals.get("amp_cost_free_usd") else ""
        print(f"\nAmp credit cost: ${totals['amp_cost_total_usd']:.2f}{free_str} across {totals['amp_cost_threads']} threads")

    # Billing route summary
    routes = report.get("billing_routes", [])
    if routes:
        print()
        print("=" * 130)
        print("BILLING ROUTE VALUE SUMMARY")
        print("=" * 130)
        print(f"{'Route':<14}{'Provider':<24}{'Threads':>7}  {'Implied API':>12}  {'Amp Credits':>14}  {'Ancillary':>10}  {'Unpriced'}")
        print("-" * 130)
        for route in routes:
            route_label = route.get("route", "unknown")
            implied = f"${route['implied_api_cost']:.2f}"
            amp_cost = route.get("amp_credit_cost", 0)
            if amp_cost > 0:
                free_part = route.get("amp_free_cost", 0)
                paid_part = route.get("amp_paid_cost", 0)
                if free_part > 0 and paid_part > 0:
                    amp_str = f"${amp_cost:.2f} (f:${free_part:.2f}+p:${paid_part:.2f})"
                elif free_part > 0:
                    amp_str = f"${amp_cost:.2f} (free)"
                else:
                    amp_str = f"${amp_cost:.2f}"
            else:
                amp_str = "-"
            ancillary = route.get("amp_ancillary_cost", 0)
            ancillary_str = f"${ancillary:.2f}" if ancillary > 0 else "-"
            unpriced = ", ".join(route.get("unpriced_models", [])) or "-"
            print(f"{route_label:<14}{route.get('provider',''):<24}{route['threads']:>7}  {implied:>12}  {amp_str:>14}  {ancillary_str:>10}  {unpriced}")
        total_implied = sum(r["implied_api_cost"] for r in routes)
        total_amp = sum(r.get("amp_credit_cost", 0) for r in routes)
        total_ancillary = sum(r.get("amp_ancillary_cost", 0) for r in routes)
        print("-" * 130)
        print(f"{'TOTAL':<14}{'':<24}{'':>7}  ${total_implied:>10.2f}  ${total_amp:>12.2f}  ${total_ancillary:>8.2f}")

    print()
    print("Top threads by token volume:")
    for thread in report["threads"][:10]:
        label = thread["title"] or thread["id"]
        models = ",".join(thread["models"]) if thread["models"] else "-"
        token_total = thread["total_input_tokens"] + thread["output_tokens"]
        route = thread.get("billing_route") or "?"
        cost = f"  {thread['amp_cost']['display']}" if thread.get("amp_cost") else f"  [{route}]"
        print(f"  {_fmt_int(token_total):>13} tokens  {thread['id']}  {models}  {label[:70]}{cost}")
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
        live_thread_ids = list_amp_thread_ids(
            args.amp_bin, args.limit, args.include_archived,
            since=args.since, until=args.until,
        )

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

    # Apply date filtering to export-file/directory threads (live threads
    # were already filtered at list time).
    since_epoch = _date_to_epoch(args.since) if args.since else None
    until_epoch = _date_to_epoch(args.until) + 86400 if args.until else None
    result = [
        t for t in deduped.values()
        if _thread_in_date_range(t, since_epoch, until_epoch)
    ]
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
    parser.add_argument("--since", type=_parse_date, metavar="YYYY-MM-DD",
                        help="Only count threads updated on/after this date")
    parser.add_argument("--until", type=_parse_date, metavar="YYYY-MM-DD",
                        help="Only count threads updated on/before this date")
    parser.add_argument("--json", action="store_true",
                        help="Output machine-readable JSON instead of text")
    args = parser.parse_args(argv)

    try:
        pricing = load_pricing(args.pricing_file)
        threads = collect_threads(args)
        report = compute_report(threads, pricing, since=args.since, until=args.until)
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
