#!/usr/bin/env python3
"""Token usage and cost statistics for Claude Code sessions."""

import json
import os
import sys
import glob
from datetime import datetime, timedelta
from collections import defaultdict


# Pricing per million tokens
PRICING = {
    "opus": {
        "input": 15.0,
        "output": 75.0,
        "cache_read_discount": 0.90,   # 90% discount
        "cache_create_premium": 0.25,   # 25% premium
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
    """Calculate cost for a single usage entry."""
    pricing = PRICING.get(tier, PRICING["sonnet"])

    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    cache_create = usage.get("cache_creation_input_tokens", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)

    # Anthropic's API returns input_tokens as already non-cached input;
    # cache_read/cache_create are reported separately. Don't subtract again.
    regular_input = input_tokens
    input_cost = (regular_input / 1_000_000) * pricing["input"]

    # Cache creation: input price + 25% premium
    cache_create_cost = (cache_create / 1_000_000) * pricing["input"] * (1 + pricing["cache_create_premium"])

    # Cache read: input price - 90% discount
    cache_read_cost = (cache_read / 1_000_000) * pricing["input"] * (1 - pricing["cache_read_discount"])

    # Output
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    return input_cost + cache_create_cost + cache_read_cost + output_cost


def parse_session_stats(jsonl_path, min_date=None):
    """Parse token usage from a session JSONL file."""
    stats = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "cost": 0.0,
        "messages": 0,
        "cwd": None,
        "model": None,
        "first_date": None,
        "last_date": None,
    }

    try:
        mtime = os.path.getmtime(jsonl_path)
        if min_date:
            file_date = datetime.fromtimestamp(mtime)
            if file_date < min_date:
                return None

        with open(jsonl_path, "r") as f:
            for line in f:
                try:
                    data = json.loads(line)

                    # Get cwd
                    if not stats["cwd"]:
                        c = data.get("cwd")
                        if c and c.startswith("/"):
                            stats["cwd"] = c

                    # Get timestamp
                    ts = data.get("timestamp")
                    if ts:
                        try:
                            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                            if not stats["first_date"] or dt < stats["first_date"]:
                                stats["first_date"] = dt
                            if not stats["last_date"] or dt > stats["last_date"]:
                                stats["last_date"] = dt
                        except (ValueError, TypeError):
                            pass

                    # Assistant messages have usage data
                    if data.get("type") == "assistant":
                        msg = data.get("message", {})
                        usage = msg.get("usage", {})
                        model = msg.get("model", "")

                        if model and not stats["model"]:
                            stats["model"] = model

                        if usage:
                            tier = detect_model_tier(model)
                            input_t = usage.get("input_tokens", 0)
                            output_t = usage.get("output_tokens", 0)
                            cache_create = usage.get("cache_creation_input_tokens", 0)
                            cache_read = usage.get("cache_read_input_tokens", 0)

                            stats["input_tokens"] += input_t
                            stats["output_tokens"] += output_t
                            stats["cache_creation_input_tokens"] += cache_create
                            stats["cache_read_input_tokens"] += cache_read
                            stats["cost"] += calculate_cost(usage, tier)
                            stats["messages"] += 1

                except (json.JSONDecodeError, KeyError):
                    continue
    except Exception:
        return None

    if stats["messages"] == 0:
        return None

    return stats


def format_tokens(n):
    """Format token count with K/M suffix."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


def main():
    days = None
    args = sys.argv[1:]
    if args:
        try:
            days = int(args[0])
        except ValueError:
            pass

    min_date = None
    if days:
        min_date = datetime.now() - timedelta(days=days)

    home = os.path.expanduser("~")
    base = os.path.join(home, ".claude", "projects")

    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    WHITE = "\033[37;1m"
    RESET = "\033[0m"

    total_stats = {
        "sessions": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "cost": 0.0,
        "messages": 0,
    }

    project_costs = defaultdict(float)
    project_sessions = defaultdict(int)
    model_usage = defaultdict(int)
    earliest_date = None
    latest_date = None

    for proj_dir in glob.glob(f"{base}/*/"):
        for jsonl_path in glob.glob(f"{proj_dir}*.jsonl"):
            stats = parse_session_stats(jsonl_path, min_date)
            if not stats:
                continue

            total_stats["sessions"] += 1
            total_stats["input_tokens"] += stats["input_tokens"]
            total_stats["output_tokens"] += stats["output_tokens"]
            total_stats["cache_creation_input_tokens"] += stats["cache_creation_input_tokens"]
            total_stats["cache_read_input_tokens"] += stats["cache_read_input_tokens"]
            total_stats["cost"] += stats["cost"]
            total_stats["messages"] += stats["messages"]

            # Track by project
            cwd = stats["cwd"] or "(unknown)"
            project_name = os.path.basename(cwd) if cwd != "(unknown)" else cwd
            project_costs[project_name] += stats["cost"]
            project_sessions[project_name] += 1

            # Track model
            if stats["model"]:
                tier = detect_model_tier(stats["model"])
                model_usage[tier] += stats["messages"]

            # Track date range
            if stats["first_date"]:
                if not earliest_date or stats["first_date"] < earliest_date:
                    earliest_date = stats["first_date"]
            if stats["last_date"]:
                if not latest_date or stats["last_date"] > latest_date:
                    latest_date = stats["last_date"]

    # Display
    period = f"last {days} days" if days else "all time"
    print(f"\n{BOLD}Claude Code Usage Stats{RESET} ({period})")
    print("\u2500" * 50)

    total_tokens = total_stats["input_tokens"] + total_stats["output_tokens"] + total_stats["cache_creation_input_tokens"]

    print(f"\n  {WHITE}Sessions:{RESET}        {total_stats['sessions']}")
    print(f"  {WHITE}API calls:{RESET}       {total_stats['messages']}")
    print(f"  {WHITE}Total tokens:{RESET}    {format_tokens(total_tokens)}")
    print(f"    Input:          {format_tokens(total_stats['input_tokens'])}")
    print(f"    Output:         {format_tokens(total_stats['output_tokens'])}")
    print(f"    Cache create:   {format_tokens(total_stats['cache_creation_input_tokens'])}")
    print(f"    Cache read:     {format_tokens(total_stats['cache_read_input_tokens'])}")
    print(f"  {WHITE}Est. cost:{RESET}       {RED}${total_stats['cost']:.2f}{RESET}")

    if earliest_date and latest_date:
        print(f"  {WHITE}Date range:{RESET}     {earliest_date.strftime('%Y-%m-%d')} to {latest_date.strftime('%Y-%m-%d')}")

    # Model breakdown
    if model_usage:
        print(f"\n  {BOLD}Model Usage:{RESET}")
        for tier, count in sorted(model_usage.items(), key=lambda x: -x[1]):
            print(f"    {CYAN}{tier.capitalize():<10}{RESET} {count} calls")

    # Top projects by cost
    if project_costs:
        print(f"\n  {BOLD}Top Projects by Cost:{RESET}")
        sorted_projects = sorted(project_costs.items(), key=lambda x: -x[1])[:10]
        for proj, cost in sorted_projects:
            sessions_count = project_sessions[proj]
            print(f"    {GREEN}{proj:<30}{RESET} {RED}${cost:.2f}{RESET}  ({sessions_count} sessions)")

    print()


if __name__ == "__main__":
    main()
