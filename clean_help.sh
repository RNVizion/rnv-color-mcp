#!/bin/bash
set -e
# Delete helper scripts (you'll recreate as needed)
rm -f *.sh

rm -rf ~/awesome-mcp-servers ~/_license_work

# Keep future helpers out of the repo
grep -q '^\*\.sh$' .gitignore 2>/dev/null || echo '*.sh' >> .gitignore

echo "Removed helper scripts. Remaining files:"
ls -1
echo ""
git status --short
