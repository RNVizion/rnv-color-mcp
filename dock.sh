cat > Dockerfile << 'EOF'
FROM python:3.13-slim

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"
WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user . .

ENV RNV_PALETTE_STORE=/data/palettes.json
ENV PORT=7860
EXPOSE 7860

CMD ["python", "server.py"]
EOF

cat > .dockerignore << 'EOF'
.venv/
__pycache__/
*.pyc
palettes.json
.git/
*.tmp
EOF

cat > requirements.txt << 'EOF'
# Engine, store, and resolver are standard-library only.
fastmcp>=3.4,<4
EOF

echo "created:"; ls -la Dockerfile .dockerignore requirements.txt
