python gen_test_key.py
export RNV_AUTH=1
export RNV_AUTH_PUBLIC_KEY="$(cat dev_public_key.pem)"
python server.py    # starts on :7860

