import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock, MagicMock
import uuid


@pytest.fixture
def mock_email_service():
    mock = MagicMock()
    mock.send_verification_email = AsyncMock(return_value=True)
    mock.send_password_reset_email = AsyncMock(return_value=True)
    return mock


@pytest.mark.asyncio
async def test_register_success(mock_email_service):
    email = f'newuser-{uuid.uuid4()}@example.com'
    with patch('app.api.auth.get_email_service', return_value=mock_email_service), \
         patch('app.api.auth.hash_password') as mock_hash, \
         patch('app.api.auth.get_settings') as mock_settings:
        mock_hash.return_value = '$2b$12$LQv3c1yqBWV9kZN7t8pMGOKmRj9pVxD9y5xY7zX8J2K4L5M6N7O8P9Q0R'
        mock_settings.return_value.resend_api_key = ''  # Dev mode - no email verification

        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            response = await client.post('/api/v1/auth/register', json={
                'email': email,
                'password': 'StrongPass123!',
            })
        assert response.status_code == 201
        data = response.json()
        # In dev mode (no RESEND_API_KEY), user is active immediately
        assert data['message'] == 'Registration successful. You can now login.'
        assert data['email'] == email


@pytest.mark.asyncio
async def test_register_duplicate_email(mock_email_service):
    email = f'dup-{uuid.uuid4()}@example.com'
    with patch('app.api.auth.get_email_service', return_value=mock_email_service), \
         patch('app.api.auth.hash_password') as mock_hash:
        mock_hash.return_value = '$2b$12$LQv3c1yqBWV9kZN7t8pMGOKmRj9pVxD9y5xY7zX8J2K4L5M6N7O8P9Q0R'

        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            # Register first user
            await client.post('/api/v1/auth/register', json={
                'email': email,
                'password': 'StrongPass123!',
            })
            # Try duplicate
            response = await client.post('/api/v1/auth/register', json={
                'email': email,
                'password': 'AnotherPass123!',
            })
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
        response = await client.post('/api/v1/auth/forgot-password', json={
            'email': 'nonexistent@example.com',
        })
    assert response.status_code == 200
    assert 'If that email exists' in response.json()['message']


@pytest.mark.asyncio
async def test_reset_password_invalid_token():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.post('/api/v1/auth/reset-password', json={
            'token': 'invalid-token',
            'new_password': 'NewPass123!',
        })
    assert response.status_code == 400
    assert 'Invalid or expired token' in response.json()['error']['message']


@pytest.mark.asyncio
async def test_github_bind_existing_email_sends_confirmation():
    """When GitHub email matches existing unbinded user, confirmation email must be sent."""
    from unittest.mock import patch, AsyncMock, MagicMock
    from app.auth import hash_password
    from app.models.user import User
    from app.database import _get_session_maker

    # Clean up any existing test data first
    async with _get_session_maker()() as session:
        from sqlalchemy import delete
        await session.execute(delete(User).where(User.email == 'existing@example.com'))
        await session.commit()

    mock_github_user = MagicMock()
    mock_github_user.github_id = '99999'
    mock_github_user.username = 'githubuser'
    mock_github_user.email = 'existing@example.com'
    mock_github_user.verified_email = True

    mock_email = MagicMock()
    mock_email.send_binding_confirmation_email = AsyncMock(return_value=True)

    mock_settings = MagicMock()
    mock_settings.jwt_secret_key = 'test_secret_key_that_is_at_least_32_characters_long'
    mock_settings.app_base_url = 'http://localhost:5173'

    # Create existing user with email but no github_id BEFORE the callback
    async with _get_session_maker()() as session:
        existing = User(
            email='existing@example.com',
            password_hash=hash_password('TestPass123!'),
            is_active=True,
            is_superuser=False,
            github_id=None,  # Not bound to GitHub
        )
        session.add(existing)
        await session.commit()

    with patch('app.api.github_oauth.get_github_service') as mock_get_service, \
         patch('app.api.github_oauth.get_email_service', return_value=mock_email), \
         patch('app.api.github_oauth.get_settings', return_value=mock_settings):
        mock_service = MagicMock()
        mock_service.exchange_code_for_token = AsyncMock(return_value='fake_token')
        mock_service.get_user_info = AsyncMock(return_value=mock_github_user)
        mock_get_service.return_value = mock_service

        from app.main import app
        from httpx import AsyncClient, ASGITransport

        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            resp = await client.get('/api/v1/auth/github/callback', params={
                'code': 'test_code',
                'state': 'test_state',
                'bind': False,
            })

        assert resp.status_code == 200
        data = resp.json()
        assert 'message' in data
        assert 'confirm' in data['message'].lower() or 'email' in data

        # Verify email was sent
        mock_email.send_binding_confirmation_email.assert_called()

    # Cleanup
    async with _get_session_maker()() as session:
        from sqlalchemy import delete
        await session.execute(delete(User).where(User.email == 'existing@example.com'))
        await session.commit()