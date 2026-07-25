pkill -f "python server.py"; sleep 1
export RNV_AUTH=1
export RNV_AUTH_PUBLIC_KEY="$(cat dev_public_key.pem)"
python server.py
# 1. The discovery route now exists — show me the resource field
curl -s http://localhost:7860/.well-known/oauth-protected-resource

# 2. The 401 now points clients at that route
curl -s -i -X POST http://localhost:7860/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | head -20
