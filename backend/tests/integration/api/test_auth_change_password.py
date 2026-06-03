"""Integration tests for POST /auth/change-password.

Covers:
- success: valid current_password + new_password updates the hash, old password rejected
- wrong current password: 401
- missing auth: 401
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient


def _unique_email() -> str:
    return f'test-{uuid.uuid4()}@example.com'


async def _create_active_user(password: str = 'OldPass123!') -> tuple[str, str]:
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


async def _login(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post(
        '/api/v1/auth/login', json={'email': email, 'password': password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()['access_token']


@pytest.mark.asyncio
async def test_change_password_success():
    email, old_password = await _create_active_user('OldPass123!')
    new_password = 'NewPass456!'

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        token = await _login(client, email, old_password)
        resp = await client.post(
            '/api/v1/auth/change-password',
            json={'current_password': old_password, 'new_password': new_password},
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()['message'] == 'Password updated.'

        # Old password no longer works
        bad = await client.post(
            '/api/v1/auth/login', json={'email': email, 'password': old_password}
        )
        assert bad.status_code == 401

        # New password works
        ok = await client.post(
            '/api/v1/auth/login', json={'email': email, 'password': new_password}
        )
        assert ok.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_current():
    email, old_password = await _create_active_user('OldPass123!')

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        token = await _login(client, email, old_password)
        resp = await client.post(
            '/api/v1/auth/change-password',
            json={'current_password': 'WrongCurrent1!', 'new_password': 'NewPass456!'},
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 401
        assert 'current' in resp.json()['error']['message'].lower() or 'incorrect' in resp.json()['error']['message'].lower()


@pytest.mark.asyncio
async def test_change_password_unauthenticated():
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        resp = await client.post(
            '/api/v1/auth/change-password',
            json={'current_password': 'x', 'new_password': 'NewPass456!'},
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_change_password_too_short():
    email, old_password = await _create_active_user('OldPass123!')

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        token = await _login(client, email, old_password)
        resp = await client.post(
            '/api/v1/auth/change-password',
            json={'current_password': old_password, 'new_password': 'short'},
            headers={'Authorization': f'Bearer {token}'},
        )
        # 422 from Pydantic validator
        assert resp.status_code == 422
