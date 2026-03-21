# claude-sessions

Multi-command CLI for browsing, searching, naming, cleaning, and analyzing Claude Code sessions. Zero dependencies beyond Python 3 standard library.

![demo](https://img.shields.io/badge/sessions-132_found-blue)
![deps](https://img.shields.io/badge/dependencies-0-green)
![python](https://img.shields.io/badge/python-3.8+-blue)

## The Problem

Your terminal crashed. You were deep in a Claude Code session. You have no idea which directory you started it in. `claude --resume` needs a session ID you don't have.

Also: you have 130+ sessions, half are unnamed, a third are empty, and you have no idea how much you've spent.

## Install

### Quick (recommended)

```bash
git clone https://github.com/La-Cappuccino/claude-sessions.git
cd claude-sessions
bash install.sh
```

This creates a `sessions` command in `~/.local/bin/`. Make sure that's in your PATH.

### Manual

```bash
git clone https://github.com/La-Cappuccino/claude-sessions.git
# Add alias to your shell config:
echo 'alias sessions="bash ~/path/to/claude-sessions/sessions.sh"' >> ~/.zshrc
```

## Commands

### `sessions` / `sessions list` — Browse sessions

```bash
sessions              # last 20 sessions
sessions 50           # last 50 sessions
sessions 0            # ALL sessions
sessions 0 music      # search all sessions for "music"
sessions ls vault     # search last 20 for "vault"
```

Shows session name, working directory (read from actual JSONL data, not folder name), first message preview, size, and a copy-pasteable `claude --resume` command.

### `sessions stats` — Token usage and cost

```bash
sessions stats        # all time
sessions stats 7      # last 7 days
sessions stats 30     # last 30 days
```

Shows total tokens, cost estimates (Opus/Sonnet/Haiku pricing with cache discounts), model breakdown, and top projects by spend.

### `sessions name` — Auto-name unnamed sessions

```bash
sessions name              # dry run — show what would be named
sessions name --force      # write names to session files
```

Analyzes first 3 user messages to generate descriptive names using keyword extraction (verbs like fix/build/deploy, tech terms, file paths).

### `sessions clean` — Delete empty sessions

```bash
sessions clean              # dry run — show empty sessions
sessions clean --force      # delete them
sessions clean --tiny       # also show single-message sessions
```

Finds sessions with zero user messages (only system/hook entries).

### `sessions pick` — Fuzzy resume with fzf

```bash
sessions pick
```

Pipes all sessions through `fzf` for fuzzy search. Select one to immediately `claude --resume` into it. Requires [fzf](https://github.com/junegunn/fzf).

### `sessions export` — JSON export

```bash
sessions export                         # JSON to stdout
sessions export --output sessions.json  # JSON to file
```

Exports every session with: id, name, cwd, first_message, date, model, token counts, and cost estimate.

## How It Works

Claude Code stores sessions as JSONL files in `~/.claude/projects/<encoded-path>/<session-id>.jsonl`.

Previous tools decoded the folder name to reconstruct the working directory, which breaks on paths with hyphens (e.g., `rnb-vault` becomes `rnb/vault`). This tool reads the `cwd` field directly from JSONL entries, giving the correct path every time.

## Structure

```
claude-sessions/
├── sessions.sh          # Bash dispatcher
├── lib/
│   ├── list.py          # List/search sessions
│   ├── name.py          # Auto-name unnamed sessions
│   ├── clean.py         # Delete empty sessions
│   ├── stats.py         # Token/cost statistics
│   ├── pick.py          # fzf fuzzy picker
│   └── export.py        # JSON export
├── install.sh           # Symlink installer
└── README.md
```

## vs. Other Tools

| Feature | claude-sessions | CCManager | AgentsView |
|---------|----------------|-----------|------------|
| Install | `git clone` | `npm install` | Desktop app |
| Size | ~15KB | ~2MB | ~50MB |
| Dependencies | Python 3 stdlib | Node.js | Electron |
| Session list | Yes | Yes | Yes |
| Search | Yes | No | Yes (full-text) |
| Auto-naming | Yes | No | No |
| Cost tracking | Yes | No | Yes |
| Empty cleanup | Yes | No | No |
| fzf integration | Yes | No | No |
| JSON export | Yes | No | Yes |
| Path accuracy | JSONL `cwd` field | Folder decode | Database |
| Offline | Yes | Yes | Yes |

## Requirements

- Bash
- Python 3.8+ (standard library only)
- Claude Code sessions in `~/.claude/projects/`
- Optional: [fzf](https://github.com/junegunn/fzf) for `sessions pick`

## License

MIT
