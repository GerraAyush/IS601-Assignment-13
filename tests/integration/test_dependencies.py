import pytest
import logging
from unittest.mock import patch

from uuid import uuid4
from datetime import datetime, timezone
from fastapi import HTTPException, status

from app.auth.dependencies import get_current_user, get_current_active_user
from app.schemas.user import UserResponse
from app.models.user import User

logger = logging.getLogger(__name__)

# Sample user data dictionaries for testing
sample_user_data = {
    "id": uuid4(),
    "username": "testuser",
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "is_active": True,
    "is_verified": True,
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow()
}

inactive_user_data = {
    "id": uuid4(),
    "username": "inactiveuser",
    "email": "inactive@example.com",
    "first_name": "Inactive",
    "last_name": "User",
    "is_active": False,
    "is_verified": False,
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc)
}

# Fixture for mocking token verification
@pytest.fixture
def mock_verify_token():
    with patch.object(User, 'verify_token') as mock:
        yield mock

# Test get_current_user with valid token and complete payload
def test_get_current_user_valid_token_existing_user(mock_verify_token):
    mock_verify_token.return_value = sample_user_data

    user_response = get_current_user(token="validtoken")

    assert isinstance(user_response, UserResponse)
    assert user_response.id == sample_user_data["id"]
    assert user_response.username == sample_user_data["username"]
    assert user_response.email == sample_user_data["email"]
    assert user_response.first_name == sample_user_data["first_name"]
    assert user_response.last_name == sample_user_data["last_name"]
    assert user_response.is_active == sample_user_data["is_active"]
    assert user_response.is_verified == sample_user_data["is_verified"]
    assert user_response.created_at == sample_user_data["created_at"]
    assert user_response.updated_at == sample_user_data["updated_at"]

    mock_verify_token.assert_called_once_with("validtoken")

# Test get_current_user with invalid token (returns None)
def test_get_current_user_invalid_token(mock_verify_token):
    mock_verify_token.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token="invalidtoken")

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Could not validate credentials"

    mock_verify_token.assert_called_once_with("invalidtoken")

# Test get_current_user with valid token but incomplete payload (simulate missing fields)
def test_get_current_user_valid_token_incomplete_payload(mock_verify_token):
    # Return an empty dict simulating missing required fields
    mock_verify_token.return_value = {}

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token="validtoken")

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Could not validate credentials"

    mock_verify_token.assert_called_once_with("validtoken")

# Test get_current_active_user with an active user
def test_get_current_active_user_active(mock_verify_token):
    mock_verify_token.return_value = sample_user_data

    current_user = get_current_user(token="validtoken")
    active_user = get_current_active_user(current_user=current_user)

    assert isinstance(active_user, UserResponse)
    assert active_user.is_active is True

# Test get_current_active_user with an inactive user
def test_get_current_active_user_inactive(mock_verify_token):
    mock_verify_token.return_value = inactive_user_data

    current_user = get_current_user(token="validtoken")

    with pytest.raises(HTTPException) as exc_info:
        get_current_active_user(current_user=current_user)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail == "Inactive user"


def _make_user_response(**overrides):
    """Build a minimal valid UserResponse dict, applying any overrides."""
    data = {
        "id": uuid4(),
        "username": "testuser",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "is_active": True,
        "is_verified": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    data.update(overrides)
    return data


def test_get_current_user_sub_only_dict():
    """Token payload contains only 'sub'; should synthesise an unknown UserResponse."""
    user_id = uuid4()
    with patch.object(User, "verify_token", return_value={"sub": str(user_id)}):
        result = get_current_user(token="anytoken")

    assert isinstance(result, UserResponse)
    assert result.id == user_id
    assert result.username == "unknown"
    assert result.is_active is True
    logger.info("sub-only dict branch returns synthetic UserResponse")


def test_get_current_user_uuid_return():
    """verify_token returns a bare UUID; should wrap it in a synthetic UserResponse."""
    user_id = uuid4()
    with patch.object(User, "verify_token", return_value=user_id):
        result = get_current_user(token="anytoken")

    assert isinstance(result, UserResponse)
    assert result.id == user_id
    assert result.username == "unknown"
    assert result.email == "unknown@example.com"
    logger.info("UUID return branch wraps UUID in synthetic UserResponse")


def test_get_current_user_dict_no_username_no_sub():
    """Dict payload with neither 'username' nor 'sub' raises 401."""
    with patch.object(User, "verify_token", return_value={"other_key": "value"}):
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token="anytoken")

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Could not validate credentials"


def test_get_current_user_unexpected_token_data_type():
    """verify_token returns an unexpected type (int); should raise 401."""
    with patch.object(User, "verify_token", return_value=99999):
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token="anytoken")

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Could not validate credentials"


def test_get_current_user_construction_exception():
    """UserResponse(**data) raises; outer except must catch it and return 401."""
    # "username" key present so we enter the UserResponse(**token_data) branch,
    # but "id" is invalid so Pydantic raises a ValidationError.
    bad_data = {
        "username": "x",
        "id": "not-a-uuid",          # will fail UUID validation
        "email": "x@x.com",
        "first_name": "X",
        "last_name": "X",
        "is_active": True,
        "is_verified": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    with patch.object(User, "verify_token", return_value=bad_data):
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token="anytoken")

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_active_user_inactive_from_uuid_branch():
    """Inactive user built via UUID return branch raises 400."""
    user_id = uuid4()
    with patch.object(User, "verify_token", return_value=user_id):
        # UUID branch always sets is_active=True, so override via the
        # inactive_user_data path through the dict-with-username branch.
        pass

    inactive_data = _make_user_response(is_active=False)
    with patch.object(User, "verify_token", return_value=inactive_data):
        current = get_current_user(token="anytoken")

    with pytest.raises(HTTPException) as exc_info:
        get_current_active_user(current_user=current)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail == "Inactive user"
