#!/usr/bin/env python3
"""Fuzzy session picker using fzf for quick resume."""

import json
import os
import sys
import glob
import subprocess
import shutil
from datetime import datetime


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


def get_sessions():
    """Get all sessions sorted by most recent."""
    home = os.path.expanduser("~")
    base = os.path.join(home, ".claude", "projects")
    sessions = []

    for proj_dir in glob.glob(f"{base}/*/"):
        for jsonl_path in glob.glob(f"{proj_dir}*.jsonl"):
            session_id = os.path.basename(jsonl_path).replace(".jsonl", "")
            session_name = None
            first_msg = None
            cwd = None

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
                            if data.get("type") == "user" and not first_msg:
                                msg = data.get("message", {})
                                if msg.get("role") == "user":
                                    content = msg.get("content", "")
                                    if isinstance(content, str) and content.strip():
                                        first_msg = content[:80].replace("\n", " ").strip()
                                    elif isinstance(content, list):
                                        for c in content:
                                            if isinstance(c, dict) and c.get("type") == "text":
                                                first_msg = c["text"][:80].replace("\n", " ").strip()
                                                break
                        except (json.JSONDecodeError, KeyError):
                            continue
            except Exception:
                continue

            session_start = get_session_start(jsonl_path)

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
