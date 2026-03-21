#!/bin/bash
# Install claude-sessions CLI
# Usage: bash install.sh [install-dir]

set -euo pipefail

INSTALL_DIR="${1:-$HOME/.local/bin}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$INSTALL_DIR"

# Create wrapper script that points to the repo
cat > "$INSTALL_DIR/sessions" << EOF
#!/bin/bash
exec bash "$SCRIPT_DIR/sessions.sh" "\$@"
EOF
chmod +x "$INSTALL_DIR/sessions"

echo "Installed: sessions -> $SCRIPT_DIR/sessions.sh"
echo ""
echo "Make sure $INSTALL_DIR is in your PATH:"
echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
