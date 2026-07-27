# gen_test_key.py  — throwaway, do NOT commit the .pem or the token
from fastmcp.server.auth.providers.jwt import RSAKeyPair

ISSUER = "https://rnvizion.dev"
AUDIENCE = "https://rnvizion-rnv-color-mcp.hf.space/mcp"

kp = RSAKeyPair.generate()

with open("dev_public_key.pem", "w") as f:
    f.write(kp.public_key)

token = kp.create_token(
    subject="rnv-dev-test",
    issuer=ISSUER,
    audience=AUDIENCE,
    scopes=["read", "write"],
)

print("Wrote dev_public_key.pem")
print("\n=== TEST TOKEN (hold this for later) ===")
print(token)
