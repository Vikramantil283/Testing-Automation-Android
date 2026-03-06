#!/usr/bin/env bash
# AI Test Agent - Manual trigger (Git Bash / Unix)
# Run this when your task is done and you want tests generated.
# Usage: bash ai_agent/run_agent.sh [base-branch]
#   base-branch defaults to "main"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BASE="${1:-main}"
BRANCH="$(git -C "$PROJECT_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')"

if [[ -z "$BRANCH" ]]; then
    echo "[ERROR] Could not detect current branch."
    exit 1
fi

echo ""
echo "[AI Test Agent] Manual trigger"
echo "  Branch : $BRANCH"
echo "  Base   : $BASE"
echo "  Root   : $PROJECT_ROOT"
echo ""

# Add Ollama to PATH if on Windows
OLLAMA_DIR="/c/Users/$USERNAME/AppData/Local/Programs/Ollama"
[[ -d "$OLLAMA_DIR" ]] && export PATH="$OLLAMA_DIR:$PATH"

# Locate Python
PYTHON=""
for CANDIDATE in \
    "/c/Users/$USERNAME/AppData/Local/Programs/Python/Python312/python.exe" \
    "/c/Users/$USERNAME/AppData/Local/Programs/Python/Python311/python.exe" \
    "/c/Users/$USERNAME/AppData/Local/Programs/Python/Python310/python.exe" \
    "/c/Python312/python.exe"
do
    if [[ -f "$CANDIDATE" ]]; then
        PYTHON="$CANDIDATE"
        break
    fi
done
if [[ -z "$PYTHON" ]]; then
    command -v python3 &>/dev/null && PYTHON=python3
    command -v python  &>/dev/null && PYTHON=python
fi
if [[ -z "$PYTHON" ]]; then
    echo "[ERROR] Python not found. Install Python 3.8+."
    exit 1
fi

echo "[OK] Using Python: $PYTHON"
echo ""

"$PYTHON" "$SCRIPT_DIR/ai_test_agent.py" \
    --branch "$BRANCH" \
    --base   "$BASE" \
    --project-root "$PROJECT_ROOT"
