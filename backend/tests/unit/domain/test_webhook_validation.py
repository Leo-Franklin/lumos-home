import pytest

from app.domain.services.webhook_validation import validate_webhook_url


def test_validate_webhook_url_accepts_https_domain():
    validate_webhook_url('https://hooks.example.com/notify')


def test_validate_webhook_url_rejects_http():
    with pytest.raises(ValueError, match='https'):
        validate_webhook_url('http://hooks.example.com/notify')


def test_validate_webhook_url_rejects_private_ip():
    with pytest.raises(ValueError, match='内网'):
        validate_webhook_url('https://192.168.1.1/hook')


def test_validate_webhook_url_rejects_invalid_url():
    with pytest.raises(ValueError, match='无效'):
        validate_webhook_url('https://')
