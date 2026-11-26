from datetime import datetime, timedelta, timezone
import hashlib
import hmac

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.users import User

bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")


def _credentials_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _password_bytes(password: str) -> bytes:
    # Pre-hash so long passwords are not silently truncated by bcrypt's 72-byte limit.
    return hashlib.sha256(password.encode("utf-8")).digest()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("utf-8")


def is_legacy_password_hash(password_hash: str) -> bool:
    return len(password_hash) == 64 and all(char in "0123456789abcdef" for char in password_hash.lower())


def verify_password(password: str, password_hash: str) -> bool:
    if is_legacy_password_hash(password_hash):
        return hmac.compare_digest(hashlib.sha256(password.encode("utf-8")).hexdigest(), password_hash.lower())

    try:
        return bcrypt.checkpw(_password_bytes(password), password_hash.encode("utf-8"))
    except (TypeError, ValueError):
        return False


def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "iat": now,
        "exp": now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes)),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise _credentials_error()


def is_admin(user: User) -> bool:
    return user.email.lower() in settings.admin_email_set


def require_self_or_admin(user: User, owner_id: int, detail: str = "Not enough permissions") -> None:
    if user.id != owner_id and not is_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _credentials_error()

    user_id = decode_access_token(credentials.credentials)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise _credentials_error()
    return user
