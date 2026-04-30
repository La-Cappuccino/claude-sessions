#!/usr/bin/env python3
"""Resume the most recently-active Claude Code session across ALL directories.

Claude Code's official `claude --continue` only resumes the most recent session
in the *current* directory, and `claude --resume` opens a cwd-scoped picker
(Ctrl+A widens to global). There's no built-in "resume my actual most recent
session anywhere" command. This fills that gap.

Selection rule: highest `last_activity` (file mtime, reliable since name.py
preserves it) across ~/.claude/projects/**/*.jsonl, excluding Paperclip agent
sub-sessions by default.

Output: prints the `claude --resume <id>` command. With --exec, runs it.
"""

import os
import sys
import glob
import shutil
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parser import parse_session_meta, is_paperclip_session  # noqa: E402


def main():
    args = sys.argv[1:]
    show_all = "--all" in args
    exec_it = "--exec" in args or "-x" in args
    print_only = "--print" in args or "-p" in args

    home = os.path.expanduser("~")
    base = os.path.join(home, ".claude", "projects")

    best = None  # (last_activity_ts, meta)
    for jsonl_path in glob.glob(f"{base}/**/*.jsonl", recursive=True):
        meta = parse_session_meta(jsonl_path, first_msg_len=80)
        if meta is None:
            continue
        if not show_all and is_paperclip_session(meta):
            continue
        if (meta.get("user_msg_count") or 0) == 0:
            continue  # skip empty placeholders
        ts = meta["last_activity"].timestamp()
        if best is None or ts > best[0]:
            best = (ts, meta)

    if best is None:
        print("No resumable sessions found.", file=sys.stderr)
        sys.exit(1)

    _, m = best
    sid = m["id"]
    cwd = m["cwd"] or "(unknown)"
    name = m["session_name"] or m["first_message"] or "(empty)"
    when = m["last_activity"].strftime("%Y-%m-%d %H:%M")

    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    RESET = "\033[0m"

    short_dir = cwd
    if short_dir.startswith(home + "/"):
        short_dir = "~/" + short_dir[len(home) + 1:]
    elif short_dir == home:
        short_dir = "~"

    print(f"{BOLD}Most recent session:{RESET}")
    print(f"  {GREEN}{when}{RESET}  {CYAN}{name[:60]}{RESET}")
    print(f"  {DIM}cwd:{RESET} {short_dir}")
    print(f"  {DIM}id: {RESET} {sid}")
    print()

    cmd = ["claude", "--resume", sid]

    if print_only or (not exec_it and not shutil.which("claude")):
        print(f"{YELLOW}{' '.join(cmd)}{RESET}")
        return

    if not exec_it:
        # Default: print the command, don't run it. User can pipe into shell or
        # add --exec when they want one-keystroke resume.
        print(f"{YELLOW}{' '.join(cmd)}{RESET}")
        print(f"{DIM}Run with --exec to resume immediately.{RESET}")
        return

    # cd into the original cwd so `claude --resume` lands in the right place
    if cwd and os.path.isdir(cwd):
        os.chdir(cwd)
    os.execvp("claude", cmd)


if __name__ == "__main__":
    main()
