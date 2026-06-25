#!/bin/bash
# open_pr.sh  -  add rnv-color-mcp to punkpeye/awesome-mcp-servers and open a PR.
# Run from anywhere in your Codespace:
#     bash open_pr.sh
# Uses the GitHub CLI (gh). If gh reports a permission problem forking or
# opening the PR, run:  gh auth login    (GitHub.com -> HTTPS -> login)  then re-run.
set -e

GHUSER=$(gh api user -q .login)
echo "Logged in as: $GHUSER"

cd "$HOME"
rm -rf awesome-mcp-servers

echo "1/5  Fork + clone ..."
gh repo fork punkpeye/awesome-mcp-servers --clone 2>/dev/null || true
[ -d awesome-mcp-servers ] || git clone "https://github.com/$GHUSER/awesome-mcp-servers.git"
cd awesome-mcp-servers

echo "2/5  Syncing fork to latest upstream ..."
git remote add upstream https://github.com/punkpeye/awesome-mcp-servers.git 2>/dev/null || true
git fetch upstream -q
git checkout -q main 2>/dev/null || git checkout -q master
git reset --hard upstream/HEAD -q 2>/dev/null || git reset --hard upstream/main -q

echo "3/5  Writing entry + inserting (alphabetical, Architecture & Design) ..."
cat > /tmp/rnv_entry.txt << 'ENTRYEOF'
- [RNVizion/rnv-color-mcp](https://github.com/RNVizion/rnv-color-mcp) 🐍 ☁️ - A complete color workflow over MCP: mix (incl. Kubelka-Munk paint physics), convert formats, generate harmonies, and remember named palettes. Resolves hex, CSS, and custom brand color names, and refuses unknown colors rather than guessing. Hosted, no install: `https://rnvizion-rnv-color-mcp.hf.space/mcp`.
ENTRYEOF
python3 - << 'PYEOF'
entry = open('/tmp/rnv_entry.txt', encoding='utf-8').read().rstrip('\n')
p = 'README.md'
lines = open(p, encoding='utf-8').read().split('\n')
if any('RNVizion/rnv-color-mcp' in l for l in lines):
    print('   already present; nothing to insert'); raise SystemExit(0)
idx = [i for i, l in enumerate(lines) if 'rdanieli/tentra-mcp' in l]
assert len(idx) == 1, f"anchor not found/unique: {idx} (upstream may have changed; tell Claude)"
lines.insert(idx[0] + 1, entry)
open(p, 'w', encoding='utf-8').write('\n'.join(lines))
print('   inserted after rdanieli/tentra-mcp')
PYEOF

echo "4/5  Branch, commit, push ..."
git checkout -b add-rnv-color-mcp
git add README.md
git commit -m "Add RNVizion/rnv-color-mcp to Architecture & Design"
git push -u origin add-rnv-color-mcp --force

echo "5/5  Opening the pull request ..."
gh pr create --repo punkpeye/awesome-mcp-servers \
  --head "$GHUSER:add-rnv-color-mcp" \
  --title "Add RNVizion/rnv-color-mcp (Architecture & Design)" \
  --body "Adds **rnv-color-mcp**, a hosted color-workflow MCP server (Python, Streamable HTTP).

Tools: mix (including Kubelka-Munk paint physics), convert between formats, generate harmonies, transform text case, and save/list/get named palettes. It resolves hex / CSS / custom brand color names and refuses unknown colors rather than guessing.

Published to the official MCP registry as \`io.github.RNVizion/rnv-color-mcp\`. Placed alphabetically under Architecture & Design, following the existing format and legend (🐍 ☁️)."
echo ""
echo "Done. The PR URL is printed above."
