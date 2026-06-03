from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_send_verification_email():
    from app.services.email import EmailService

    with patch('app.services.email.httpx') as mock_httpx:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_httpx.AsyncClient.return_value = mock_client

        service = EmailService(api_key='test_key', from_email='test@resend.dev')
        await service.send_email(
            to='user@example.com',
            subject='Verify',
            body='Click here',
        )
        mock_httpx.AsyncClient.return_value.post.assert_called_once()
        call_args = mock_httpx.AsyncClient.return_value.post.call_args
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
