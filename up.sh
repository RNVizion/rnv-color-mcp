cat > gen_test_key.py << 'PYEOF'
from fastmcp.server.auth.providers.jwt import RSAKeyPair

kp = RSAKeyPair.generate()
with open("dev_public_key.pem", "w") as f:
    f.write(kp.public_key)

token = kp.create_token(
    subject="rnv-dev-test",
    issuer="https://rnvizion.dev",
    audience="https://rnvizion-rnv-color-mcp.hf.space/mcp",
    scopes=["read", "write"],
)
print("wrote dev_public_key.pem")
print(token)
PYEOF

grep -qxF 'dev_public_key.pem' .gitignore || echo 'dev_public_key.pem' >> .gitignore
grep -qxF 'gen_test_key.py' .gitignore || echo 'gen_test_key.py' >> .gitignore

python gen_test_key.py

export RNV_AUTH=1
export RNV_AUTH_PUBLIC_KEY="$(cat dev_public_key.pem)"
echo "KEY_LEN=${#RNV_AUTH_PUBLIC_KEY}"

pkill -f server.py; sleep 1
nohup python server.py > server.log 2>&1 &
sleep 3
tail -3 server.log

echo "--- metadata ---"
curl -s -w "\n[HTTP %{http_code}]\n" http://localhost:7860/.well-known/oauth-protected-resource/mcp
