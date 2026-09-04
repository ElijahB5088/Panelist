from __future__ import annotations

import base64
import hashlib
import os
import secrets
from datetime import datetime, timezone

from cryptography.fernet import Fernet

from .config import settings


def _key() -> bytes:
    key = settings.credential_encryption_key.strip()
    if key:
        return key.encode("utf-8")
    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


fernet = Fernet(_key())


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210_000)
    return f"{base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(derived).decode()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt_b64, derived_b64 = password_hash.split("$", 1)
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(derived_b64.encode())
    except Exception:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210_000)
    return secrets.compare_digest(candidate, expected)


def issue_token() -> str:
    return secrets.token_urlsafe(32)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def encrypt_secret(value: str) -> str:
    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    return fernet.decrypt(value.encode("utf-8")).decode("utf-8")
