# Changelog

## [1.1.0] - 2026-03-22

### Fixed
- **Naming: complete rewrite** — Old naming grabbed random verbs + tech keywords ("Fix Next.js Auth"). New naming uses project directory prefix + user's actual words ("Allegro: URGENT Fix Font & Contrast Issues")
- **Naming: preserves manual names** — Sessions you named yourself (`custom-title` entries) are never touched
- **Naming: noise filtering** — Strips system tags (`<local-command-caveat>`, `<command-message>`), UUIDs, audit headers, greetings, and other noise before generating names
- **Naming: fallback chain** — If first message is just "hei" or "hi", tries the second message instead

### Added
- Project alias mapping for well-known directories (rnb-vault → "R&B Vault", afrobeats-next → "Afrobeats", etc.)
- Comparison table in README now includes claude-history (Rust tool)

## [1.0.0] - 2026-03-21

### Added
- **6 commands**: `list`, `name`, `clean`, `stats`, `pick`, `export`
- **Path bug fix**: Reads `cwd` from JSONL data instead of decoding folder name (fixes `rnb-vault` → `rnb/vault` bug)
- **Cost tracking**: Parses token usage from session data, estimates costs per Opus/Sonnet/Haiku pricing with cache discounts
- **Auto-naming**: Generates session names from content analysis
- **Empty cleanup**: Identifies and deletes sessions with zero user messages
- **fzf integration**: Fuzzy search + instant `claude --resume`
- **JSON export**: Full session index with tokens and cost estimates
- **Install script**: Creates `sessions` symlink in `~/.local/bin/`

## [0.1.0] - 2026-03-21

### Added
- Initial single-file session browser (`sessions.sh`)
- Basic listing with search and colored output
