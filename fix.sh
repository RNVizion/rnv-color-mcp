#!/bin/bash
set -e
# Fix the namespace case to match what GitHub granted: io.github.RNVizion
sed -i 's|io.github.rnvizion/rnv-color-mcp|io.github.RNVizion/rnv-color-mcp|' server.json
sed -i 's|<!-- mcp-name:.*-->|<!-- mcp-name: io.github.RNVizion/rnv-color-mcp -->|' README.md

python3 -c "import json,re; n=json.load(open('server.json'))['name']; m=re.search(r'mcp-name:\s*(\S+)',open('README.md').read()).group(1); print('name  :',n); print('marker:',m); print('MATCH' if n==m else 'MISMATCH — stop')"

# Commit + push so GitHub/Space carry the corrected marker
git add -A
git commit -m "Fix registry namespace case: io.github.RNVizion" || true
git push origin HEAD:main || echo "(origin push skipped)"

# Republish (you're already logged in)
mcp-publisher publish

echo ""
echo "Verifying ..."
curl -s "https://registry.modelcontextprotocol.io/v0/servers?search=io.github.RNVizion/rnv-color-mcp" | python3 -m json.tool 2>/dev/null | head -40
