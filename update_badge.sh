#!/bin/bash
# update_badge.sh  -  add the Glama score badge to the PR entry and push (updates PR #8681).
#     bash update_badge.sh
set -e

cd "$HOME/awesome-mcp-servers" 2>/dev/null || {
  echo "Can't find ~/awesome-mcp-servers. Re-run: bash open_pr.sh"; exit 1; }

unset GITHUB_TOKEN GH_TOKEN
git checkout add-rnv-color-mcp

echo "Inserting the Glama badge into your entry ..."
python3 - << 'PYEOF'
p = 'README.md'
t = open(p, encoding='utf-8').read()
badge = '[![RNVizion/rnv-color-mcp MCP server](https://glama.ai/mcp/servers/RNVizion/rnv-color-mcp/badges/score.svg)](https://glama.ai/mcp/servers/RNVizion/rnv-color-mcp)'
if 'glama.ai/mcp/servers/RNVizion/rnv-color-mcp/badges' in t:
    print('   badge already present; nothing to do'); raise SystemExit(0)
anchor = '](https://github.com/RNVizion/rnv-color-mcp) 🐍'
assert t.count(anchor) == 1, f"anchor count = {t.count(anchor)} (tell Claude)"
t = t.replace(anchor, f'](https://github.com/RNVizion/rnv-color-mcp) {badge} 🐍')
open(p, 'w', encoding='utf-8').write(t)
print('   badge inserted')
PYEOF

if git diff --quiet README.md; then
  echo "No change to push (badge was already there). PR is current."
  exit 0
fi

echo "Commit + push to the PR branch ..."
git add README.md
git commit -m "Add Glama score badge to rnv-color-mcp entry"
TOKEN=$(gh auth token)
git push "https://x-access-token:${TOKEN}@github.com/RNVizion/awesome-mcp-servers.git" add-rnv-color-mcp

echo ""
echo "Done. PR #8681 now shows the badge. The score image fills in once Glama finishes scoring."
