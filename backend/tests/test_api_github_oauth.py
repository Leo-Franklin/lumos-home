# Tests for GitHub OAuth functionality

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


def test_config_fields():
    """Test that GitHub OAuth config fields exist in settings."""
    from app.config import get_settings
    settings = get_settings()
    assert hasattr(settings, 'github_client_id')
    assert hasattr(settings, 'github_client_secret')


def test_user_github_fields():
    """Test that User model has GitHub-related fields."""
    from app.models.user import User
    assert hasattr(User, 'github_id')
    assert hasattr(User, 'github_username')


def test_binding_token_model():
    """Test that GitHubBindingToken model exists."""
    from app.models.github_binding import GitHubBindingToken
    from app.database import Base
    assert 'github_binding_tokens' in Base.metadata.tables


def test_github_service_token_exchange():
    """Test that GitHubService has required methods."""
    from app.services.github import GitHubService
    assert hasattr(GitHubService, 'exchange_code_for_token')
    assert hasattr(GitHubService, 'get_user_info')


@pytest.mark.asyncio
async def test_github_login_redirects():
    """Test that GitHub login endpoint returns redirect URL."""
    from app.main import app
    from httpx import AsyncClient, ASGITransport

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/api/v1/auth/github/login')
    assert response.status_code == 200
    data = response.json()
    assert 'redirect_url' in data
    assert 'github.com/login/oauth/authorize' in data['redirect_url']


def test_route_registered():
    """Test that GitHub OAuth routes are registered."""
    from app.main import app
    routes = [r.path for r in app.routes]
    assert '/api/v1/auth/github/login' in routes


@pytest.mark.asyncio
async def test_oauth_config_get():
    """Test that OAuth config endpoint returns config without secret."""
    from app.main import app
    from httpx import AsyncClient, ASGITransport

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/api/v1/oauth-config')
    assert response.status_code == 200
    data = response.json()
    assert 'github_client_id' in data
    assert 'github_configured' in data
    assert 'client_secret' not in data


def test_schemas():
    """Test that GitHub-related schemas exist."""
    from app.schemas.auth import GitHubStatusResponse, OAuthConfigUpdate
    assert 'github_id' in GitHubStatusResponse.model_fields
    assert 'bound' in GitHubStatusResponse.model_fields
    assert 'github_client_id' in OAuthConfigUpdate.model_fields
    assert 'github_client_secret' in OAuthConfigUpdate.model_fields


@pytest.mark.asyncio
async def test_full_github_login_flow():
    """Test complete GitHub OAuth login flow with mocks."""
    from unittest.mock import patch, AsyncMock, MagicMock
    from httpx import AsyncClient, ASGITransport

    # Mock GitHub user info
    mock_github_user = MagicMock()
    mock_github_user.github_id = '12345'
    mock_github_user.username = 'testuser'
    mock_github_user.email = 'test@example.com'
    mock_github_user.verified_email = True

    with patch('app.api.github_oauth.get_github_service') as mock_get_service:
        mock_service = MagicMock()
        mock_service.exchange_code_for_token = AsyncMock(return_value='fake_token')
        mock_service.get_user_info = AsyncMock(return_value=mock_github_user)
        mock_get_service.return_value = mock_service

        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            # Step 1: Get login redirect
            response = await client.get('/api/v1/auth/github/login')
            assert response.status_code == 200
            assert 'redirect_url' in response.json()

            # Step 2: Callback with code
            response = await client.get('/api/v1/auth/github/callback', params={
                'code': 'test_code',
                'state': 'test_state',
            })
            # Should return access token for new user
            assert response.status_code == 200
            data = response.json()
            assert 'access_token' in data


