echo "=== is anything listening on 7860? ==="
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:7860/ || echo "nothing there"

echo "=== full server.log ==="
cat server.log

echo "=== try starting in the FOREGROUND (show the real error) ==="
export RNV_AUTH=1
export RNV_AUTH_PUBLIC_KEY="$(cat dev_public_key.pem)"
pkill -f server.py; sleep 1
python server.py
