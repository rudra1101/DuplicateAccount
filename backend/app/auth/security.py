import os
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError


_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (InvalidHashError, VerifyMismatchError):
        return False


def _secret() -> str:
    secret = os.getenv("AUTH_SECRET_KEY", "").strip()
    if not secret:
        raise RuntimeError("AUTH_SECRET_KEY is not configured.")
    return secret


def create_access_token(user_id: int, username: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    minutes = int(os.getenv("AUTH_ACCESS_TOKEN_MINUTES", "480"))
    return jwt.encode(
        {
            "sub": str(user_id),
            "username": username,
            "role": role,
            "iat": now,
            "exp": now + timedelta(minutes=minutes),
        },
        _secret(),
        algorithm="HS256",
    )


def decode_access_token(token: str):
    return jwt.decode(token, _secret(), algorithms=["HS256"])
