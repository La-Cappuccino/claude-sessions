# claude-sessions

Multi-command CLI for browsing, searching, naming, cleaning, and analyzing Claude Code sessions. Zero dependencies beyond Python 3 standard library.

![version](https://img.shields.io/badge/version-1.1.0-blue)
![deps](https://img.shields.io/badge/dependencies-0-green)
![python](https://img.shields.io/badge/python-3.8+-blue)
![license](https://img.shields.io/badge/license-MIT-lightgrey)

## The Problem

Your terminal crashed. You were deep in a Claude Code session. You have no idea which directory you started it in. `claude --resume` needs a session ID you don't have.

Also: you have 100+ sessions, half are unnamed, a third are empty, and you have no idea how much you've spent.

## Install

### Quick (recommended)

```bash
git clone https://github.com/La-Cappuccino/claude-sessions.git
cd claude-sessions
bash install.sh
```

This creates a `sessions` symlink in `~/.local/bin/`. Make sure that's in your PATH.

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

Shows session name, working directory, first message preview, size, and a copy-pasteable `claude --resume` command.

**Path accuracy:** Reads the `cwd` field directly from JSONL data, not the encoded folder name. This means `rnb-vault` stays `rnb-vault` (not broken into `rnb/vault`).

### `sessions stats` — Token usage and cost estimates

```bash
sessions stats        # all time
sessions stats 7      # last 7 days
sessions stats 30     # last 30 days
```

Shows total tokens, estimated costs (Opus $15/$75, Sonnet $3/$15, Haiku $0.25/$1.25 per million tokens, with cache discounts), model usage breakdown, and top projects by spend.

### `sessions name` — Auto-name unnamed sessions

```bash
sessions name              # dry run — preview names
sessions name --force      # write names to session files
```

Generates descriptive names using:
- **Project prefix** from the working directory (e.g., "Allegro:", "Afrobeats:", "R&B Vault:")
- **User's actual first message** — not random keyword extraction
- **Noise filtering** — strips system tags, command artifacts, UUIDs, greetings
- **Fallback chain** — if first message is just "hei", tries second message

Sessions you've already named manually are **never overwritten**.

### `sessions clean` — Delete empty sessions

```bash
sessions clean              # dry run — show empty sessions
sessions clean --force      # delete them
sessions clean --tiny       # also show single-message sessions
```

Finds sessions with zero user messages (crashed starts, aborted sessions, hook-only entries).

### `sessions pick` — Fuzzy resume with fzf

```bash
sessions pick
```

Pipes all sessions through [fzf](https://github.com/junegunn/fzf) for instant fuzzy search. Select one and it runs `claude --resume <id>` automatically.

### `sessions export` — JSON export

```bash
sessions export                         # JSON to stdout
sessions export --output sessions.json  # JSON to file
```

Exports every session with: id, name, cwd, first_message, date, model, user_messages count, token breakdown (input, output, cache_creation, cache_read), and cost estimate.

## How It Works

Claude Code stores sessions as JSONL files in `~/.claude/projects/<encoded-path>/<session-id>.jsonl`.

Other tools decode the folder name to guess the working directory, which breaks on hyphenated paths (e.g., `rnb-vault` becomes `rnb/vault`). This tool reads the `cwd` field directly from JSONL entries — always correct.

Session names are stored as `{"type":"custom-title","customTitle":"..."}` entries appended to the JSONL file. The `name` command reads these and skips any session that already has one, so your manual names are preserved.

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

| Feature | claude-sessions | CCManager | AgentsView | claude-history |
|---------|----------------|-----------|------------|----------------|
| Install | `git clone` | `npm install -g` | Desktop app | `brew install` |
| Size | ~20KB | ~2MB | ~50MB | ~5MB |
| Dependencies | Python 3 stdlib | Node.js | Go binary | Rust binary |
| Browse sessions | Yes | Yes | Yes | Yes |
| Search | Yes | Limited | Full-text (FTS5) | Fuzzy search |
| Auto-naming | **Yes** | No | No | No |
| Cost tracking | **Yes** | No | Tokens only | No |
| Empty cleanup | **Yes** | No | No | No |
| fzf picker | **Yes** | No | No | Yes |
| JSON export | **Yes** | No | Yes | No |
| Path accuracy | JSONL `cwd` | Folder decode | SQLite DB | JSONL parse |
| Offline | Yes | Yes | Yes | Yes |
| Multi-tool | Claude only | 8 tools | 12 tools | Claude only |

**Best for:** Quick session recovery, batch naming, cost awareness, cleanup. Use alongside AgentsView (visual dashboard) or CCManager (multi-session management) — they complement each other.

## Requirements

- Bash
- Python 3.8+ (standard library only)
- Claude Code sessions in `~/.claude/projects/`
- Optional: [fzf](https://github.com/junegunn/fzf) for `sessions pick`

## License

MIT
