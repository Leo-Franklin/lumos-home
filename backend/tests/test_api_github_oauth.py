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
    assert hasattr(GitHubStatusResponse, 'github_id')
    assert hasattr(GitHubStatusResponse, 'bound')
    assert hasattr(OAuthConfigUpdate, 'github_client_id')
    assert hasattr(OAuthConfigUpdate, 'github_client_secret')


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