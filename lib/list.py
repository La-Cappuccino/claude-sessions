#!/usr/bin/env python3
"""List and search Claude Code sessions with correct path resolution."""

import os
import sys
import glob

# Shared JSONL session parsing (see lib/parser.py).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parser import parse_session_meta, get_session_start, is_paperclip_session  # noqa: E402,F401


def parse_session(jsonl_path):
    """Thin adapter over parse_session_meta() that produces the dict shape
    this command's main() expects."""
    meta = parse_session_meta(jsonl_path, first_msg_len=120)
    if meta is None:
        return None

    session_start = meta["session_start"]
    last_activity = meta["last_activity"]

    return {
        "id": meta["id"],
        "dir": meta["cwd"] or "(unknown)",
        "name": meta["session_name"],
        "first_msg": meta["first_message"] or "(empty session)",
        "date": last_activity.strftime("%Y-%m-%d %H:%M"),
        "session_start": session_start,
        "last_activity": last_activity,
        "mtime": last_activity.timestamp(),
        "size": meta["size_kb"],
        "user_msg_count": meta["user_msg_count"],
        "is_paperclip": is_paperclip_session(meta),
    }


def main():
    count = 20
    search = ""

    args = sys.argv[1:]
    show_all = "--all" in args
    args = [a for a in args if a != "--all"]

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

    for jsonl_path in glob.glob(f"{base}/**/*.jsonl", recursive=True):
        s = parse_session(jsonl_path)
        if s:
            sessions.append(s)

    # Sort by last_activity (file mtime, now reliable after repairing
    # name-command pollution). This is "what did I last touch?" — the
    # question the user is actually asking when scanning the list.
    # session_start (creation time) is shown as a dim suffix when it
    # differs meaningfully from last_activity.
    sessions.sort(key=lambda x: x["last_activity"], reverse=True)

    # Filter out Paperclip agent sub-sessions by default. After recursive glob,
    # agent heartbeats can swamp daily views — hide unless --all.
    hidden_paperclip = 0
    if not show_all:
        before = len(sessions)
        sessions = [s for s in sessions if not s.get("is_paperclip")]
        hidden_paperclip = before - len(sessions)

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
    print("─" * 104)

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

        # Show original-start annotation when last_activity and session_start
        # differ by more than 1 day — reveals resumed-after-long-gap sessions.
        last_active_suffix = ""
        delta = s["last_activity"] - s["session_start"]
        if delta.total_seconds() > 86400:
            last_active_suffix = (
                f" {DIM}(started {s['session_start'].strftime('%Y-%m-%d')}){RESET}"
            )

        print(
            f"{CYAN}{i:<4}{RESET} "
            f"{GREEN}{s['date']:<18}{RESET} "
            f"{name_color}{name[:29]:<30}{RESET} "
            f"{short_dir[:39]:<40} "
            f"{DIM}{size_str:>6}{RESET}"
            f"{last_active_suffix}"
        )
        # Preview of first message
        if s["first_msg"] and s["first_msg"] != "(empty session)":
            preview = s["first_msg"][:80]
            print(f"     {DIM}{preview}{RESET}")
        print(f"     {YELLOW}claude --resume {s['id']}{RESET}")
        print()

    if hidden_paperclip and not show_all:
        print(f"{DIM}(hiding {hidden_paperclip} Paperclip agent sessions — use --all to show){RESET}")
        print()


if __name__ == "__main__":
    main()
