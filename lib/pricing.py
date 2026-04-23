#!/usr/bin/env python3
"""Shared pricing tiers and cost calculation for Claude Code sessions.

Single source of truth. Both lib/stats.py and lib/export.py import from here
so cost numbers stay consistent across commands.
"""


# Pricing per million tokens
PRICING = {
    "opus": {
        "input": 15.0,
        "output": 75.0,
        "cache_read_discount": 0.90,   # 90% discount
        "cache_create_premium": 0.25,  # 25% premium
    },
    "sonnet": {
        "input": 3.0,
        "output": 15.0,
        "cache_read_discount": 0.90,
        "cache_create_premium": 0.25,
    },
    "haiku": {
        "input": 0.25,
        "output": 1.25,
        "cache_read_discount": 0.90,
        "cache_create_premium": 0.25,
    },
}


def detect_model_tier(model_name):
    """Detect pricing tier from model name."""
    if not model_name:
        return "sonnet"  # Default assumption
    model_lower = model_name.lower()
    if "opus" in model_lower:
        return "opus"
    elif "haiku" in model_lower:
        return "haiku"
    return "sonnet"


def calculate_cost(usage, tier):
    """Calculate cost for a single usage entry.

    Counts regular input, cache-creation (with premium), cache-read (with
    discount), and output. Anthropic's API reports input_tokens as already
    non-cached input, so it is NOT reduced by cache_read here.
    """
    pricing = PRICING.get(tier, PRICING["sonnet"])

    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    cache_create = usage.get("cache_creation_input_tokens", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)

    # Regular input — API already excludes cached tokens from input_tokens.
    regular_input = input_tokens
    input_cost = (regular_input / 1_000_000) * pricing["input"]

    # Cache creation: input price + 25% premium
    cache_create_cost = (cache_create / 1_000_000) * pricing["input"] * (1 + pricing["cache_create_premium"])

    # Cache read: input price - 90% discount
    cache_read_cost = (cache_read / 1_000_000) * pricing["input"] * (1 - pricing["cache_read_discount"])

    # Output
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    return input_cost + cache_create_cost + cache_read_cost + output_cost
