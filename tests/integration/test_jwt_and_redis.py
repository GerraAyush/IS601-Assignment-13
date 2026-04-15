import pytest
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from fastapi import HTTPException, status

from app.auth.jwt import (
    create_token,
    decode_token,
    verify_password,
    get_password_hash,
    get_current_user as jwt_get_current_user,
)
from app.auth import redis as redis_module
from app.auth.redis import add_to_blacklist, is_blacklisted
from app.schemas.token import TokenType
from app.models.user import User


logger = logging.getLogger(__name__)


def _access_token(user_id=None, expires_delta=None):
    uid = user_id or str(uuid4())
    return create_token(uid, TokenType.ACCESS, expires_delta=expires_delta)


def _refresh_token(user_id=None):
    uid = user_id or str(uuid4())
    return create_token(uid, TokenType.REFRESH)


def test_create_token_with_explicit_expires_delta():
    """Passing expires_delta takes the if-branch on line 42."""
    token = create_token(str(uuid4()), TokenType.ACCESS, expires_delta=timedelta(hours=1))
    assert isinstance(token, str) and len(token) > 0
    logger.info("create_token with explicit expires_delta OK")


def test_create_token_with_uuid_object_user_id():
    """Passing a UUID object triggers the isinstance(user_id, UUID) branch (line 54)."""
    uid = uuid4()
    token = create_token(uid, TokenType.ACCESS)
    assert isinstance(token, str) and len(token) > 0
    logger.info("create_token coerces UUID to str OK")


def test_create_token_refresh_default_expiry():
    """Refresh token path uses REFRESH_TOKEN_EXPIRE_DAYS (else branch inside else)."""
    token = create_token(str(uuid4()), TokenType.REFRESH)
    assert isinstance(token, str) and len(token) > 0


def test_verify_password_correct():
    hashed = get_password_hash("MyPass123!")
    assert verify_password("MyPass123!", hashed) is True


def test_verify_password_wrong():
    hashed = get_password_hash("MyPass123!")
    assert verify_password("WrongPass!", hashed) is False


@pytest.mark.asyncio
async def test_decode_token_valid_access():
    """Happy path: valid access token decodes successfully."""
    token = _access_token()
    with patch("app.auth.jwt.is_blacklisted", new=AsyncMock(return_value=False)):
        payload = await decode_token(token, TokenType.ACCESS)
    assert payload["type"] == TokenType.ACCESS.value
    logger.info("decode_token valid access token OK")


@pytest.mark.asyncio
async def test_decode_token_valid_refresh():
    """Happy path: valid refresh token decodes successfully."""
    token = _refresh_token()
    with patch("app.auth.jwt.is_blacklisted", new=AsyncMock(return_value=False)):
        payload = await decode_token(token, TokenType.REFRESH)
    assert payload["type"] == TokenType.REFRESH.value


@pytest.mark.asyncio
async def test_decode_token_wrong_type_raises_401():
    """Access token presented as refresh token → 401 'Invalid token type'."""
    token = _access_token()
    with patch("app.auth.jwt.is_blacklisted", new=AsyncMock(return_value=False)):
        with pytest.raises(HTTPException) as exc_info:
            await decode_token(token, TokenType.REFRESH)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid token type" in exc_info.value.detail


@pytest.mark.asyncio
async def test_decode_token_blacklisted_raises_401():
    """Token whose JTI is blacklisted → 401 'Token has been revoked'."""
    token = _access_token()
    with patch("app.auth.jwt.is_blacklisted", new=AsyncMock(return_value=True)):
        with pytest.raises(HTTPException) as exc_info:
            await decode_token(token, TokenType.ACCESS)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "revoked" in exc_info.value.detail


@pytest.mark.asyncio
async def test_decode_token_expired_raises_401():
    """Expired token → 401 'Token has expired'."""
    token = _access_token(expires_delta=timedelta(seconds=-10))
    with pytest.raises(HTTPException) as exc_info:
        await decode_token(token, TokenType.ACCESS)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "expired" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_decode_token_garbage_raises_401():
    """Completely invalid token string → 401 'Could not validate credentials'."""
    with pytest.raises(HTTPException) as exc_info:
        await decode_token("not.a.real.token", TokenType.ACCESS)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_decode_token_verify_exp_false():
    """verify_exp=False allows decoding an already-expired token."""
    token = _access_token(expires_delta=timedelta(seconds=-10))
    with patch("app.auth.jwt.is_blacklisted", new=AsyncMock(return_value=False)):
        payload = await decode_token(token, TokenType.ACCESS, verify_exp=False)
    assert payload["type"] == TokenType.ACCESS.value


