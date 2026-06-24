git remote add space https://huggingface.co/spaces/<OWNER>/rnv-color-mcp
git add -A
git commit -m "Add Docker frontmatter for HF Space"
git push space HEAD:main --force
