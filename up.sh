curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:7860/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
