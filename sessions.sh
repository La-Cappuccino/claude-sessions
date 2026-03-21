#!/bin/bash
# Claude Code Session Manager
# https://github.com/La-Cappuccino/claude-sessions
#
# Usage: sessions [command] [args]
# Commands:
#   list|ls [count] [search]  — List sessions (default: last 20)
#   name [--force]            — Auto-name unnamed sessions
#   clean [--force] [--tiny]  — Delete empty sessions
#   stats [days]              — Token/cost statistics
#   pick                      — Fuzzy picker (requires fzf)
#   export [--output file]    — Export session index as JSON
#   help|-h                   — Show this help

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CMD="${1:-list}"
shift 2>/dev/null || true

case "$CMD" in
  list|ls)
    python3 "$SCRIPT_DIR/lib/list.py" "$@"
    ;;
  name)
    python3 "$SCRIPT_DIR/lib/name.py" "$@"
    ;;
  clean)
    python3 "$SCRIPT_DIR/lib/clean.py" "$@"
    ;;
  stats)
    python3 "$SCRIPT_DIR/lib/stats.py" "$@"
    ;;
  pick)
    python3 "$SCRIPT_DIR/lib/pick.py" "$@"
    ;;
  export)
    python3 "$SCRIPT_DIR/lib/export.py" "$@"
    ;;
  help|-h|--help)
    echo ""
    echo "  Claude Code Session Manager"
    echo ""
    echo "  Usage: sessions [command] [args]"
    echo ""
    echo "  Commands:"
    echo "    list|ls [count] [search]  List sessions (default: last 20)"
    echo "    name [--force]            Auto-name unnamed sessions"
    echo "    clean [--force] [--tiny]  Delete empty sessions"
    echo "    stats [days]              Token/cost statistics"
    echo "    pick                      Fuzzy picker (requires fzf)"
    echo "    export [--output file]    Export session index as JSON"
    echo "    help                      Show this help"
    echo ""
    echo "  Examples:"
    echo "    sessions                  Show last 20 sessions"
    echo "    sessions 50               Show last 50 sessions"
    echo "    sessions 0 music          Search all sessions for 'music'"
    echo "    sessions stats 7          Cost stats for last 7 days"
    echo "    sessions clean            Show empty sessions (dry run)"
    echo "    sessions clean --force    Delete empty sessions"
    echo "    sessions name --force     Auto-name all unnamed sessions"
    echo "    sessions pick             Fuzzy search + resume"
    echo "    sessions export           JSON to stdout"
    echo ""
    ;;
  *)
    # Default: treat as count arg for list (e.g., `sessions 50`)
    python3 "$SCRIPT_DIR/lib/list.py" "$CMD" "$@"
    ;;
esac
