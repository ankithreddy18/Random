#!/bin/bash
set -euo pipefail

# Only run in remote (Claude Code on the web) environments
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

echo "=== Session Start: Installing global tools ==="

# npm global packages
echo "[1/5] Installing npm globals (repomix, @aoagents/ao)..."
npm install -g repomix @aoagents/ao 2>&1 | tail -3 || true

# superclaude via pip (installs 30 slash commands)
echo "[2/5] Installing superclaude..."
pip install --quiet --upgrade superclaude 2>/dev/null || true
superclaude install --yes 2>/dev/null || true

# tradingview-mcp: no pre-install needed — uvx fetches it on demand at MCP server startup
echo "[3/5] tradingview-mcp configured (uvx on-demand via settings.json)..."

# claude-mem
echo "[4/5] Installing claude-mem..."
npx --yes claude-mem install 2>/dev/null || true

# Plugin marketplace skill packs
echo "[5/5] Adding plugin marketplace skills..."
claude plugin marketplace add trailofbits/skills 2>/dev/null || true
claude plugin marketplace add anthropics/skills 2>/dev/null || true

echo "=== Session Start: Setup complete ==="
