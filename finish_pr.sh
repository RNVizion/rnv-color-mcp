#!/bin/bash
# finish_pr.sh  -  push the committed branch with your REAL login token, then open the PR.
#     bash finish_pr.sh
set -e

cd "$HOME/awesome-mcp-servers" 2>/dev/null || {
  echo "Can't find ~/awesome-mcp-servers. Re-run: bash open_pr.sh"; exit 1; }

# CRITICAL: drop the limited Codespace token so gh + git use your gh login instead.
unset GITHUB_TOKEN GH_TOKEN

echo "Which account/token gh is using now:"
gh auth status 2>&1 | grep -iE "Logged in|Token scopes" || true
echo ""

TOKEN=$(gh auth token)
if [ -z "$TOKEN" ]; then
  echo "gh has no stored token. Run this, then re-run finish_pr.sh:"
  echo "    unset GITHUB_TOKEN GH_TOKEN && gh auth login -h github.com -p https -s repo -w"
  exit 1
fi

echo "Pushing branch to your fork ..."
git push "https://x-access-token:${TOKEN}@github.com/RNVizion/awesome-mcp-servers.git" add-rnv-color-mcp --force

echo "Opening the pull request ..."
gh pr create --repo punkpeye/awesome-mcp-servers \
  --head "RNVizion:add-rnv-color-mcp" \
  --title "Add RNVizion/rnv-color-mcp (Architecture & Design)" \
  --body "Adds **rnv-color-mcp**, a hosted color-workflow MCP server (Python, Streamable HTTP).

Tools: mix (including Kubelka-Munk paint physics), convert between formats, generate harmonies, transform text case, and save/list/get named palettes. It resolves hex / CSS / custom brand color names and refuses unknown colors rather than guessing.

Published to the official MCP registry as \`io.github.RNVizion/rnv-color-mcp\`. Placed alphabetically under Architecture & Design, following the existing format and legend (🐍 ☁️)."
echo ""
echo "Done. The PR URL is printed above."
