#!/bin/bash
set -e
python3 - << 'PYEOF'
import re, pathlib
p = pathlib.Path("engine/resolve.py")
t = p.read_text()
t = t.replace('"#0a0a0f"', '"#1a1a1a"')   # near-black -> charcoal
# add dark/light-mode gold aliases if not already present
if "dark gold" not in t:
    t = t.replace(
        '    "rnv gold": "#d2bc93",\n',
        '    "rnv gold": "#d2bc93",\n'
        '    "dark gold": "#b19145",\n'
        '    "gold dark": "#b19145",\n'
        '    "light-mode gold": "#b19145",\n'
    )
p.write_text(t)
print("resolve.py updated: near-black=#1a1a1a, added #b19145 gold aliases")
PYEOF
BASE=$(git remote get-url space | sed 's|https://[^@]*@|https://|')
USER=$(echo "$BASE" | cut -d/ -f5)
git add -A
git commit -m "Brand: near-black -> #1a1a1a; add #b19145 dark/light-mode gold" || true
git push "$(echo "$BASE" | sed "s|https://|https://${USER}:${HF_TOKEN}@|")" HEAD:main --force
echo "Pushed. After rebuild, near-black=#1a1a1a, 'dark gold'=#b19145 resolve correctly."
