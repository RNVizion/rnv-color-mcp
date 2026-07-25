pkill -f "python server.py"; sleep 1
export RNV_AUTH=1
export RNV_AUTH_PUBLIC_KEY="$(cat dev_public_key.pem)"
nohup python server.py > server.log 2>&1 &


