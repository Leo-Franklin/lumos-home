import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.auth import create_access_token, hash_password, verify_password
from app.config import get_settings
from app.deps import DBDep
from app.models.email_token import EmailVerificationToken, PasswordResetToken
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.services.email import get_email_service

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/register', response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    db: DBDep,
) -> MessageResponse:
    # Check if email exists
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail='Email already registered')

    settings = get_settings()
    # Skip email verification if no email API is configured (dev mode)
    is_active = not settings.resend_api_key

    # Create user
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        is_active=is_active,
        is_superuser=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    if is_active:
        return MessageResponse(
            message='Registration successful. You can now login.',
            email=user.email,
        )

    # Generate verification token (24h)
    token = str(uuid.uuid4())
    # EmailVerificationToken.expires_at is a naive DateTime column; keep naive.
    verification = EmailVerificationToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.now() + timedelta(hours=24),  # noqa: DTZ005
    )
    db.add(verification)
    await db.commit()

    # Send email
    email_service = get_email_service()
    await email_service.send_verification_email(user.email, token, settings.app_base_url)

    return MessageResponse(
        message='Verification email sent. Please check your inbox.',
        email=user.email,
    )


@router.get('/verify-email', response_model=MessageResponse)
async def verify_email(
    db: DBDep,
    token: str = Query(...),
) -> MessageResponse:
    result = await db.execute(
        select(EmailVerificationToken).where(EmailVerificationToken.token == token)
    )
    token_record = result.scalar_one_or_none()

    if not token_record:
        raise HTTPException(status_code=400, detail='Invalid or expired token')

    # EmailVerificationToken.expires_at is a naive DateTime column; compare naive.
    if token_record.expires_at < datetime.now():  # noqa: DTZ005
        raise HTTPException(status_code=400, detail='Invalid or expired token')

    # Activate user
    user_result = await db.execute(select(User).where(User.id == token_record.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail='Invalid or expired token')

    user.is_active = True
    await db.delete(token_record)
    await db.commit()

    return MessageResponse(message='Email verified. You can now login.')


@router.post('/login', response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: DBDep,
) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail='Invalid email or password')

    if not user.is_active:
        raise HTTPException(status_code=403, detail='Please verify your email first')

    settings = get_settings()
    expires_hours = 720 if body.remember_me else 24  # 30 days or 24h
    token = create_access_token(user.email, settings.jwt_secret_key, expires_hours)
    expires_in = expires_hours * 3600

    return TokenResponse(access_token=token, token_type='bearer', expires_in=expires_in)


@router.post('/forgot-password', response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: DBDep,
) -> MessageResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user:
        # Generate reset token (15 min)
        token = str(uuid.uuid4())
        # PasswordResetToken.expires_at is a naive DateTime column; keep naive.
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=datetime.now() + timedelta(minutes=15),  # noqa: DTZ005
        )
        db.add(reset_token)
        await db.commit()

        # Send email
        settings = get_settings()
        email_service = get_email_service()
        await email_service.send_password_reset_email(user.email, token, settings.app_base_url)

    # Always return same message (prevent user enumeration)
    return MessageResponse(message='If that email exists, a reset link has been sent.')


@router.post('/reset-password', response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest,
    db: DBDep,
) -> MessageResponse:
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == body.token)
    )
    token_record = result.scalar_one_or_none()

    # PasswordResetToken.expires_at is a naive DateTime column; compare naive.
    if not token_record or token_record.expires_at < datetime.now():  # noqa: DTZ005
        raise HTTPException(status_code=400, detail='Invalid or expired token')

    # Update user password
    user_result = await db.execute(select(User).where(User.id == token_record.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail='Invalid or expired token')

    user.password_hash = hash_password(body.new_password)
    await db.delete(token_record)
    await db.commit()

    return MessageResponse(
        message='Password reset successful. Please login with your new password.'
    )
