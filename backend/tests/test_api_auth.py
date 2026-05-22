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
         patch('app.api.auth.hash_password') as mock_hash:
        mock_hash.return_value = '$2b$12$LQv3c1yqBWV9kZN7t8pMGOKmRj9pVxD9y5xY7zX8J2K4L5M6N7O8P9Q0R'

        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            response = await client.post('/api/v1/auth/register', json={
                'email': email,
                'password': 'StrongPass123!',
            })
        assert response.status_code == 201
        data = response.json()
        assert data['message'] == 'Verification email sent. Please check your inbox.'
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

    With the new auth.py /auth/login (JSON body with email/password),
    an unverified user gets 403 (email not verified).
    """
    email = f'unverified-{uuid.uuid4()}@example.com'
    with patch('app.api.auth.get_email_service', return_value=mock_email_service), \
         patch('app.api.auth.hash_password') as mock_hash, \
         patch('app.api.auth.verify_password', return_value=True):
        mock_hash.return_value = '$2b$12$LQv3c1yqBWV9kZN7t8pMGOKmRj9pVxD9y5xY7zX8J2K4L5M6N7O8P9Q0R'

        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            # Register user (unverified)
            await client.post('/api/v1/auth/register', json={
                'email': email,
                'password': 'StrongPass123!',
            })
            # Try login with JSON body (auth.py LoginRequest)
            response = await client.post('/api/v1/auth/login', json={
                'email': email,
                'password': 'StrongPass123!',
            })
        # New auth.py login returns 403 for unverified users
        assert response.status_code == 403


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