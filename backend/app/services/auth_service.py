from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings
from app.utils.errors import AppError, ConfigurationError


def hash_password(password: str) -> str:
    # bcrypt only uses the first 72 bytes of the password.
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode("utf-8"))
    except ValueError:
        return False


def _secret() -> str:
    if not settings.JWT_SECRET_KEY or len(settings.JWT_SECRET_KEY) < 32:
        raise ConfigurationError("JWT_SECRET_KEY must be set to a random string of at least 32 characters.")
    return settings.JWT_SECRET_KEY


def create_access_token(user_id: int) -> tuple[str, int]:
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(seconds=expires_in), "type": "access"}
    return jwt.encode(payload, _secret(), algorithm=settings.JWT_ALGORITHM), expires_in


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, _secret(), algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise AppError("Session expired. Please log in again.", status_code=401) from exc
    except jwt.InvalidTokenError as exc:
        raise AppError("Invalid authentication token.", status_code=401) from exc
    if payload.get("type") != "access" or "sub" not in payload:
        raise AppError("Invalid authentication token.", status_code=401)
    return int(payload["sub"])
