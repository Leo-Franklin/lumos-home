import logging
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class EmailTemplate(Enum):
    VERIFY_EMAIL = 'verify_email'
    PASSWORD_RESET = 'password_reset'


class EmailService:
    def __init__(self, api_key: str, from_email: str):
        self.api_key = api_key
        self.from_email = from_email
        self.base_url = 'https://api.resend.com/emails'

    async def send_email(self, to: str, subject: str, body: str) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        'Authorization': f'Bearer {self.api_key}',
                        'Content-Type': 'application/json',
                    },
                    json={
                        'from': self.from_email,
                        'to': [to],
                        'subject': subject,
                        'html': f'<p>{body}</p>',
                    },
                    timeout=10.0,
                )
                response.raise_for_status()
                return True
        except httpx.HTTPError as e:
            logger.error(f'Failed to send email to {to}: {e}')
            return False

    async def send_verification_email(self, to: str, token: str, base_url: str) -> bool:
        verify_url = f'{base_url}/api/v1/auth/verify-email?token={token}'
        body = f"""
        Hi,<br/><br/>
        Please click the link below to verify your email address:<br/>
        <a href="{verify_url}">{verify_url}</a><br/><br/>
        This link expires in 24 hours.<br/><br/>
        If you didn't create an account, please ignore this email.
        """
        return await self.send_email(
            to=to,
            subject='Verify your email - Smart Home',
            body=body,
        )

    async def send_password_reset_email(self, to: str, token: str, base_url: str) -> bool:
        reset_url = f'{base_url}/api/v1/auth/reset-password?token={token}'
        body = f"""
        Hi,<br/><br/>
        You requested a password reset. Click the link below to set a new password:<br/>
        <a href="{reset_url}">{reset_url}</a><br/><br/>
        This link expires in 15 minutes.<br/><br/>
        If you didn't request this, please ignore this email.
        """
        return await self.send_email(
            to=to,
            subject='Reset your password - Smart Home',
            body=body,
        )


_email_service: EmailService | None = None


def get_email_service() -> EmailService:
    global _email_service
    if _email_service is None:
        from app.config import get_settings
        settings = get_settings()
        _email_service = EmailService(
            api_key=settings.resend_api_key,
            from_email=settings.resend_from_email,
        )
    return _email_service