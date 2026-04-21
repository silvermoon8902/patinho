import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker, get_db
from app.schemas.auth import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    Token,
    TokenRefresh,
    UserLogin,
    UserRegister,
)
from app.services import auth_service
from app.services.auth_service import (
    authenticate_user,
    generate_tokens,
    register_user,
    send_welcome_email,
)
from app.utils.security import create_access_token, create_refresh_token, decode_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


async def _run_forgot_password(email: str) -> None:
    """Background task: request reset token and send email in its own session."""
    async with async_session_maker() as db:
        try:
            await auth_service.request_password_reset(db, email)
            await db.commit()
        except Exception:
            logger.exception("Forgot-password background task failed for %s", email)
            await db.rollback()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    user = await register_user(db, user_data)
    tokens = generate_tokens(user)
    background.add_task(send_welcome_email, user)
    return tokens


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, credentials.email, credentials.password)
    return generate_tokens(user)


@router.post("/refresh", response_model=Token)
async def refresh(body: TokenRefresh):
    payload = decode_token(body.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type, expected refresh token",
        )

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    token_data = {"sub": sub}
    return Token(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post("/forgot-password", status_code=202)
async def forgot_password(
    body: ForgotPasswordRequest,
    background: BackgroundTasks,
):
    background.add_task(_run_forgot_password, body.email)
    return {"message": "Se o e-mail existir, você receberá instruções em instantes."}


@router.post("/reset-password")
async def reset_password_endpoint(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    await auth_service.reset_password(db, body.token, body.new_password)
    return {"message": "Senha redefinida com sucesso"}
