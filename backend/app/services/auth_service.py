import logging
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.auth import UserRegister
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)

security_scheme = HTTPBearer()


async def register_user(db: AsyncSession, user_data: UserRegister) -> User:
    """Create a new user and their wallet in a single transaction."""
    # Check email uniqueness
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Check username uniqueness
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hash_password(user_data.password),
        phone=user_data.phone,
        birth_date=user_data.birth_date,
    )
    db.add(user)
    await db.flush()

    wallet = Wallet(user_id=user.id)
    db.add(wallet)
    await db.flush()

    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    """Verify credentials and return the user."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return user


def generate_tokens(user: User) -> dict:
    """Generate access and refresh tokens for a user."""
    token_data = {"sub": str(user.id)}
    return {
        "access_token": create_access_token(token_data),
        "refresh_token": create_refresh_token(token_data),
        "token_type": "bearer",
    }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency: extract JWT, decode, fetch user from DB."""
    payload = decode_token(credentials.credentials)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """Dependency that also checks is_active."""
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )
    return user


_optional_bearer = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Like get_current_user but returns None instead of raising on missing/invalid token."""
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            return None
        user_id = UUID(payload.get("sub", ""))
    except Exception:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user and user.is_active:
        return user
    return None


async def get_admin_user(
    user: User = Depends(get_current_active_user),
) -> User:
    """Dependency that also checks is_admin."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


async def request_password_reset(db: AsyncSession, email: str) -> None:
    """Generate reset token and send email. Silent if user doesn't exist (security)."""
    import secrets as secrets_mod
    from datetime import datetime, timedelta, timezone

    from app.config import settings
    from app.models.password_reset_token import PasswordResetToken
    from app.services import email_service

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        return  # silent for security

    token = secrets_mod.token_urlsafe(32)
    reset = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(reset)
    await db.flush()

    reset_url = f"{settings.APP_URL}/reset-password/{token}"
    html, text = email_service.render_password_reset(user.username, reset_url)
    try:
        await email_service.send_email(
            user.email, "Redefinir senha — Patinho", html, text
        )
    except Exception:
        logger.exception("Failed to send password reset email to %s", user.email)


async def reset_password(db: AsyncSession, token: str, new_password: str) -> None:
    from datetime import datetime, timezone

    from app.models.password_reset_token import PasswordResetToken

    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == token)
    )
    reset = result.scalar_one_or_none()
    if not reset:
        raise HTTPException(status_code=400, detail="Token inválido")
    if reset.used_at:
        raise HTTPException(status_code=400, detail="Token já utilizado")
    if reset.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token expirado")

    user = await db.get(User, reset.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="Usuário não encontrado")

    user.hashed_password = hash_password(new_password)
    reset.used_at = datetime.now(timezone.utc)
    await db.flush()


async def send_welcome_email(user: User) -> None:
    """Send a welcome email. Best-effort — never crashes the caller."""
    from app.config import settings
    from app.services import email_service

    try:
        html, text = email_service.render_welcome(user.username, settings.APP_URL)
        await email_service.send_email(
            user.email, "Bem-vindo ao Patinho", html, text
        )
    except Exception:
        logger.exception("Failed to send welcome email to %s", user.email)
