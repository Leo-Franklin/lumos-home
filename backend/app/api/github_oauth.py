import secrets
import uuid
from datetime import datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, verify_token
from app.config import get_settings
from app.database import get_db
from app.deps import DBDep
from app.models.github_binding import GitHubBindingToken
from app.models.user import User
from app.schemas.auth import GitHubStatusResponse, MessageResponse
from app.services.email import get_email_service
from app.services.github import GitHubUserInfo, get_github_service

router = APIRouter(prefix='/auth/github', tags=['auth'])


def generate_state() -> str:
    return secrets.token_urlsafe(32)


@router.get('/login')
async def github_login(bind: bool = Query(False)):
    """Redirect to GitHub authorization page."""
    github_service = get_github_service()
    if not github_service:
        raise HTTPException(status_code=503, detail='GitHub OAuth not configured')

    state = generate_state()
    params = {
        'client_id': github_service.client_id,
        'redirect_uri': f'{get_settings().app_base_url}/api/v1/auth/github/callback',
        'scope': 'read:user',
        'state': state,
    }
    auth_url = f'https://github.com/login/oauth/authorize?{urlencode(params)}'
    return {'redirect_url': auth_url, 'state': state}


@router.get('/callback')
async def github_callback(
    code: str = Query(...),
    state: str = Query(...),
    bind: bool = Query(False),
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Handle GitHub OAuth callback."""
    github_service = get_github_service()
    if not github_service:
        raise HTTPException(status_code=503, detail='GitHub OAuth not configured')

    access_token = await github_service.exchange_code_for_token(code)
    if not access_token:
        raise HTTPException(status_code=400, detail='Failed to exchange code for token')

    user_info = await github_service.get_user_info(access_token)
    if not user_info:
        raise HTTPException(status_code=400, detail='Failed to get user info from GitHub')

    if not user_info.verified_email:
        raise HTTPException(status_code=400, detail='No verified email from GitHub')

    result = await db.execute(select(User).where(User.github_id == user_info.github_id))
    existing_user = result.scalar_one_or_none()

    if bind:
        # Binding mode - requires logged-in user
        if not authorization:
            raise HTTPException(status_code=401, detail='Authentication required for account binding')

        settings = get_settings()
        if not authorization.startswith('Bearer '):
            raise HTTPException(status_code=401, detail='Invalid authorization header')
        token = authorization[7:]
        email = verify_token(token, settings.jwt_secret_key)
        if not email:
            raise HTTPException(status_code=401, detail='Invalid or expired token')

        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail='User not found')

        if user.github_id:
            raise HTTPException(status_code=400, detail='GitHub account already bound')

        # Create binding token and send confirmation email
        token = str(uuid.uuid4())
        binding_token = GitHubBindingToken(
            token=token,
            user_id=user.id,
            github_id=user_info.github_id,
            github_username=user_info.username,
            github_email=user_info.email,
            expires_at=datetime.now() + timedelta(minutes=15),
        )
        db.add(binding_token)
        await db.commit()

        email_service = get_email_service()
        await email_service.send_binding_confirmation_email(
            to=user_info.email,
            username=user_info.username,
            token=token,
            base_url=settings.app_base_url,
        )
        return {'message': 'Please check your email to confirm GitHub binding'}
    else:
        # Login mode
        if existing_user:
            settings = get_settings()
            token = create_access_token(existing_user.email, settings.jwt_secret_key)
            return {'access_token': token, 'token_type': 'bearer'}
        else:
            result = await db.execute(select(User).where(User.email == user_info.email))
            existing_by_email = result.scalar_one_or_none()

            if existing_by_email and not existing_by_email.github_id:
                # Email exists but not bound to GitHub - need confirmation
                settings = get_settings()
                token = str(uuid.uuid4())
                binding_token = GitHubBindingToken(
                    token=token,
                    user_id=existing_by_email.id,
                    github_id=user_info.github_id,
                    github_username=user_info.username,
                    github_email=user_info.email,
                    expires_at=datetime.now() + timedelta(minutes=15),
                )
                db.add(binding_token)
                await db.commit()

                # Send confirmation email
                email_service = get_email_service()
                await email_service.send_binding_confirmation_email(
                    to=user_info.email,
                    username=user_info.username,
                    token=token,
                    base_url=settings.app_base_url,
                )
                return {'message': 'Please check your email to confirm binding'}
            else:
                # Create new user
                new_user = User(
                    email=user_info.email,
                    password_hash='',
                    is_active=True,
                    is_superuser=False,
                    github_id=user_info.github_id,
                    github_username=user_info.username,
                )
                db.add(new_user)
                await db.commit()
                settings = get_settings()
                token = create_access_token(new_user.email, settings.jwt_secret_key)
                return {'access_token': token, 'token_type': 'bearer'}


@router.get('/bind/verify')
async def github_bind_verify(token: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Verify binding token and complete binding."""
    result = await db.execute(
        select(GitHubBindingToken).where(GitHubBindingToken.token == token)
    )
    binding_token = result.scalar_one_or_none()

    if not binding_token or binding_token.expires_at < datetime.now():
        raise HTTPException(status_code=400, detail='Invalid or expired token')

    result = await db.execute(select(User).where(User.id == binding_token.user_id))
    user = result.scalar_one_or_none()

    if user:
        user.github_id = binding_token.github_id
        user.github_username = binding_token.github_username
        await db.delete(binding_token)
        await db.commit()

    return MessageResponse(message='GitHub account bound successfully')


@router.get('/status', response_model=GitHubStatusResponse)
async def github_status(
    db: DBDep,
    authorization: str | None = Header(None),
):
    """Get current user's GitHub binding status."""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Authentication required')

    from app.auth import verify_token
    from app.config import get_settings
    settings = get_settings()

    token = authorization[7:]
    email = verify_token(token, settings.jwt_secret_key)
    if not email:
        raise HTTPException(status_code=401, detail='Invalid or expired token')

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail='User not found')

    return GitHubStatusResponse(
        github_id=user.github_id,
        github_username=user.github_username,
        bound=user.github_id is not None,
    )


@router.delete('/unbind', response_model=MessageResponse)
async def github_unbind(
    db: DBDep,
    authorization: str | None = Header(None),
):
    """Unbind GitHub account from user account."""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Authentication required')

    from app.auth import verify_token
    from app.config import get_settings
    settings = get_settings()

    token = authorization[7:]
    email = verify_token(token, settings.jwt_secret_key)
    if not email:
        raise HTTPException(status_code=401, detail='Invalid or expired token')

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail='User not found')

    if not user.github_id:
        raise HTTPException(status_code=400, detail='GitHub account not bound')

    user.github_id = None
    user.github_username = None
    await db.commit()

    return MessageResponse(message='GitHub account unlinked successfully')
