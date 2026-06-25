#!/bin/bash
# add_license_repos.sh  -  add MIT LICENSE to ask-the-corpus and publishing-agent.
# Scans files for obvious secrets before committing; skips a repo if anything looks risky.
#     bash add_license_repos.sh
set -e

unset GITHUB_TOKEN GH_TOKEN
GHUSER=$(gh api user -q .login)
TOKEN=$(gh auth token)
if [ -z "$TOKEN" ]; then
  echo "No gh token. Run: gh auth login -h github.com -p https -s repo -w"; exit 1; fi
echo "Account: $GHUSER"

WORK="$HOME/_license_work"
rm -rf "$WORK"; mkdir -p "$WORK"

for REPO in ask-the-corpus publishing-agent; do
  echo ""
  echo "================  $REPO  ================"
  URL="https://x-access-token:${TOKEN}@github.com/${GHUSER}/${REPO}.git"
  cd "$WORK"
  git clone -q "$URL" "$REPO" || { echo "  clone failed (does $GHUSER/$REPO exist?); skipping."; continue; }
  cd "$REPO"
  BR=$(git rev-parse --abbrev-ref HEAD)

  echo "  Scanning files for secrets ..."
  python3 - << 'PYEOF'
import os, re, sys
patterns = [
    (r'hf_[A-Za-z0-9]{20,}', 'HuggingFace token'),
    (r'gh[pousr]_[A-Za-z0-9]{20,}', 'GitHub token'),
    (r'sk-ant-[A-Za-z0-9-]{20,}', 'Anthropic key'),
    (r'sk-[A-Za-z0-9]{20,}', 'OpenAI-style key'),
    (r'AKIA[0-9A-Z]{16}', 'AWS access key'),
    (r'-----BEGIN [A-Z ]*PRIVATE KEY-----', 'private key'),
]
hits = []
for root, dirs, files in os.walk('.'):
    if '.git' in dirs: dirs.remove('.git')
    for f in files:
        p = os.path.join(root, f)
        try:
            for i, line in enumerate(open(p, encoding='utf-8', errors='ignore'), 1):
                for pat, name in patterns:
                    if re.search(pat, line):
                        hits.append(f"    {p}:{i}  ({name})")
        except Exception:
            pass
if hits:
    print("  !! POSSIBLE SECRET(S) FOUND:")
    print("\n".join(hits[:30]))
    sys.exit(1)
print("  clean.")
PYEOF
  if [ $? -ne 0 ]; then
    echo "  Skipping $REPO (review/rotate the above, then re-run)."; continue
  fi

  if [ -f LICENSE ]; then
    echo "  LICENSE already present; skipping."; continue
  fi

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

  git add LICENSE
  git commit -q -m "Add MIT license"
  git push -q "$URL" "HEAD:$BR"
  echo "  licensed + pushed to $BR."
done

echo ""
echo "Done. Check each repo on GitHub - the License should now read MIT."
