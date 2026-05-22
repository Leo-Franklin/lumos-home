from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear lru_cache before and after each test to ensure monkeypatch env vars take effect."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def test_env(monkeypatch):
    """Set required env vars for tests and clear cache."""
    monkeypatch.setenv('JWT_SECRET_KEY', 'test_secret_key_that_is_at_least_32_characters_long')
    monkeypatch.setenv('ADMIN_PASSWORD', 'testpassword_for_ci_only')
    monkeypatch.setenv('CORS_ALLOW_ORIGINS', 'http://localhost:5173')
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_health():
    mock_nas = MagicMock()
    mock_nas.check_writable.return_value = True
    app.state.nas_syncer = mock_nas
    with patch('app.api.system._check_ffmpeg', return_value=True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            resp = await client.get('/api/v1/health')
    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'healthy'
    assert 'uptime_seconds' in data


@pytest.mark.asyncio
async def test_login_success(test_env):
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.user import User

    # Create admin user for login test
    async with AsyncSessionLocal() as db:
        # Check if user already exists to avoid UNIQUE constraint failures on re-run
        result = await db.execute(select(User).where(User.email == 'admin@test.com'))
        if result.scalar_one_or_none() is None:
            admin = User(
                email='admin@test.com',
                password_hash='$2b$12$LQv3c1yqBWV9kZN7t8pMGOKmRj9pVxD9y5xY7zX8J2K4L5M6N7O8P9Q0R',
                is_active=True,
                is_superuser=False,
            )
            db.add(admin)
            await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        with patch('app.api.auth.verify_password', return_value=True):
            resp = await client.post(
                '/api/v1/auth/login',
                json={'email': 'admin@test.com', 'password': 'testpassword_for_ci_only'},
            )
    assert resp.status_code == 200
    assert 'access_token' in resp.json()


@pytest.mark.asyncio
async def test_login_fail():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        resp = await client.post(
            '/api/v1/auth/login',
            json={'email': 'nonexistent@example.com', 'password': 'wrong'},
        )
    assert resp.status_code == 401