@pytest.mark.asyncio
async def test_github_bind_login_user_flow():
    """Authenticated user initiating GitHub binding gets confirmation email."""
    from unittest.mock import patch, AsyncMock, MagicMock

    # Mock GitHub user info
    mock_github_user = MagicMock()
    mock_github_user.github_id = '12345'
    mock_github_user.username = 'testuser'
    mock_github_user.email = 'test@example.com'
    mock_github_user.verified_email = True

    # Mock email service
    mock_email_service = MagicMock()
    mock_email_service.send_binding_confirmation_email = AsyncMock(return_value=True)

    # Mock settings
    mock_settings = MagicMock()
    mock_settings.jwt_secret_key = 'test_secret_key_that_is_at_least_32_characters_long'
    mock_settings.app_base_url = 'http://localhost:5173'

    with patch('app.api.github_oauth.get_github_service') as mock_get_service, \
         patch('app.api.github_oauth.get_email_service', return_value=mock_email_service), \
         patch('app.api.github_oauth.get_settings', return_value=mock_settings):
        mock_service = MagicMock()
        mock_service.exchange_code_for_token = AsyncMock(return_value='fake_token')
        mock_service.get_user_info = AsyncMock(return_value=mock_github_user)
        mock_get_service.return_value = mock_service

        from app.main import app
        from httpx import AsyncClient, ASGITransport

        # Create existing user (logged-in user who wants to bind GitHub)
        from app.auth import hash_password
        from app.models.user import User
        from app.database import _get_session_maker

        async with _get_session_maker()() as session:
            existing = User(
                email='bind_test@example.com',
                password_hash=hash_password('TestPass123!'),
                is_active=True,
                is_superuser=False,
            )
            session.add(existing)
            await session.commit()

        # Get token for this user
        from app.auth import create_access_token
        token = create_access_token('bind_test@example.com', mock_settings.jwt_secret_key)

        # Callback with bind=true and auth header
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            resp = await client.get('/api/v1/auth/github/callback', params={
                'code': 'test_code',
                'state': 'test_state',
                'bind': True,
            }, headers={'Authorization': f'Bearer {token}'})

        assert resp.status_code == 200
        data = resp.json()
        assert 'message' in data
        assert 'confirm' in data.get('message', '').lower()

        # Verify email was sent
        mock_email_service.send_binding_confirmation_email.assert_called()


@pytest.mark.asyncio
async def test_github_bind_without_auth_fails():
    """Binding without Authorization header returns 401."""
    mock_github_user = MagicMock()
    mock_github_user.github_id = '12345'
    mock_github_user.username = 'testuser'
    mock_github_user.email = 'test@example.com'
    mock_github_user.verified_email = True

    mock_email_service = MagicMock()
    mock_email_service.send_binding_confirmation_email = AsyncMock(return_value=True)

    mock_settings = MagicMock()
    mock_settings.jwt_secret_key = 'test_secret_key_that_is_at_least_32_characters_long'
    mock_settings.app_base_url = 'http://localhost:5173'

    with patch('app.api.github_oauth.get_github_service') as mock_get_service, \
         patch('app.api.github_oauth.get_email_service', return_value=mock_email_service), \
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
                'bind': True,
            })

        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_github_bind_already_bound_fails():
    """Binding when user already has github_id returns 400."""
    from app.auth import hash_password
    from app.models.user import User
    from app.database import _get_session_maker

    mock_github_user = MagicMock()
    mock_github_user.github_id = '12345'
    mock_github_user.username = 'testuser'
    mock_github_user.email = 'test@example.com'
    mock_github_user.verified_email = True

    mock_email_service = MagicMock()
    mock_email_service.send_binding_confirmation_email = AsyncMock(return_value=True)

    mock_settings = MagicMock()
    mock_settings.jwt_secret_key = 'test_secret_key_that_is_at_least_32_characters_long'
    mock_settings.app_base_url = 'http://localhost:5173'

    with patch('app.api.github_oauth.get_github_service') as mock_get_service, \
         patch('app.api.github_oauth.get_email_service', return_value=mock_email_service), \
         patch('app.api.github_oauth.get_settings', return_value=mock_settings):
        mock_service = MagicMock()
        mock_service.exchange_code_for_token = AsyncMock(return_value='fake_token')
        mock_service.get_user_info = AsyncMock(return_value=mock_github_user)
        mock_get_service.return_value = mock_service

        # Create user that already has github_id (different email to avoid conflict)
        async with _get_session_maker()() as session:
            existing = User(
                email='already_bound@example.com',
                password_hash=hash_password('TestPass123!'),
                is_active=True,
                is_superuser=False,
                github_id='99999',  # Already has GitHub bound
            )
            session.add(existing)
            await session.commit()

        from app.auth import create_access_token
        token = create_access_token('already_bound@example.com', mock_settings.jwt_secret_key)

        from app.main import app
        from httpx import AsyncClient, ASGITransport

        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            resp = await client.get('/api/v1/auth/github/callback', params={
                'code': 'test_code',
                'state': 'test_state',
                'bind': True,
            }, headers={'Authorization': f'Bearer {token}'})

        assert resp.status_code == 400
        data = resp.json()
        assert 'already bound' in data.get('error', {}).get('message', '').lower()


