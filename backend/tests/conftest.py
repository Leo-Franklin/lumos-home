import os

# Use direct assignment (not setdefault) to ensure these values always take effect
os.environ['JWT_SECRET_KEY'] = 'test_secret_key_that_is_at_least_32_characters_long'
os.environ['ADMIN_PASSWORD'] = 'testpassword_for_ci_only'
os.environ['CORS_ALLOW_ORIGINS'] = 'http://localhost:5173'


def pytest_configure(config):
    """Re-assert env vars in case something reset them after module load."""
    os.environ['JWT_SECRET_KEY'] = 'test_secret_key_that_is_at_least_32_characters_long'
    os.environ['ADMIN_PASSWORD'] = 'testpassword_for_ci_only'
    os.environ['CORS_ALLOW_ORIGINS'] = 'http://localhost:5173'
