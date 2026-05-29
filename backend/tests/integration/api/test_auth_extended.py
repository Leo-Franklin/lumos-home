"""Extended integration tests for app/api/auth.py.

Covers endpoints not fully tested in test_auth.py:
- POST /auth/login (remember_me=True/False, unverified user, wrong password)
- GET /auth/verify-email (success, token not found, token expired)
- POST /auth/forgot-password (email exists — mock email service, verify token created)
- POST /auth/reset-password (success flow)
- POST /auth/register (prod mode with RESEND_API_KEY — sends verification email)
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# Ensure email_token tables are registered with Base.metadata before any test runs.
# The conftest.py only imports app.models.user; we need email_token too.
from app.models import email_token as _et  # noqa: F401 – side-effect import registers ORM models

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unique_email() -> str:
    return f'test-{uuid.uuid4()}@example.com'


async def _create_active_user(password: str = 'TestPass123!') -> tuple[str, str]:
    """Insert an active user directly in the DB, return (email, plain_password)."""
    from app.auth import hash_password
    from app.database import AsyncSessionLocal
    from app.models.user import User

    email = _unique_email()
    async with AsyncSessionLocal() as db:
        user = User(
            email=email,
            password_hash=hash_password(password),
            is_active=True,
            is_superuser=False,
        )
        db.add(user)
        await db.commit()
    return email, password


async def _create_inactive_user(password: str = 'TestPass123!') -> tuple[str, str]:
    """Insert an inactive (unverified) user directly in the DB."""
    from app.auth import hash_password
    from app.database import AsyncSessionLocal
    from app.models.user import User

    email = _unique_email()
    async with AsyncSessionLocal() as db:
        user = User(
            email=email,
            password_hash=hash_password(password),
            is_active=False,
            is_superuser=False,
        )
        db.add(user)
        await db.commit()
    return email, password


async def _get_user_id_by_email(email: str) -> int:
    """Fetch user id from the DB."""
    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app.models.user import User

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        return user.id


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_success_remember_me_false():
    """Successful login with remember_me=False → expires_in == 24 * 3600."""
    from app.main import app

    email, password = await _create_active_user()

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.post(
            '/api/v1/auth/login',
            json={'email': email, 'password': password, 'remember_me': False},
        )

    assert response.status_code == 200
    data = response.json()
    assert data['token_type'] == 'bearer'
    assert 'access_token' in data
    assert data['expires_in'] == 24 * 3600  # 86400 seconds


@pytest.mark.asyncio
async def test_login_success_remember_me_true():
    """Successful login with remember_me=True → expires_in == 720 * 3600 (30 days)."""
    from app.main import app

    email, password = await _create_active_user()

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.post(
            '/api/v1/auth/login',
            json={'email': email, 'password': password, 'remember_me': True},
        )

    assert response.status_code == 200
    data = response.json()
    assert data['expires_in'] == 720 * 3600  # 2592000 seconds (30 days)


@pytest.mark.asyncio
async def test_login_unverified_user_returns_403():
    """Login with an inactive (unverified) user must return 403."""
    from app.main import app

    email, password = await _create_inactive_user()

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.post(
            '/api/v1/auth/login',
            json={'email': email, 'password': password},
        )

    assert response.status_code == 403
    body = response.json()
    assert 'verify' in body['error']['message'].lower()


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401():
    """Login with wrong password must return 401."""
    from app.main import app

    email, _correct_password = await _create_active_user()

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.post(
            '/api/v1/auth/login',
            json={'email': email, 'password': 'WrongPassword!'},
        )

    assert response.status_code == 401
    body = response.json()
    assert 'Invalid' in body['error']['message']


@pytest.mark.asyncio
async def test_login_nonexistent_user_returns_401():
    """Login with an email that does not exist must return 401."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.post(
            '/api/v1/auth/login',
            json={'email': _unique_email(), 'password': 'AnyPass123!'},
        )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /auth/verify-email
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_email_success():
    """Providing a valid, unexpired token activates the user."""
    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app.main import app
    from app.models.email_token import EmailVerificationToken
    from app.models.user import User

    # Create an inactive user
    email, _ = await _create_inactive_user()
    user_id = await _get_user_id_by_email(email)

    # Insert a valid verification token
    token_str = str(uuid.uuid4())
    async with AsyncSessionLocal() as db:
        vt = EmailVerificationToken(
            user_id=user_id,
            token=token_str,
            expires_at=datetime.now() + timedelta(hours=24),
        )
        db.add(vt)
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/api/v1/auth/verify-email', params={'token': token_str})

    assert response.status_code == 200
    assert 'verified' in response.json()['message'].lower()

    # Confirm user is now active
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        assert user.is_active is True

    # Confirm token was deleted
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(EmailVerificationToken).where(EmailVerificationToken.token == token_str)
        )
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_verify_email_token_not_found_returns_400():
    """Supplying a non-existent token returns 400."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get(
            '/api/v1/auth/verify-email',
            params={'token': str(uuid.uuid4())},
        )

    assert response.status_code == 400
    assert 'Invalid or expired token' in response.json()['error']['message']


@pytest.mark.asyncio
async def test_verify_email_expired_token_returns_400():
    """An expired token (expires_at in the past) returns 400."""
    from app.database import AsyncSessionLocal
    from app.main import app
    from app.models.email_token import EmailVerificationToken

    email, _ = await _create_inactive_user()
    user_id = await _get_user_id_by_email(email)

    token_str = str(uuid.uuid4())
    async with AsyncSessionLocal() as db:
        vt = EmailVerificationToken(
            user_id=user_id,
            token=token_str,
            expires_at=datetime.now() - timedelta(hours=1),  # already expired
        )
        db.add(vt)
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/api/v1/auth/verify-email', params={'token': token_str})

    assert response.status_code == 400
    assert 'Invalid or expired token' in response.json()['error']['message']


# ---------------------------------------------------------------------------
# POST /auth/forgot-password (email exists)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forgot_password_existing_email_creates_token_and_sends_email():
    """When email exists, a PasswordResetToken must be created and email sent."""
    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app.main import app
    from app.models.email_token import PasswordResetToken

    email, _ = await _create_active_user()

    mock_email = MagicMock()
    mock_email.send_verification_email = AsyncMock(return_value=True)
    mock_email.send_password_reset_email = AsyncMock(return_value=True)

    with patch('app.api.auth.get_email_service', return_value=mock_email):
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            response = await client.post(
                '/api/v1/auth/forgot-password',
                json={'email': email},
            )

    assert response.status_code == 200
    assert 'If that email exists' in response.json()['message']

    # Verify email service was called once
    mock_email.send_password_reset_email.assert_called_once()

    # Verify a PasswordResetToken was persisted for this user
    user_id = await _get_user_id_by_email(email)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(PasswordResetToken).where(PasswordResetToken.user_id == user_id)
        )
        token_record = result.scalar_one_or_none()
        assert token_record is not None
        assert token_record.expires_at > datetime.now()


# ---------------------------------------------------------------------------
# POST /auth/reset-password (success flow)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reset_password_success():
    """Valid reset token + new password → password updated, token deleted."""
    from sqlalchemy import select

    from app.auth import verify_password
    from app.database import AsyncSessionLocal
    from app.main import app
    from app.models.email_token import PasswordResetToken
    from app.models.user import User

    email, _old_password = await _create_active_user(password='OldPass123!')
    user_id = await _get_user_id_by_email(email)

    reset_token_str = str(uuid.uuid4())
    async with AsyncSessionLocal() as db:
        rt = PasswordResetToken(
            user_id=user_id,
            token=reset_token_str,
            expires_at=datetime.now() + timedelta(minutes=15),
        )
        db.add(rt)
        await db.commit()

    new_password = 'BrandNewPass456!'

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.post(
            '/api/v1/auth/reset-password',
            json={'token': reset_token_str, 'new_password': new_password},
        )

    assert response.status_code == 200
    assert 'reset successful' in response.json()['message'].lower()

    # Verify password was actually changed
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        assert verify_password(new_password, user.password_hash)

    # Verify token was deleted
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token == reset_token_str)
        )
        assert result.scalar_one_or_none() is None


# ---------------------------------------------------------------------------
# POST /auth/register (prod mode — RESEND_API_KEY set)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_prod_mode_sends_verification_email():
    """When RESEND_API_KEY is set, register must send a verification email and
    return the 'Verification email sent' message (user not immediately active)."""
    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app.main import app
    from app.models.user import User

    email = _unique_email()

    mock_email = MagicMock()
    mock_email.send_verification_email = AsyncMock(return_value=True)
    mock_email.send_password_reset_email = AsyncMock(return_value=True)

    with patch('app.api.auth.get_email_service', return_value=mock_email):
        with patch('app.api.auth.get_settings') as mock_settings:
            # Simulate production mode: RESEND_API_KEY is non-empty
            settings_instance = MagicMock()
            settings_instance.resend_api_key = 're_live_abc123'
            settings_instance.app_base_url = 'http://localhost:8000'
            mock_settings.return_value = settings_instance

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url='http://test'
            ) as client:
                response = await client.post(
                    '/api/v1/auth/register',
                    json={'email': email, 'password': 'StrongPass123!'},
                )

    assert response.status_code == 201
    data = response.json()
    assert 'Verification email sent' in data['message']
    assert data['email'] == email

    # Verify the user was created as inactive
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.is_active is False

    # Verify email service was called
    mock_email.send_verification_email.assert_called_once()
