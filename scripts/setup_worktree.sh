#!/usr/bin/env bash
# Prepare a git worktree for development by linking the main checkout's Python venv and node_modules
# (no workstream adds dependencies, so all worktrees can share them).
# Usage, from inside a worktree:  scripts/setup_worktree.sh /path/to/main/checkout
set -euo pipefail
MAIN="${1:?usage: scripts/setup_worktree.sh /path/to/main/checkout}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"

[ -d "$MAIN/backend/.venv" ] || { echo "No venv at $MAIN/backend/.venv"; exit 1; }
[ -d "$MAIN/frontend/node_modules" ] || { echo "No node_modules at $MAIN/frontend/node_modules"; exit 1; }
[ -e "$HERE/backend/.venv" ] || ln -s "$MAIN/backend/.venv" "$HERE/backend/.venv"
[ -e "$HERE/frontend/node_modules" ] || ln -s "$MAIN/frontend/node_modules" "$HERE/frontend/node_modules"
echo "Linked venv and node_modules from $MAIN"
