from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.core.errors import APIError

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    return password_hash is not None and password_hasher.verify(password, password_hash)


def create_access_token(subject: UUID) -> str:
    settings = get_settings()
    if len(settings.jwt_secret_key.strip()) < 32:
        raise APIError(
            503,
            "authentication_not_configured",
            "Set JWT_SECRET_KEY to at least 32 characters before logging in.",
        )
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {
            "sub": str(subject),
            "iat": now,
            "exp": expires_at,
            "type": "access",
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
