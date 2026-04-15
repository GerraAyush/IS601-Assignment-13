import logging
from datetime import datetime, timezone
from uuid import uuid4

from app.models.user import User


logger = logging.getLogger(__name__)

def test_authenticate_wrong_password_returns_none(db_session, fake_user_data):
    """authenticate() returns None when password is wrong (line 160)."""
    fake_user_data["password"] = "TestPass123"
    User.register(db_session, fake_user_data)
    db_session.commit()

    result = User.authenticate(db_session, fake_user_data["username"], "WrongPass!")
    assert result is None
    logger.info("authenticate with wrong password returns None")


def test_authenticate_unknown_user_returns_none(db_session):
    """authenticate() returns None for a username that does not exist (line 160)."""
    result = User.authenticate(db_session, "no_such_user_xyz", "AnyPass123!")
    assert result is None


def test_verify_token_no_sub_returns_none():
    """Token payload missing 'sub' → verify_token returns None (line 226)."""
    from jose import jwt as jose_jwt
    from app.core.config import settings

    token = jose_jwt.encode(
        {"exp": datetime.now(timezone.utc).timestamp() + 3600},
        settings.JWT_SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    result = User.verify_token(token)
    assert result is None
    logger.info("verify_token with no sub field returns None")


def test_verify_token_non_uuid_sub_returns_none():
    """Token sub that is not a valid UUID → verify_token returns None (line 229)."""
    from jose import jwt as jose_jwt
    from app.core.config import settings

    token = jose_jwt.encode(
        {"sub": "not-a-uuid-at-all", "exp": datetime.now(timezone.utc).timestamp() + 3600},
        settings.JWT_SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    result = User.verify_token(token)
    assert result is None
    logger.info("verify_token with non-UUID sub returns None")


def test_verify_token_jwt_error_returns_none():
    """Completely invalid token string causes JWTError → returns None (line 230)."""
    result = User.verify_token("garbage.token.value")
    assert result is None


def test_create_refresh_token_returns_string(fake_user_data):
    """User.create_refresh_token returns a non-empty JWT string."""
    token = User.create_refresh_token({"sub": str(uuid4())})
    assert isinstance(token, str) and len(token) > 0
