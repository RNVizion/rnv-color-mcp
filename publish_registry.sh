#!/bin/bash
# publish_registry.sh  -  publish server.json to the official MCP Registry.
# Run from the repo root in your Codespace, AFTER prep_registry.sh:
#     bash publish_registry.sh
# The login step is interactive: you'll visit a URL and enter a code in your browser.
set -e

echo "1/4  Installing the mcp-publisher CLI ..."
if ! command -v mcp-publisher >/dev/null 2>&1; then
  curl -L "https://github.com/modelcontextprotocol/registry/releases/latest/download/mcp-publisher_$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/').tar.gz" | tar xz mcp-publisher
  sudo mv mcp-publisher /usr/local/bin/
fi
echo "   installed: $(command -v mcp-publisher)"

echo ""
echo "2/4  Logging in to the registry with GitHub ..."
echo "   ---> A URL and a code will print below."
echo "   ---> Open the URL, enter the code, authorize as RNVizion, come back here."
echo ""
mcp-publisher login github

echo ""
echo "3/4  Publishing server.json ..."
mcp-publisher publish

echo ""
echo "4/4  Verifying it's live in the registry ..."
sleep 2
curl -s "https://registry.modelcontextprotocol.io/v0/servers?search=io.github.rnvizion/rnv-color-mcp" | python3 -m json.tool 2>/dev/null | head -40 || \
  curl -s "https://registry.modelcontextprotocol.io/v0/servers?search=io.github.rnvizion/rnv-color-mcp"
echo ""
echo "If you see your server's metadata above, you're published. 🎉"
