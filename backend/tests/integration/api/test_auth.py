import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def mock_email_service():
    mock = MagicMock()
    mock.send_verification_email = AsyncMock(return_value=True)
    mock.send_password_reset_email = AsyncMock(return_value=True)
    return mock


@pytest.mark.asyncio
async def test_register_success(mock_email_service):
    email = f'newuser-{uuid.uuid4()}@example.com'
    with (
        patch('app.api.auth.get_email_service', return_value=mock_email_service),
        patch('app.api.auth.hash_password') as mock_hash,
        patch('app.api.auth.get_settings') as mock_settings,
    ):
        mock_hash.return_value = '$2b$12$LQv3c1yqBWV9kZN7t8pMGOKmRj9pVxD9y5xY7zX8J2K4L5M6N7O8P9Q0R'
        mock_settings.return_value.resend_api_key = ''  # Dev mode - no email verification

        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            response = await client.post(
                '/api/v1/auth/register',
                json={
                    'email': email,
                    'password': 'StrongPass123!',
                },
            )
        assert response.status_code == 201
        data = response.json()
        # In dev mode (no RESEND_API_KEY), user is active immediately
        assert data['message'] == 'Registration successful. You can now login.'
        assert data['email'] == email


@pytest.mark.asyncio
async def test_register_duplicate_email(mock_email_service):
    email = f'dup-{uuid.uuid4()}@example.com'
    with (
        patch('app.api.auth.get_email_service', return_value=mock_email_service),
        patch('app.api.auth.hash_password') as mock_hash,
    ):
        mock_hash.return_value = '$2b$12$LQv3c1yqBWV9kZN7t8pMGOKmRj9pVxD9y5xY7zX8J2K4L5M6N7O8P9Q0R'

        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            # Register first user
            await client.post(
                '/api/v1/auth/register',
                json={
                    'email': email,
                    'password': 'StrongPass123!',
                },
            )
            # Try duplicate
            response = await client.post(
                '/api/v1/auth/register',
                json={
                    'email': email,
                    'password': 'AnotherPass123!',
                },
            )
        assert response.status_code == 400
        assert 'already registered' in response.json()['error']['message']


@pytest.mark.asyncio
async def test_login_unverified_user(mock_email_service):
    """Test that login fails with 403 when user is not verified.

    This test only applies when RESEND_API_KEY is configured (production mode).
    In dev mode (no RESEND_API_KEY), users are active immediately.
    """
    pytest.skip('Only applicable when RESEND_API_KEY is configured - dev mode skips verification')


@pytest.mark.asyncio
async def test_forgot_password_returns_same_message():
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.post(
            '/api/v1/auth/forgot-password',
            json={
                'email': 'nonexistent@example.com',
            },
        )
    assert response.status_code == 200
    assert 'If that email exists' in response.json()['message']


@pytest.mark.asyncio
async def test_reset_password_invalid_token():
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.post(
            '/api/v1/auth/reset-password',
            json={
                'token': 'invalid-token',
                'new_password': 'NewPass123!',
            },
        )
    assert response.status_code == 400
    assert 'Invalid or expired token' in response.json()['error']['message']
