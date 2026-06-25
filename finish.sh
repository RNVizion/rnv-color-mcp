#!/bin/bash
# remove_rebuild_marker.sh  -  delete the leftover .rebuild_marker and prevent recurrence.
#     bash remove_rebuild_marker.sh
set -e

git remote get-url origin 2>/dev/null | grep -q "rnv-color-mcp" || {
  echo "Run this from the rnv-color-mcp repo root."; exit 1; }

CHANGED=0
if git ls-files --error-unmatch .rebuild_marker >/dev/null 2>&1; then
  git rm -q .rebuild_marker; CHANGED=1
elif [ -f .rebuild_marker ]; then
  rm -f .rebuild_marker; CHANGED=1
fi

if ! grep -q '^\.rebuild_marker$' .gitignore 2>/dev/null; then
  echo '.rebuild_marker' >> .gitignore; CHANGED=1
fi

if [ "$CHANGED" -eq 0 ]; then
  echo ".rebuild_marker already gone and ignored. Nothing to do."; exit 0
fi

git add -A
git commit -q -m "Remove .rebuild_marker scaffolding; ignore it going forward"
git push origin HEAD:main || echo "  origin push failed - check manually."
if [ -n "$HF_TOKEN" ]; then
  SPACE=$(git remote get-url space | sed 's|https://[^@]*@|https://|')
  SUSER=$(echo "$SPACE" | cut -d/ -f5)
  git push "$(echo "$SPACE" | sed "s|https://|https://${SUSER}:${HF_TOKEN}@|")" HEAD:main --force
fi
echo "Done. .rebuild_marker removed from the repo."