@pytest.mark.asyncio
async def test_send_binding_confirmation_email():
    """Test that EmailService has send_binding_confirmation_email method with correct behavior."""
    from app.services.email import EmailService, EmailTemplate

    service = EmailService(api_key='test_key', from_email='test@example.com')
    assert hasattr(service, 'send_binding_confirmation_email')
    assert EmailTemplate.BINDING_CONFIRMATION.value == 'binding_confirmation'


@pytest.mark.asyncio
async def test_github_status_bound():
    """GET /auth/github/status returns bound=True with github info when user has github_id."""
    import uuid
    test_id = str(uuid.uuid4())
    from app.auth import create_access_token, hash_password
    from app.models.user import User
    from app.database import _get_session_maker

    async with _get_session_maker()() as session:
        from sqlalchemy import delete
        await session.execute(delete(User).where(User.email == f'bound-{test_id}@example.com'))
        await session.commit()

    async with _get_session_maker()() as session:
        bound_user = User(
            email=f'bound-{test_id}@example.com',
            password_hash=hash_password('TestPass123!'),
            is_active=True,
            is_superuser=False,
            github_id=f'github-bound-{test_id}',
            github_username=f'bounduser-{test_id[:8]}',
        )
        session.add(bound_user)
        await session.commit()

    from app.main import app
    from httpx import AsyncClient, ASGITransport

    token = create_access_token(f'bound-{test_id}@example.com', 'test_secret_key_that_is_at_least_32_characters_long')

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        resp = await client.get('/api/v1/auth/github/status', headers={'Authorization': f'Bearer {token}'})

    assert resp.status_code == 200
    data = resp.json()
    assert data['bound'] is True
    assert data['github_id'] == f'github-bound-{test_id}'
    assert data['github_username'] == f'bounduser-{test_id[:8]}'


@pytest.mark.asyncio
async def test_github_status_not_bound():
    """GET /auth/github/status returns bound=False when user has no github_id."""
    from app.auth import create_access_token, hash_password
    from app.models.user import User
    from app.database import _get_session_maker

    async with _get_session_maker()() as session:
        from sqlalchemy import delete
        await session.execute(delete(User).where(User.email == 'unbound@example.com'))
        await session.commit()

    async with _get_session_maker()() as session:
        unbound_user = User(
            email='unbound@example.com',
            password_hash=hash_password('TestPass123!'),
            is_active=True,
            is_superuser=False,
            github_id=None,
            github_username=None,
        )
        session.add(unbound_user)
        await session.commit()

    from app.main import app
    from httpx import AsyncClient, ASGITransport

    token = create_access_token('unbound@example.com', 'test_secret_key_that_is_at_least_32_characters_long')

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        resp = await client.get('/api/v1/auth/github/status', headers={'Authorization': f'Bearer {token}'})

    assert resp.status_code == 200
    data = resp.json()
    assert data['bound'] is False
    assert data['github_id'] is None
    assert data['github_username'] is None


@pytest.mark.asyncio
async def test_github_status_unauthenticated():
    """GET /auth/github/status returns 401 when no auth header."""
    from app.main import app
    from httpx import AsyncClient, ASGITransport

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        resp = await client.get('/api/v1/auth/github/status')

    assert resp.status_code == 401