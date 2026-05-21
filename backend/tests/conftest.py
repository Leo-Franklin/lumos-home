import os

os.environ.setdefault('JWT_SECRET_KEY', 'test_secret_key_that_is_at_least_32_characters_long')
os.environ.setdefault('ADMIN_PASSWORD', 'testpassword_for_ci_only')
os.environ.setdefault('CORS_ALLOW_ORIGINS', 'http://localhost:5173')