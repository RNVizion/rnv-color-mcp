#!/bin/bash
# add_license_glama.sh  -  add MIT LICENSE + glama.json, push to GitHub (and HF Space).
# Run from the rnv-color-mcp repo root:
#     bash add_license_glama.sh
set -e

git remote get-url origin 2>/dev/null | grep -q "rnv-color-mcp" || {
  echo "Run this from the rnv-color-mcp repo root (where server.py lives)."; exit 1; }

echo "1/3  Writing LICENSE (MIT) ..."
cat > LICENSE << 'LICEOF'
MIT License

Copyright (c) 2026 Christian Smith

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
LICEOF

echo "2/3  Writing glama.json ..."
cat > glama.json << 'GLAMAEOF'
{
  "$schema": "https://glama.ai/mcp/schemas/server.json",
  "maintainers": ["RNVizion"]
}
GLAMAEOF
python3 -c "import json; json.load(open('glama.json')); print('   glama.json valid')"

echo "3/3  Commit + push ..."
git add LICENSE glama.json
git commit -m "Add MIT license and glama.json" || echo "   (nothing new to commit)"
git push origin HEAD:main || echo "   NOTE: origin push failed - check it manually."
if [ -n "$HF_TOKEN" ]; then
  SPACE=$(git remote get-url space | sed 's|https://[^@]*@|https://|')
  SUSER=$(echo "$SPACE" | cut -d/ -f5)
  git push "$(echo "$SPACE" | sed "s|https://|https://${SUSER}:${HF_TOKEN}@|")" HEAD:main --force
else
  echo "   HF_TOKEN not set - skipped Space mirror (fine; Glama scans GitHub)."
fi
echo ""
echo "Done. LICENSE + glama.json are on GitHub."
echo "Now re-run Glama's 'Claim ownership' so it picks up glama.json; the License F clears on the next scan."
