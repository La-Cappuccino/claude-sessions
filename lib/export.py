#!/usr/bin/env python3
"""Export Claude Code session index as JSON."""

import json
import os
import sys
import glob
from datetime import datetime

# Shared pricing source of truth (keeps cost numbers in sync with stats.py)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pricing import PRICING, detect_model_tier, calculate_cost  # noqa: E402,F401


def get_session_start(jsonl_path):
    """Return the first entry's timestamp. Falls back to file mtime if no
    timestamped entry found (happens for ~3% of sessions that start with
    permission-mode/file-history-snapshot/agent-setting/custom-title)."""
    try:
        with open(jsonl_path, "r") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    ts = d.get("timestamp")
                    if ts:
                        return datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
                except (json.JSONDecodeError, KeyError):
                    continue
    except Exception:
        pass
    return datetime.fromtimestamp(os.path.getmtime(jsonl_path))


def parse_session(jsonl_path):
    session_id = os.path.basename(jsonl_path).replace(".jsonl", "")
    session_name = None
    first_msg = None
    cwd = None
    total_input = 0
    total_output = 0
    total_cache_create = 0
    total_cache_read = 0
    cost = 0.0
    model = None
    user_msg_count = 0

    try:
        with open(jsonl_path, "r") as f:
            for line in f:
                try:
                    data = json.loads(line)

                    if not cwd:
                        c = data.get("cwd")
                        if c and c.startswith("/"):
                            cwd = c

                    if data.get("type") == "custom-title":
                        session_name = data.get("customTitle")

                    if data.get("type") == "summary":
                        t = data.get("summary", {}).get("title")
                        if t and not session_name:
                            session_name = t

                    if data.get("type") == "user":
                        msg = data.get("message", {})
                        if msg.get("role") == "user":
                            content = msg.get("content", "")
                            if isinstance(content, str) and content.strip():
                                if not first_msg:
                                    first_msg = content[:200].replace("\n", " ").strip()
                                user_msg_count += 1
                            elif isinstance(content, list):
                                for c in content:
                                    if isinstance(c, dict) and c.get("type") == "text":
                                        if not first_msg:
                                            first_msg = c["text"][:200].replace("\n", " ").strip()
                                        user_msg_count += 1
                                        break

                    if data.get("type") == "assistant":
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

                except (json.JSONDecodeError, KeyError, AttributeError, TypeError):
                    continue
    except Exception as e:
        print(
            f"  Warning: failed to parse {jsonl_path}: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        return None

    mtime = os.path.getmtime(jsonl_path)
    last_activity = datetime.fromtimestamp(mtime)
    session_start = get_session_start(jsonl_path)

    return {
        "id": session_id,
        "name": session_name,
        "cwd": cwd,
        "first_message": first_msg,
        "start_date": session_start.isoformat(),
        "last_activity": last_activity.isoformat(),
        "model": model,
        "user_messages": user_msg_count,
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

    for proj_dir in glob.glob(f"{base}/*/"):
        for jsonl_path in glob.glob(f"{proj_dir}*.jsonl"):
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
