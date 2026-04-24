#!/usr/bin/env python3
"""Shared JSONL session parsing.

Before this module, list.py/pick.py/export.py each duplicated slightly-divergent
parsing logic for cwd, custom-title, first user message, and user-message count.
That led to the same session producing inconsistent metadata across commands.
Consolidate here so there is one source of truth.

stats.py is intentionally NOT migrated — it parses for a different purpose
(per-entry usage aggregation with window filtering) and has no overlap worth
unifying.
"""

import json
import os
import sys
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
                except (json.JSONDecodeError, KeyError, AttributeError, TypeError):
                    continue
    except Exception:
        pass
    return datetime.fromtimestamp(os.path.getmtime(jsonl_path))


def iter_entries(jsonl_path):
    """Yield (line_num, dict) tuples for each parseable JSONL entry.

    Malformed lines are skipped silently; file-level errors are logged to
    stderr and terminate iteration."""
    try:
        with open(jsonl_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    yield line_num, json.loads(line)
                except (json.JSONDecodeError, KeyError, AttributeError, TypeError):
                    continue
    except Exception as e:
        print(
            f"  Warning: failed to parse {jsonl_path}: {type(e).__name__}: {e}",
            file=sys.stderr,
        )


def parse_session_meta(jsonl_path, first_msg_len=120):
    """Parse a session JSONL file for display metadata.

    Returns a dict with:
      id, cwd, session_name, first_message, session_start,
      last_activity, user_msg_count, size_kb
    or None if the file cannot be opened at all.

    session_name prefers custom-title; falls back to summary title.
    """
    session_id = os.path.basename(jsonl_path).replace(".jsonl", "")
    session_name = None
    first_msg = None
    cwd = None
    user_msg_count = 0

    saw_any = False
    for _, data in iter_entries(jsonl_path):
        saw_any = True
        try:
            # cwd: first entry that carries one
            if not cwd:
                c = data.get("cwd")
                if c and c.startswith("/"):
                    cwd = c

            # Session name: custom-title is authoritative
            if data.get("type") == "custom-title":
                session_name = data.get("customTitle")

            # Fallback to summary.title when no custom-title yet
            if data.get("type") == "summary":
                t = data.get("summary", {}).get("title")
                if t and not session_name:
                    session_name = t

            # First user message & user-message count
            if data.get("type") == "user":
                msg = data.get("message", {})
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        has_text = False
                        for c in content:
                            if isinstance(c, dict):
                                if c.get("type") == "tool_result":
                                    continue
                                if c.get("type") == "text":
                                    has_text = True
                                    if not first_msg:
                                        first_msg = (
                                            c["text"][:first_msg_len]
                                            .replace("\n", " ")
                                            .strip()
                                        )
                        if not has_text:
                            continue
                        user_msg_count += 1
                    elif isinstance(content, str) and content.strip():
                        if not first_msg:
                            first_msg = (
                                content[:first_msg_len].replace("\n", " ").strip()
                            )
                        user_msg_count += 1
        except (AttributeError, TypeError):
            # Malformed shape inside one entry — skip it, keep going.
            continue

    # If iter_entries couldn't even open the file, it already logged. Surface
    # None so callers can filter.
    try:
        mtime = os.path.getmtime(jsonl_path)
    except OSError:
        return None
    if not saw_any:
        # File was opened but yielded nothing (0 lines). Still return meta
        # with timestamps derived from mtime; callers can filter on
        # user_msg_count == 0 if desired.
        pass

    last_activity = datetime.fromtimestamp(mtime)
    session_start = get_session_start(jsonl_path)
    try:
        size_kb = os.path.getsize(jsonl_path) / 1024
    except OSError:
        size_kb = 0.0

    return {
        "id": session_id,
        "cwd": cwd,
        "session_name": session_name,
        "first_message": first_msg,
        "session_start": session_start,
        "last_activity": last_activity,
        "user_msg_count": user_msg_count,
        "size_kb": size_kb,
    }
