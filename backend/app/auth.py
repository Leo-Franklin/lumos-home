from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(username: str, secret: str, expires_hours: int = 24) -> str:
    expire = datetime.now(UTC) + timedelta(hours=expires_hours)
    return jwt.encode({'sub': username, 'exp': expire}, secret, algorithm='HS256')


def verify_token(token: str, secret: str) -> str | None:
    try:
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        return payload.get('sub')
    except JWTError:
        return None
