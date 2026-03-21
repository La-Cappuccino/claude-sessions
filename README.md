# claude-sessions

Zero-dependency Claude Code session browser. One bash script, ~100 lines.

![demo](https://img.shields.io/badge/sessions-132_found-blue)
![deps](https://img.shields.io/badge/dependencies-0-green)
![size](https://img.shields.io/badge/size-3KB-lightgrey)

## The Problem

Your terminal crashed. You were deep in a Claude Code session. You have no idea which directory you started it in. `claude --resume` needs a session ID you don't have.

## The Solution

```bash
sessions          # show last 20 sessions
sessions 50       # show last 50 sessions  
sessions 0 music  # search ALL sessions for "music"
sessions 0 allegro # find all allegro project sessions
```

Output:
```
Claude Code Sessions (showing 5 of 132)

#    Date               Name                           Directory                           Size
──────────────────────────────────────────────────────────────────────────────────────────────────
1    2026-03-21 09:35   Session Manager                ~                                   45KB
     claude --resume bcbc5e66-1234-5678-9abc-def012345678

2    2026-03-21 08:12   Allegro Dark Mode              ~/Projects/active/allegro-contracts 128KB
     claude --resume 4f99809d-07de-415e-90ef-b1fb3659b677

3    2026-03-20 22:45   R&B Vault GDPR                 ~/Projects/active/rnb-vault         67KB
     claude --resume a1b2c3d4-5678-90ab-cdef-ghijklmnopqr
```

Just copy-paste the `claude --resume <id>` command to jump back in.

## Install

### Quick (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/La-Cappuccino/claude-sessions/main/sessions.sh \
  -o ~/.local/bin/sessions && chmod +x ~/.local/bin/sessions
```

### Manual

```bash
# Download
curl -O https://raw.githubusercontent.com/La-Cappuccino/claude-sessions/main/sessions.sh
chmod +x sessions.sh

# Option A: Add alias
echo 'alias sessions="bash ~/path/to/sessions.sh"' >> ~/.zshrc

# Option B: Move to PATH
mv sessions.sh ~/.local/bin/sessions
```

## Why not CCManager / AgentsView?

Those are great tools! Use them if you want:
- **CCManager**: TUI for managing multiple *active* sessions in parallel
- **AgentsView**: Desktop app with analytics dashboard, full-text search, heatmaps

**claude-sessions** is for when you just need to:
- Find a lost session after a crash
- Browse recent sessions quickly
- Search by project/keyword
- Zero setup, zero dependencies, works offline

| Tool | Install | Size | Database | Use Case |
|------|---------|------|----------|----------|
| claude-sessions | curl one file | 3KB | None | Quick session recovery |
| CCManager | npm install | ~2MB | None | Multi-session workflows |
| AgentsView | Desktop app | ~50MB | SQLite | Team analytics |

## Requirements

- Bash
- Python 3 (standard library only)
- Claude Code sessions in `~/.claude/projects/`

## How It Works

Claude Code stores sessions as JSONL files in `~/.claude/projects/<project-path>/<session-id>.jsonl`.

This script:
1. Scans all session files
2. Extracts session name (if set), first message, timestamp
3. Sorts by most recent
4. Pretty-prints with resume commands

That's it. No database, no server, no npm.

## Tips

### Name your sessions

In Claude Code, use `/name My Session Name` to set a session name. This script will display it.

### Add to shell config

```bash
# ~/.zshrc or ~/.bashrc
alias sessions="bash ~/.local/bin/sessions"
```

## License

MIT
