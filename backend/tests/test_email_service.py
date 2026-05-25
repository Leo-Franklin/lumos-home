from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_send_verification_email():
    from app.services.email import EmailService

    with patch('httpx.AsyncClient.post') as mock_post:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        service = EmailService(api_key='test_key', from_email='test@resend.dev')
        await service.send_email(
            to='user@example.com',
            subject='Verify',
            body='Click here',
        )
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert 'user@example.com' in str(call_args)


@pytest.mark.asyncio
async def test_send_verification_email_failure():
    import httpx

    from app.services.email import EmailService

    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.side_effect = httpx.HTTPError('Network error')

        service = EmailService(api_key='test_key', from_email='test@resend.dev')
        # Should not raise, just log
        await service.send_email(to='user@example.com', subject='Test', body='Body')
