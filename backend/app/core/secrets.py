from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken


def _derive_fernet_key(raw_key: str) -> bytes:
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _fernet() -> Fernet | None:
    raw_key = os.getenv("APP_SECRETS_KEY", "").strip()
    if not raw_key:
        return None
    return Fernet(_derive_fernet_key(raw_key))


def encrypt_secret(value: str) -> str:
    if not value:
        return ""

    fernet = _fernet()
    if not fernet:
        raise RuntimeError(
            "APP_SECRETS_KEY is required before storing API keys or tokens. "
            "Set a long random value in the backend environment."
        )

    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    if not value:
        return ""

    fernet = _fernet()
    if not fernet:
        return ""

    try:
        return fernet.decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""
