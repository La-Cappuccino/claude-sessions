#!/usr/bin/env python3
"""List and search Claude Code sessions with correct path resolution."""

import json
import os
import sys
import glob
from datetime import datetime


def get_cwd_from_jsonl(jsonl_path):
    """Extract the real cwd from JSONL entries instead of decoding folder name."""
    try:
        with open(jsonl_path, "r") as f:
            for line in f:
                try:
                    # Fast string search before parsing JSON
                    if '"cwd"' not in line:
                        continue
                    data = json.loads(line)
                    cwd = data.get("cwd")
                    if cwd and cwd.startswith("/"):
                        return cwd
                except (json.JSONDecodeError, KeyError):
                    continue
    except Exception:
        pass
    return None


def parse_session(jsonl_path):
    """Parse a session JSONL file for metadata."""
    session_id = os.path.basename(jsonl_path).replace(".jsonl", "")
    session_name = None
    first_msg = None
    cwd = None
    user_msg_count = 0

    try:
        with open(jsonl_path, "r") as f:
            for line in f:
                try:
                    data = json.loads(line)

                    # Get cwd from first entry that has it
                    if not cwd:
                        c = data.get("cwd")
                        if c and c.startswith("/"):
                            cwd = c

                    # Session name from custom-title
                    if data.get("type") == "custom-title":
                        session_name = data.get("customTitle")

                    # Fallback name from summary
                    if data.get("type") == "summary":
                        t = data.get("summary", {}).get("title")
                        if t and not session_name:
                            session_name = t

                    # First user message for preview
                    if data.get("type") == "user":
                        msg = data.get("message", {})
                        if msg.get("role") == "user":
                            content = msg.get("content", "")
                            # Skip tool results
                            if isinstance(content, list):
                                # Check if it's just tool results
                                has_text = False
                                for c in content:
                                    if isinstance(c, dict):
                                        if c.get("type") == "tool_result":
                                            continue
                                        if c.get("type") == "text":
                                            has_text = True
                                            if not first_msg:
                                                first_msg = c["text"][:120].replace("\n", " ").strip()
                                if not has_text:
                                    continue
                            elif isinstance(content, str) and content.strip():
                                if not first_msg:
                                    first_msg = content[:120].replace("\n", " ").strip()
                            else:
                                continue
                            user_msg_count += 1

                except (json.JSONDecodeError, KeyError):
                    continue
    except Exception:
        return None

    mtime = os.path.getmtime(jsonl_path)
    dt = datetime.fromtimestamp(mtime)
    size_kb = os.path.getsize(jsonl_path) / 1024

    return {
        "id": session_id,
        "dir": cwd or "(unknown)",
        "name": session_name,
        "first_msg": first_msg or "(empty session)",
        "date": dt.strftime("%Y-%m-%d %H:%M"),
        "mtime": mtime,
        "size": size_kb,
        "user_msg_count": user_msg_count,
    }


def main():
    count = 20
    search = ""

    args = sys.argv[1:]
    if args:
        try:
            count = int(args[0])
            args = args[1:]
        except ValueError:
            # First arg is search term, not count
            search = args[0].lower()
            args = args[1:]

    if args and not search:
        search = " ".join(args).lower()

    home = os.path.expanduser("~")
    base = os.path.join(home, ".claude", "projects")
    sessions = []

    for proj_dir in glob.glob(f"{base}/*/"):
        for jsonl_path in glob.glob(f"{proj_dir}*.jsonl"):
            s = parse_session(jsonl_path)
            if s:
                sessions.append(s)

    sessions.sort(key=lambda x: x["mtime"], reverse=True)

    # Filter by search term
    if search:
        sessions = [
            s for s in sessions
            if search in (s["first_msg"] or "").lower()
            or search in (s["name"] or "").lower()
            or search in s["dir"].lower()
            or search in s["id"].lower()
        ]

    # Colors
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    WHITE = "\033[37;1m"
    RESET = "\033[0m"

    show_count = len(sessions) if count == 0 else min(count, len(sessions))
    total = len(sessions)

    print(f"\n{BOLD}Claude Code Sessions{RESET} (showing {show_count} of {total})")
    if search:
        print(f"  Search: {YELLOW}{search}{RESET}")
    print()
    print(f"{'#':<4} {'Date':<18} {'Name':<30} {'Directory':<40} {'Size':>6}")
    print("\u2500" * 104)

    display = sessions if count == 0 else sessions[:count]
    for i, s in enumerate(display, 1):
        short_dir = s["dir"]
        if short_dir.startswith(home + "/"):
            short_dir = "~/" + short_dir[len(home) + 1:]
        elif short_dir == home:
            short_dir = "~"

        name = s["name"] or "unnamed"
        name_color = WHITE if s["name"] else DIM
        size_str = f"{s['size']:.0f}KB"

        print(
            f"{CYAN}{i:<4}{RESET} "
            f"{GREEN}{s['date']:<18}{RESET} "
            f"{name_color}{name[:29]:<30}{RESET} "
            f"{short_dir[:39]:<40} "
            f"{DIM}{size_str:>6}{RESET}"
        )
        # Preview of first message
        if s["first_msg"] and s["first_msg"] != "(empty session)":
            preview = s["first_msg"][:80]
            print(f"     {DIM}{preview}{RESET}")
        print(f"     {YELLOW}claude --resume {s['id']}{RESET}")
        print()


if __name__ == "__main__":
    main()
