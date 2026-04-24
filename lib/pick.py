#!/usr/bin/env python3
"""Fuzzy session picker using fzf for quick resume."""

import os
import sys
import glob
import subprocess
import shutil

# Shared JSONL session parsing (see lib/parser.py).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parser import parse_session_meta, get_session_start  # noqa: E402,F401


def get_sessions():
    """Get all sessions sorted by session_start (most recent first)."""
    home = os.path.expanduser("~")
    base = os.path.join(home, ".claude", "projects")
    sessions = []

    for jsonl_path in glob.glob(f"{base}/**/*.jsonl", recursive=True):
        meta = parse_session_meta(jsonl_path, first_msg_len=80)
        if meta is None:
            continue

        session_id = meta["id"]
        cwd = meta["cwd"]
        session_name = meta["session_name"]
        first_msg = meta["first_message"]
        session_start = meta["session_start"]

        short_dir = cwd or "(unknown)"
        if short_dir.startswith(home + "/"):
            short_dir = "~/" + short_dir[len(home) + 1:]
        elif short_dir == home:
            short_dir = "~"

        name = session_name or first_msg or "(empty)"
        line = f"{session_start.strftime('%m-%d %H:%M')}  {name[:40]:<40}  {short_dir:<35}  {session_id}"

        sessions.append((session_start.timestamp(), line, session_id))

    sessions.sort(key=lambda x: -x[0])
    return sessions


def main():
    # Check for fzf
    if not shutil.which("fzf"):
        print("\033[31mError:\033[0m fzf is not installed.")
        print("  brew install fzf")
        sys.exit(1)

    sessions = get_sessions()
    if not sessions:
        print("No sessions found.")
        sys.exit(1)

    # Build fzf input
    fzf_input = "\n".join(s[1] for s in sessions)

    try:
        result = subprocess.run(
            [
                "fzf",
                "--ansi",
                "--no-multi",
                "--header=Select a session to resume (ESC to cancel)",
                "--prompt=Session> ",
                "--height=80%",
                "--reverse",
            ],
            input=fzf_input,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            sys.exit(0)  # User cancelled

        selected = result.stdout.strip()
        if not selected:
            sys.exit(0)

        # Extract session ID (last field)
        session_id = selected.split()[-1]

        # Exec into claude --resume
        print(f"\033[33mclaude --resume {session_id}\033[0m")
        os.execvp("claude", ["claude", "--resume", session_id])

    except FileNotFoundError:
        print("\033[31mError:\033[0m fzf not found in PATH.")
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