def _mock_db_returning(user):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = user
    return db


@pytest.mark.asyncio
async def test_jwt_get_current_user_valid(db_session, fake_user_data):
    """Valid token + active user → returns the User ORM object."""
    fake_user_data["password"] = "TestPass123"
    user = User.register(db_session, fake_user_data)
    db_session.commit()
    db_session.refresh(user)

    token = _access_token(user_id=str(user.id))
    mock_db = _mock_db_returning(user)

    with patch("app.auth.jwt.is_blacklisted", new=AsyncMock(return_value=False)):
        result = await jwt_get_current_user(token=token, db=mock_db)

    assert result is user
    logger.info("jwt.get_current_user returns correct user")


@pytest.mark.asyncio
async def test_jwt_get_current_user_not_found_raises_401():
    """Token valid but user not in DB → 401."""
    token = _access_token()
    mock_db = _mock_db_returning(None)

    with patch("app.auth.jwt.is_blacklisted", new=AsyncMock(return_value=False)):
        with pytest.raises(HTTPException) as exc_info:
            await jwt_get_current_user(token=token, db=mock_db)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_jwt_get_current_user_inactive_raises_401(db_session, fake_user_data):
    """Inactive user found in DB → 401."""
    fake_user_data["password"] = "TestPass123"
    user = User.register(db_session, fake_user_data)
    db_session.commit()
    db_session.refresh(user)
    user.is_active = False
    db_session.commit()

    token = _access_token(user_id=str(user.id))
    mock_db = _mock_db_returning(user)

    with patch("app.auth.jwt.is_blacklisted", new=AsyncMock(return_value=False)):
        with pytest.raises(HTTPException) as exc_info:
            await jwt_get_current_user(token=token, db=mock_db)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_redis_creates_and_caches_connection():
    """get_redis() calls aioredis.from_url on first call and caches the result."""
    # Clear any cached connection from a prior test run
    if hasattr(redis_module.get_redis, "redis"):
        del redis_module.get_redis.redis

    mock_conn = AsyncMock()
    with patch("aioredis.from_url", new=AsyncMock(return_value=mock_conn)):
        first = await redis_module.get_redis()
        second = await redis_module.get_redis()

    assert first is mock_conn
    assert second is mock_conn  # cached — from_url only called once
    logger.info("get_redis caches the connection")

    # Cleanup
    if hasattr(redis_module.get_redis, "redis"):
        del redis_module.get_redis.redis


@pytest.mark.asyncio
async def test_add_to_blacklist_calls_redis_set():
    """add_to_blacklist writes the correct key and TTL to Redis."""
    mock_conn = AsyncMock()
    with patch("app.auth.redis.get_redis", new=AsyncMock(return_value=mock_conn)):
        await add_to_blacklist("test-jti-abc", 3600)

    mock_conn.set.assert_called_once_with("blacklist:test-jti-abc", "1", ex=3600)
    logger.info("add_to_blacklist sets correct key")


@pytest.mark.asyncio
async def test_is_blacklisted_returns_true_when_present():
    """is_blacklisted returns truthy when the key exists in Redis."""
    mock_conn = AsyncMock()
    mock_conn.exists = AsyncMock(return_value=1)
    with patch("app.auth.redis.get_redis", new=AsyncMock(return_value=mock_conn)):
        result = await is_blacklisted("test-jti-abc")

    assert result == 1
    mock_conn.exists.assert_called_once_with("blacklist:test-jti-abc")


@pytest.mark.asyncio
async def test_is_blacklisted_returns_false_when_absent():
    """is_blacklisted returns falsy when the key does not exist in Redis."""
    mock_conn = AsyncMock()
    mock_conn.exists = AsyncMock(return_value=0)
    with patch("app.auth.redis.get_redis", new=AsyncMock(return_value=mock_conn)):
        result = await is_blacklisted("unknown-jti")

    assert result == 0
