from __future__ import annotations

import base64
import os
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def private_key_from_env() -> Ed25519PrivateKey:
    raw = os.environ.get("SPARKLE_ED_PRIVATE_KEY", "").strip()
    if not raw:
        raise RuntimeError("SPARKLE_ED_PRIVATE_KEY is not set")
    seed = base64.b64decode(raw)
    if len(seed) != 32:
        raise RuntimeError("SPARKLE_ED_PRIVATE_KEY must be base64 of a 32-byte Ed25519 seed")
    return Ed25519PrivateKey.from_private_bytes(seed)


def sign_file(path: Path, key: Ed25519PrivateKey | None = None) -> str:
    signing_key = key if key is not None else private_key_from_env()
    signature = signing_key.sign(path.read_bytes())
    return base64.b64encode(signature).decode("ascii")


def verify_file(path: Path, signature_b64: str, public_key_b64: str) -> None:
    public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
    public_key.verify(base64.b64decode(signature_b64), path.read_bytes())
