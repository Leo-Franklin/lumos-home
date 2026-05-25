import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class GitHubUserInfo:
    github_id: str
    username: str
    email: str | None
    verified_email: bool


class GitHubService:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = 'https://github.com'
        self.api_url = 'https://api.github.com'

    async def exchange_code_for_token(self, code: str) -> str | None:
        """Exchange authorization code for access token."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f'{self.base_url}/login/oauth/access_token',
                    headers={'Accept': 'application/json'},
                    data={
                        'client_id': self.client_id,
                        'client_secret': self.client_secret,
                        'code': code,
                    },
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                return data.get('access_token')
            except httpx.HTTPError as e:
                logger.error(f'GitHub token exchange failed: {e}')
                return None

    async def get_user_info(self, access_token: str) -> GitHubUserInfo | None:
        """Get user info from GitHub API."""
        async with httpx.AsyncClient() as client:
            try:
                # Get user details
                user_response = await client.get(
                    f'{self.api_url}/user',
                    headers={'Authorization': f'Bearer {access_token}'},
                    timeout=10.0,
                )
                user_response.raise_for_status()
                user_data = user_response.json()

                # Get emails (to find verified email)
                email_response = await client.get(
                    f'{self.api_url}/user/emails',
                    headers={'Authorization': f'Bearer {access_token}'},
                    timeout=10.0,
                )
                emails_data = email_response.json() if email_response.status_code == 200 else []

                # Find primary verified email
                verified_email = None
                for email in emails_data:
                    if email.get('verified') and email.get('primary'):
                        verified_email = email.get('email')
                        break

                return GitHubUserInfo(
                    github_id=str(user_data['id']),
                    username=user_data.get('login', ''),
                    email=verified_email,
                    verified_email=verified_email is not None,
                )
            except (httpx.HTTPError, KeyError) as e:
                logger.error(f'GitHub user info fetch failed: {e}')
                return None


_github_service: GitHubService | None = None


def get_github_service() -> GitHubService | None:
    global _github_service
    if _github_service is None:
        from app.config import get_settings
        settings = get_settings()
        if settings.github_client_id and settings.github_client_secret:
            _github_service = GitHubService(
                settings.github_client_id,
                settings.github_client_secret,
            )
    return _github_service