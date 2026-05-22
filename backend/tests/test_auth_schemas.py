import pytest
from pydantic import ValidationError
from app.schemas.auth import RegisterRequest, LoginRequest, VerifyEmailRequest, ForgotPasswordRequest, ResetPasswordRequest


def test_register_request_valid():
    req = RegisterRequest(email='test@example.com', password='StrongPass123!')
    assert req.email == 'test@example.com'
    assert req.password == 'StrongPass123!'


def test_register_request_invalid_email():
    with pytest.raises(ValidationError):
        RegisterRequest(email='not-an-email', password='StrongPass123!')


def test_register_request_short_password():
    with pytest.raises(ValidationError):
        RegisterRequest(email='test@example.com', password='short')


def test_login_request():
    req = LoginRequest(email='test@example.com', password='pass123', remember_me=True)
    assert req.remember_me is True


def test_forgot_password_request():
    req = ForgotPasswordRequest(email='test@example.com')
    assert req.email == 'test@example.com'


def test_reset_password_request():
    req = ResetPasswordRequest(token='some-uuid-token', new_password='NewPass123!')
    assert req.token == 'some-uuid-token'
    assert req.new_password == 'NewPass123!'


def test_reset_password_short():
    with pytest.raises(ValidationError):
        ResetPasswordRequest(token='some-uuid-token', new_password='short')
