#!/bin/bash
set -e

# >>> EDIT THIS: your Hugging Face username (the owner in your Space URL) <<<
HF_USER=RNVizion

# Token: set HF_TOKEN as a Codespace secret (like your ANTHROPIC_API_KEY),
# or pass it as an argument:  bash phs.sh hf_xxxxxxxx
TOKEN="${HF_TOKEN:-$1}"
if [ -z "$TOKEN" ]; then echo "Need a token: set HF_TOKEN secret or run: bash phs.sh <token>"; exit 1; fi

# 1. Add the Docker frontmatter to README.md (only if not already there)
if ! head -1 README.md | grep -q '^---'; then
  cat > /tmp/fm.md << 'EOF'
---
title: RNV Color MCP
emoji: 🎨
colorFrom: gray
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
short_description: Color workflow MCP server
---

EOF
  cat README.md >> /tmp/fm.md
  mv /tmp/fm.md README.md
  echo "Added frontmatter."
else
  echo "Frontmatter already present, skipping."
fi

# 2. Point a 'space' remote at the HF Space (token used only for this push)
git remote remove space 2>/dev/null || true
git remote add space "https://${HF_USER}:${TOKEN}@huggingface.co/spaces/${HF_USER}/rnv-color-mcp"

# 3. Commit and push -> auto-builds the Space
git add -A
git commit -m "Deploy MCP color server to HF Space" || true
git push space HEAD:main --force

# 4. Strip the token back out of the remote config
git remote set-url space "https://huggingface.co/spaces/${HF_USER}/rnv-color-mcp"
echo "Pushed. Open your Space and watch the build logs."
