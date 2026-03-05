#!/usr/bin/env bash
# AI Test Agent - One-time Unix / Git Bash setup
# Run once from the project root: bash ai_agent/setup_hook.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo ""
echo "[AI Test Agent Setup]"
echo "====================="
echo "Project root: $PROJECT_ROOT"

# ── Verify git repo ──────────────────────────────────────────────────────────
if [[ ! -d "$PROJECT_ROOT/.git" ]]; then
    echo "[ERROR] Not a git repository: $PROJECT_ROOT"
    exit 1
fi

# ── Install the hook ─────────────────────────────────────────────────────────
HOOK_SRC="$SCRIPT_DIR/hooks/pre-push"
HOOK_DST="$PROJECT_ROOT/.git/hooks/pre-push"

if [[ ! -f "$HOOK_SRC" ]]; then
    echo "[ERROR] Hook source not found: $HOOK_SRC"
    exit 1
fi

cp "$HOOK_SRC" "$HOOK_DST"
chmod +x "$HOOK_DST"
echo "[OK] Hook installed: .git/hooks/pre-push"

# ── Install Python dependencies ───────────────────────────────────────────────
echo ""
echo "[Setup] Installing Python dependencies..."

if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "[WARN] Python not found in PATH. Install Python 3.8+ and re-run this script."
    PYTHON=""
fi

if [[ -n "$PYTHON" ]]; then
    "$PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt" --quiet && \
        echo "[OK] Python dependencies installed." || \
        echo "[WARN] pip install had issues. Check: pip install -r ai_agent/requirements.txt"
fi

# ── Create .env if it doesn't exist ──────────────────────────────────────────
echo ""
if [[ ! -f "$SCRIPT_DIR/.env" ]]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo "[OK] Created ai_agent/.env from template."
    echo ""
    echo ">>> ACTION REQUIRED: Edit ai_agent/.env and set your ANTHROPIC_API_KEY <<<"
else
    echo "[OK] ai_agent/.env already exists."
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "====================="
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit ai_agent/.env and set ANTHROPIC_API_KEY=sk-ant-..."
echo "  2. Make changes on a branch and run: git push"
echo "  3. The agent runs automatically and saves reports to ai_agent/reports/"
echo ""
