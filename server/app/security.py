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
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def issue_token() -> str:
    return secrets.token_urlsafe(32)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def encrypt_secret(value: str) -> str:
    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    return fernet.decrypt(value.encode("utf-8")).decode("utf-8")
