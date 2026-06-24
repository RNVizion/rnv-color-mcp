#!/bin/bash
set -e
# Delete helper scripts (you'll recreate as needed)
rm -f look.sh phs.sh dock.sh rebuild.sh fixdata.sh preview.sh steps.sh \
      apply_persistence.sh apply_brand_source.sh

# Keep future helpers out of the repo
grep -q '^\*\.sh$' .gitignore 2>/dev/null || echo '*.sh' >> .gitignore

echo "Removed helper scripts. Remaining files:"
ls -1
echo ""
git status --short
