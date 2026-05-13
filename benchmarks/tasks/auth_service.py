"""Authentication service: token issuance and validation."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass


# Minimum token length for security
_MIN_TOKEN_BYTES = 32
_TOKEN_TTL_SECONDS = 3600


@dataclass
class User:
    user_id: str
    username: str
    password_hash: str
    created_at: float


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Return (hash, salt) for the given plaintext password."""
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=200_000,
    )
    return digest.hex(), salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    candidate, _ = hash_password(password, salt)
    return hmac.compare_digest(candidate, stored_hash)


class TokenStore:
    """In-memory token store with TTL enforcement."""

    def __init__(self, ttl: float = _TOKEN_TTL_SECONDS) -> None:
        self._tokens: dict[str, tuple[str, float]] = {}  # token -> (user_id, expires_at)
        self._ttl = ttl

    def issue(self, user_id: str) -> str:
        """Issue a new token for user_id, replacing any existing one."""
        token = secrets.token_urlsafe(_MIN_TOKEN_BYTES)
        self._tokens[token] = (user_id, time.monotonic() + self._ttl)
        return token

    def validate(self, token: str) -> str | None:
        """Return user_id if the token is valid and not expired, else None."""
        entry = self._tokens.get(token)
        if entry is None:
            return None
        user_id, expires_at = entry
        if time.monotonic() > expires_at:
            del self._tokens[token]
            return None
        return user_id

    def revoke(self, token: str) -> bool:
        """Remove the token. Returns True if it existed."""
        return self._tokens.pop(token, None) is not None
