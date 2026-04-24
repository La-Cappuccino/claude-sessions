#!/usr/bin/env python3
"""Token usage and cost statistics for Claude Code sessions."""

import json
import os
import sys
import glob
from datetime import datetime, timedelta
from collections import defaultdict

# Shared pricing source of truth
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pricing import PRICING, detect_model_tier, calculate_cost  # noqa: E402,F401


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

    # min_date is compared against each entry's own timestamp (naive local
    # datetime). Normalize here so comparisons don't mix tz-aware and naive.
    if min_date is not None and min_date.tzinfo is not None:
        min_date = min_date.replace(tzinfo=None)

    try:
        with open(jsonl_path, "r") as f:
            for line in f:
                try:
                    data = json.loads(line)

                    # Get cwd
                    if not stats["cwd"]:
                        c = data.get("cwd")
                        if c and c.startswith("/"):
                            stats["cwd"] = c

                    # Parse entry timestamp once; used for both window filter
                    # and first/last tracking.
                    entry_dt = None
                    ts = data.get("timestamp")
                    if ts:
                        try:
                            entry_dt = datetime.fromisoformat(
                                ts.replace("Z", "+00:00")
                            ).replace(tzinfo=None)
                            if not stats["first_date"] or entry_dt < stats["first_date"]:
                                stats["first_date"] = entry_dt
                            if not stats["last_date"] or entry_dt > stats["last_date"]:
                                stats["last_date"] = entry_dt
                        except (ValueError, TypeError):
                            pass

                    # Assistant messages have usage data
                    if data.get("type") == "assistant":
                        # Per-entry window filter: only count usage from
                        # entries whose timestamp is within the window.
                        # Entries without a timestamp are skipped when
                        # filtering (conservative — avoids over-counting).
                        if min_date is not None:
                            if entry_dt is None or entry_dt < min_date:
                                continue

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

                except (json.JSONDecodeError, KeyError, AttributeError, TypeError):
                    continue
    except Exception as e:
        print(
            f"  Warning: failed to parse {jsonl_path}: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
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
