#!/bin/bash
# finish_pr.sh  -  push the already-committed branch with the correct token, then open the PR.
# Run after open_pr.sh stopped at the push step:
#     bash finish_pr.sh
set -e

cd "$HOME/awesome-mcp-servers" 2>/dev/null || {
  echo "Can't find ~/awesome-mcp-servers. Re-run: bash open_pr.sh"; exit 1; }

# Make git use the gh-authenticated token (not the limited Codespace token)
gh auth setup-git
TOKEN=$(gh auth token)

echo "Pushing branch to your fork ..."
git push "https://RNVizion:${TOKEN}@github.com/RNVizion/awesome-mcp-servers.git" add-rnv-color-mcp --force

echo "Opening the pull request ..."
gh pr create --repo punkpeye/awesome-mcp-servers \
  --head "RNVizion:add-rnv-color-mcp" \
  --title "Add RNVizion/rnv-color-mcp (Architecture & Design)" \
  --body "Adds **rnv-color-mcp**, a hosted color-workflow MCP server (Python, Streamable HTTP).

Tools: mix (including Kubelka-Munk paint physics), convert between formats, generate harmonies, transform text case, and save/list/get named palettes. It resolves hex / CSS / custom brand color names and refuses unknown colors rather than guessing.

Published to the official MCP registry as \`io.github.RNVizion/rnv-color-mcp\`. Placed alphabetically under Architecture & Design, following the existing format and legend (🐍 ☁️)."
echo ""
echo "Done. The PR URL is printed above."
