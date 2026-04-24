#!/usr/bin/env python3
"""Find and delete empty/dead Claude Code sessions."""

import json
import os
import sys
import glob
import shutil
import subprocess


def trash_file(path):
    """Move a file to the system trash. Falls back to os.remove on non-macOS
    systems without the `trash` CLI, so a recovery path exists everywhere.
    """
    if shutil.which("trash"):
        subprocess.run(["trash", path], check=True)
    elif sys.platform == "darwin":
        subprocess.run([
            "osascript", "-e",
            f'tell app "Finder" to delete POSIX file "{path}"'
        ], check=True, capture_output=True)
    else:
        print(f"  Warning: no trash tool available, falling back to os.remove for {path}")
        os.remove(path)


def count_user_messages(jsonl_path):
    """Count actual user messages (not tool results) in a session."""
    count = 0
    try:
        with open(jsonl_path, "r") as f:
            for line in f:
                if '"type":"user"' not in line and '"type": "user"' not in line:
                    continue
                try:
                    data = json.loads(line)
                    if data.get("type") == "user":
                        msg = data.get("message", {})
                        if msg.get("role") == "user":
                            content = msg.get("content", "")
                            if isinstance(content, str) and content.strip():
                                count += 1
                            elif isinstance(content, list):
                                for c in content:
                                    if isinstance(c, dict) and c.get("type") == "text":
                                        count += 1
                                        break
                except (json.JSONDecodeError, KeyError):
                    continue
    except Exception:
        pass
    return count


def main():
    force = "--force" in sys.argv
    include_tiny = "--tiny" in sys.argv  # Also clean sessions with only 1 message

    home = os.path.expanduser("~")
    base = os.path.join(home, ".claude", "projects")

    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    RESET = "\033[0m"

    empty = []
    total = 0
    total_size = 0

    threshold = 1 if include_tiny else 0

    for jsonl_path in glob.glob(f"{base}/**/*.jsonl", recursive=True):
        total += 1
        msg_count = count_user_messages(jsonl_path)
        if msg_count <= threshold:
            size_kb = os.path.getsize(jsonl_path) / 1024
            total_size += size_kb
            session_id = os.path.basename(jsonl_path).replace(".jsonl", "")
            empty.append({
                "path": jsonl_path,
                "id": session_id,
                "size": size_kb,
                "msgs": msg_count,
            })

    if not empty:
        print(f"\n{GREEN}No empty sessions found.{RESET} ({total} total sessions)")
        return

    print(f"\n{BOLD}Empty Session Cleanup{RESET}")
    print(f"  Total sessions: {total}")
    print(f"  Empty sessions: {RED}{len(empty)}{RESET}")
    print(f"  Space to free: {total_size:.0f} KB")
    print()

    # Show first 30
    for s in empty[:30]:
        print(f"  {CYAN}{s['id'][:12]}...{RESET}  {DIM}{s['size']:.0f}KB  {s['msgs']} msgs{RESET}")
    if len(empty) > 30:
        print(f"  {DIM}... and {len(empty) - 30} more{RESET}")
    print()

    if not force:
        flags = "--force"
        if include_tiny:
            flags += " --tiny"
        print(f"{YELLOW}Dry run.{RESET} Run with {BOLD}{flags}{RESET} to delete.")
        return

    deleted = 0
    for s in empty:
        try:
            trash_file(s["path"])
            deleted += 1
        except Exception as e:
            print(f"  Error trashing {s['id']}: {e}")

    print(f"{GREEN}Moved {deleted} empty sessions to trash.{RESET} Freed ~{total_size:.0f} KB.")


if __name__ == "__main__":
    main()
