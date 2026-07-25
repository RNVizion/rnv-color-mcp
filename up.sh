pkill -f "python server.py"; sleep 1
export RNV_AUTH=1
export RNV_AUTH_PUBLIC_KEY="$(cat dev_public_key.pem)"
python server.py

