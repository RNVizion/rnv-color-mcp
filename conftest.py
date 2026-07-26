"""
Test harness for rnv-color-mcp auth.

server.py builds its auth provider at import time from environment variables,
so the environment must be set BEFORE server is imported. pytest loads a
root conftest.py first, which makes this the correct place for it.

The keypair is generated per run and never written to disk: tests mint their
own tokens and the server verifies against the matching public key.
"""
from __future__ import annotations

import os
import tempfile

from fastmcp.server.auth.providers.jwt import RSAKeyPair

ISSUER = "https://rnvizion.dev"
AUDIENCE = "https://rnvizion-rnv-color-mcp.hf.space/mcp"
BASE_URL = "https://rnvizion-rnv-color-mcp.hf.space"

KEYPAIR = RSAKeyPair.generate()

os.environ["RNV_AUTH"] = "1"
os.environ["RNV_AUTH_PUBLIC_KEY"] = KEYPAIR.public_key
os.environ["RNV_AUTH_ISSUER"] = ISSUER
os.environ["RNV_AUTH_AUDIENCE"] = AUDIENCE
os.environ["RNV_AUTH_BASE_URL"] = BASE_URL

# keep tests off the real palette store and off the HF Dataset
os.environ["RNV_PALETTE_STORE"] = os.path.join(
    tempfile.mkdtemp(prefix="rnv-test-"), "palettes.json"
)
os.environ.pop("HF_TOKEN", None)

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def keypair():
    return KEYPAIR


@pytest.fixture
def make_token(keypair):
    """Mint a JWT. Defaults are valid; override one field per negative case."""

    def _make(
        scopes=("read", "write"),
        issuer=ISSUER,
        audience=AUDIENCE,
        subject="rnv-test",
        expires_in_seconds=None,
    ):
        kwargs = {
            "subject": subject,
            "issuer": issuer,
            "audience": audience,
            "scopes": list(scopes),
        }
        if expires_in_seconds is not None:
            kwargs["expires_in_seconds"] = expires_in_seconds
        return keypair.create_token(**kwargs)

    return _make
