#!/usr/bin/env bash
export RNV_AUTH=1
export RNV_AUTH_PUBLIC_KEY="$(cat dev_public_key.pem)"

echo "RNV_AUTH=$RNV_AUTH  KEY_LEN=${#RNV_AUTH_PUBLIC_KEY}"

pkill -f server.py; sleep 1
nohup python server.py > server.log 2>&1 &
sleep 3

echo "--- server.log tail ---"
tail -3 server.log
echo "--- metadata route ---"
curl -s -w "\n[HTTP %{http_code}]\n" http://localhost:7860/.well-known/oauth-protected-resource
