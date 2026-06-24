#!/bin/bash
set -e
# Trivial change to force a fresh Space build
date "+rebuild test %Y-%m-%d %H:%M" >> .rebuild_marker
BASE=$(git remote get-url space | sed 's|https://[^@]*@|https://|')
USER=$(echo "$BASE" | cut -d/ -f5)
git add -A
git commit -m "Force rebuild: test palette persistence" || true
git push "$(echo "$BASE" | sed "s|https://|https://${USER}:${HF_TOKEN}@|")" HEAD:main --force
echo "Pushed. Watch the Space rebuild to Running, then test in a fresh chat."
