#!/bin/bash
# Claude Code Session Browser
# https://github.com/La-Cappuccino/claude-sessions
#
# Usage: sessions [count] [search]
# Examples:
#   sessions          → show last 20 sessions
#   sessions 50       → show last 50 sessions
#   sessions 50 music → show last 50 sessions matching "music"
#   sessions 0        → show ALL sessions

COUNT="${1:-20}"
SEARCH="${2:-}"

python3 - "$COUNT" "$SEARCH" << 'PYEOF'
import json, os, glob, sys
from datetime import datetime

count = int(sys.argv[1]) if len(sys.argv) > 1 else 20
search = sys.argv[2].lower() if len(sys.argv) > 2 else ""

sessions = []
base = os.path.expanduser("~/.claude/projects")
home = os.path.expanduser("~")

for proj_dir in glob.glob(f"{base}/*/"):
    proj_name = os.path.basename(proj_dir.rstrip("/"))
    cwd = "/" + proj_name.lstrip("-").replace("-", "/")

    for jsonl_path in glob.glob(f"{proj_dir}*.jsonl"):
        session_id = os.path.basename(jsonl_path).replace(".jsonl", "")
        session_name = None
        first_msg = None

        try:
            with open(jsonl_path, "r") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if data.get("type") == "custom-title":
                            session_name = data.get("customTitle")
                        if data.get("type") == "summary":
                            t = data.get("summary", {}).get("title")
                            if t and not session_name:
                                session_name = t
                        if data.get("type") == "user" and data.get("message", {}).get("role") == "user":
                            if not first_msg:
                                content = data["message"].get("content", "")
                                if isinstance(content, str):
                                    first_msg = content[:100].replace("\n", " ")
                                elif isinstance(content, list):
                                    for c in content:
                                        if isinstance(c, dict) and c.get("type") == "text":
                                            first_msg = c["text"][:100].replace("\n", " ")
                                            break
                    except (json.JSONDecodeError, KeyError):
                        continue
        except Exception:
            continue

        mtime = os.path.getmtime(jsonl_path)
        dt = datetime.fromtimestamp(mtime)
        size_kb = os.path.getsize(jsonl_path) / 1024

        sessions.append({
            "id": session_id,
            "dir": cwd,
            "name": session_name,
            "first_msg": first_msg or "(empty session)",
            "date": dt.strftime("%Y-%m-%d %H:%M"),
            "mtime": mtime,
            "size": size_kb,
        })

sessions.sort(key=lambda x: x["mtime"], reverse=True)

# Filter by search term
if search:
    sessions = [s for s in sessions if
        search in (s["first_msg"] or "").lower() or
        search in (s["name"] or "").lower() or
        search in s["dir"].lower() or
        search in s["id"].lower()]

# Pretty print
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
WHITE = "\033[37;1m"
RESET = "\033[0m"

show_count = len(sessions) if count == 0 else min(count, len(sessions))
print(f"\n{BOLD}Claude Code Sessions{RESET} (showing {show_count} of {len(sessions)})\n")
print(f"{'#':<4} {'Date':<18} {'Name':<30} {'Directory':<35} {'Size':>6}")
print("─" * 98)

display = sessions if count == 0 else sessions[:count]
for i, s in enumerate(display, 1):
    short_dir = s["dir"]
    if short_dir.startswith(home + "/"):
        short_dir = "~/" + short_dir[len(home)+1:]
    elif short_dir == home:
        short_dir = "~"

    name = s["name"] or "unnamed"
    name_color = WHITE if s["name"] else DIM
    size_str = f"{s['size']:.0f}KB"

    print(f"{CYAN}{i:<4}{RESET} {GREEN}{s['date']:<18}{RESET} {name_color}{name[:29]:<30}{RESET} {short_dir[:34]:<35} {DIM}{size_str:>6}{RESET}")
    print(f"     {YELLOW}claude --resume {s['id']}{RESET}")
    print()

PYEOF
