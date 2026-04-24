#!/usr/bin/env python3
"""Export Claude Code session index as JSON."""

import json
import os
import sys
import glob

# Shared pricing source of truth (keeps cost numbers in sync with stats.py)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pricing import PRICING, detect_model_tier, calculate_cost  # noqa: E402,F401
# Shared JSONL session parsing (see lib/parser.py).
from parser import parse_session_meta, iter_entries  # noqa: E402,F401


def parse_session(jsonl_path):
    """Build the export record: parse_session_meta() handles metadata; a
    light second pass here aggregates tokens & cost (kept here because
    export.py and stats.py are the only commands that need usage data)."""
    meta = parse_session_meta(jsonl_path, first_msg_len=200)
    if meta is None:
        return None

    total_input = 0
    total_output = 0
    total_cache_create = 0
    total_cache_read = 0
    cost = 0.0
    model = None

    for _, data in iter_entries(jsonl_path):
        try:
            if data.get("type") != "assistant":
                continue
            msg = data.get("message", {})
            usage = msg.get("usage", {})
            m = msg.get("model", "")
            if m and not model:
                model = m
            if usage:
                total_input += usage.get("input_tokens", 0)
                total_output += usage.get("output_tokens", 0)
                total_cache_create += usage.get("cache_creation_input_tokens", 0)
                total_cache_read += usage.get("cache_read_input_tokens", 0)
                tier = detect_model_tier(m)
                cost += calculate_cost(usage, tier)
        except (AttributeError, TypeError):
            continue

    return {
        "id": meta["id"],
        "name": meta["session_name"],
        "cwd": meta["cwd"],
        "first_message": meta["first_message"],
        "start_date": meta["session_start"].isoformat(),
        "last_activity": meta["last_activity"].isoformat(),
        "model": model,
        "user_messages": meta["user_msg_count"],
        "tokens": {
            "input": total_input,
            "output": total_output,
            "cache_creation": total_cache_create,
            "cache_read": total_cache_read,
            "total": total_input + total_output + total_cache_create,
        },
        "cost_estimate": round(cost, 4),
    }


def main():
    output_file = None
    args = sys.argv[1:]
    if "--output" in args:
        idx = args.index("--output")
        if idx + 1 < len(args):
            output_file = args[idx + 1]

    home = os.path.expanduser("~")
    base = os.path.join(home, ".claude", "projects")
    sessions = []

    for jsonl_path in glob.glob(f"{base}/**/*.jsonl", recursive=True):
        s = parse_session(jsonl_path)
        if s:
            sessions.append(s)

    sessions.sort(key=lambda x: x["start_date"], reverse=True)

    output = json.dumps(sessions, indent=2, ensure_ascii=False)

    if output_file:
        with open(output_file, "w") as f:
            f.write(output)
        print(f"Exported {len(sessions)} sessions to {output_file}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
