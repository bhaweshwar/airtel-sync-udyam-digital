"""Encryption at rest for small personal values (phone numbers). Phase 0 owns this file."""
from __future__ import annotations

from cryptography.fernet import Fernet

from ..config import settings


def encrypt(value: str) -> str:
    return Fernet(settings.fernet_key.encode()).encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    return Fernet(settings.fernet_key.encode()).decrypt(token.encode()).decode()
