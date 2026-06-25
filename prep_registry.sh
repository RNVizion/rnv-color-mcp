#!/bin/bash
# prep_registry.sh  -  stage the registry listing: server.json + README marker, then push.
# Run from the repo root in your Codespace:
#     bash prep_registry.sh
# Uses the Codespace's built-in GitHub auth for origin, and HF_TOKEN for the Space.
set -e

echo "1/4  Writing server.json ..."
cat > server.json << 'JSONEOF'
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-10-17/server.schema.json",
  "name": "io.github.rnvizion/rnv-color-mcp",
  "description": "A complete color workflow over MCP: mix, convert, harmonize, and remember palettes.",
  "version": "1.0.0",
  "repository": {
    "url": "https://github.com/RNVizion/rnv-color-mcp",
    "source": "github"
  },
  "remotes": [
    { "type": "streamable-http", "url": "https://rnvizion-rnv-color-mcp.hf.space/mcp" }
  ]
}
JSONEOF
python3 -c "import json; json.load(open('server.json')); print('   server.json is valid JSON')"

echo "2/4  Syncing README mcp-name marker to match server.json ..."
sed -i 's|<!-- mcp-name:.*-->|<!-- mcp-name: io.github.rnvizion/rnv-color-mcp -->|' README.md
grep -m1 "mcp-name" README.md

echo "3/4  Commit ..."
git add -A
git commit -m "Add server.json for the MCP registry; sync mcp-name marker" || echo "   (nothing new to commit)"

echo "4/4  Push to GitHub (origin) and HF (space) ..."
git push origin HEAD:main || echo "   NOTE: origin push skipped/failed - check it manually if needed."
if [ -n "$HF_TOKEN" ]; then
  SPACE=$(git remote get-url space | sed 's|https://[^@]*@|https://|')
  SUSER=$(echo "$SPACE" | cut -d/ -f5)
  git push "$(echo "$SPACE" | sed "s|https://|https://${SUSER}:${HF_TOKEN}@|")" HEAD:main --force
else
  echo "   HF_TOKEN not set - skipped Space push (fine; the Space already runs the same code)."
fi
echo ""
echo "Done. server.json is committed and the README marker matches it."
echo "Next: bash publish_registry.sh"
