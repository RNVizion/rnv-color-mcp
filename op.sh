cd /workspaces/rnv-color-mcp && cat server.py > /tmp/server_dump.txt && cat api.py > /tmp/api_dump.txt && python -m http.server 8000 --directory /tmp
