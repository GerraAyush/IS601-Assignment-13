import pytest
import logging

from app.models.user import User
from app.schemas.user import UserCreate, PasswordUpdate


logger = logging.getLogger(__name__)

def test_password_hashing(db_session, fake_user_data):
    original_password = "TestPass123"  # Use known password for test
    hashed = User.hash_password(original_password)

    print("Original:", original_password)
    print("Hashed:", hashed)
    print("Length hashed:", len(hashed))
    
    user = User(
        first_name=fake_user_data['first_name'],
        last_name=fake_user_data['last_name'],
        email=fake_user_data['email'],
        username=fake_user_data['username'],
        password=hashed
    )
    
    assert user.verify_password(original_password) is True
    assert user.verify_password("WrongPass123") is False
    assert hashed != original_password


def test_user_registration(db_session, fake_user_data):
    fake_user_data['password'] = "TestPass123"
    
    user = User.register(db_session, fake_user_data)
    db_session.commit()
    
    assert user.first_name == fake_user_data['first_name']
    assert user.last_name == fake_user_data['last_name']
    assert user.email == fake_user_data['email']
    assert user.username == fake_user_data['username']
    assert user.is_active is True
    assert user.is_verified is False
    assert user.verify_password("TestPass123") is True


def test_duplicate_user_registration(db_session):
    # First user data
    user1_data = {
        "first_name": "Test",
        "last_name": "User1",
        "email": "unique.test@example.com",
        "username": "uniqueuser1",
        "password": "TestPass123"
    }
    
    # Second user data with same email
    user2_data = {
        "first_name": "Test",
        "last_name": "User2",
        "email": "unique.test@example.com",  # Same email
        "username": "uniqueuser2",
        "password": "TestPass123"
    }
    
    # Register first user
    first_user = User.register(db_session, user1_data)
    db_session.commit()
    db_session.refresh(first_user)
    
    # Try to register second user with same email
    with pytest.raises(ValueError, match="Username or email already exists"):
        User.register(db_session, user2_data)


def test_user_authentication(db_session, fake_user_data):
    # Use fake_user_data from fixture
    fake_user_data['password'] = "TestPass123"
    user = User.register(db_session, fake_user_data)
    db_session.commit()
    
    # Test successful authentication
    auth_result = User.authenticate(
        db_session,
        fake_user_data['username'],
        "TestPass123"
    )
    
    assert auth_result is not None
    assert "access_token" in auth_result
    assert "token_type" in auth_result
    assert auth_result["token_type"] == "bearer"
    assert "user" in auth_result


def test_user_last_login_update(db_session, fake_user_data):
    fake_user_data['password'] = "TestPass123"
    user = User.register(db_session, fake_user_data)
    db_session.commit()
    
    # Authenticate and check last_login
    assert user.last_login is None
    auth_result = User.authenticate(db_session, fake_user_data['username'], "TestPass123")
    db_session.refresh(user)
    assert user.last_login is not None


def test_unique_email_username(db_session):
    # Create first user with specific test data
    user1_data = {
        "first_name": "Test",
        "last_name": "User1",
        "email": "unique_test@example.com",
        "username": "uniqueuser",
        "password": "TestPass123"
    }
    
    # Register and commit first user
    User.register(db_session, user1_data)
    db_session.commit()
    
    # Try to create user with same email
    user2_data = {
        "first_name": "Test",
        "last_name": "User2",
        "email": "unique_test@example.com",  # Same email
        "username": "differentuser",
        "password": "TestPass123"
    }
    
    with pytest.raises(ValueError, match="Username or email already exists"):
        User.register(db_session, user2_data)


def test_short_password_registration(db_session):
    # Prepare test data with a 5-character password
    test_data = {
        "first_name": "Password",
        "last_name": "Test",
        "email": "short.pass@example.com",
        "username": "shortpass",
        "password": "Shor1"  # 5 characters, should fail
    }
    
    # Attempt registration with short password
    with pytest.raises(ValueError, match="Password must be at least 6 characters long"):
        User.register(db_session, test_data)


def test_invalid_token():
    invalid_token = "invalid.token.string"
    result = User.verify_token(invalid_token)
    assert result is None


def test_token_creation_and_verification(db_session, fake_user_data):
    fake_user_data['password'] = "TestPass123"
    user = User.register(db_session, fake_user_data)
    db_session.commit()
    
    # Create token
    token = User.create_access_token({"sub": str(user.id)})
    
    # Verify token
    decoded_user_id = User.verify_token(token)
    assert decoded_user_id == user.id


def test_authenticate_with_email(db_session, fake_user_data):
    fake_user_data['password'] = "TestPass123"
    user = User.register(db_session, fake_user_data)
    db_session.commit()
    
    # Test authentication with email
    auth_result = User.authenticate(
        db_session,
        fake_user_data['email'],  # Using email instead of username
        "TestPass123"
    )
    
    assert auth_result is not None
    assert "access_token" in auth_result


def test_user_model_representation(test_user):
    expected = f"<User(name={test_user.first_name} {test_user.last_name}, email={test_user.email})>"
    assert str(test_user) == expected


def test_missing_password_registration(db_session):
    test_data = {
        "first_name": "NoPassword",
        "last_name": "Test",
        "email": "no.password@example.com",
        "username": "nopassworduser",
        # Password is missing
    }
    
    # Adjust the expected error message
    with pytest.raises(ValueError, match="Password must be at least 6 characters long"):
        User.register(db_session, test_data)


def test_user_create_password_mismatch():
    """confirm_password differs from password → ValidationError (line 53-55)."""
    with pytest.raises(Exception, match="Passwords do not match"):
        UserCreate(
            first_name="Test",
            last_name="User",
            email="t@example.com",
            username="testuser",
            password="SecurePass123!",
            confirm_password="DifferentPass1!",
        )


def test_user_create_password_no_uppercase():
    """Password without uppercase letter → ValidationError (line 63)."""
    with pytest.raises(Exception, match="uppercase"):
        UserCreate(
            first_name="Test",
            last_name="User",
            email="t@example.com",
            username="testuser",
            password="lowercase1!",
            confirm_password="lowercase1!",
        )


def test_user_create_password_no_lowercase():
    """Password without lowercase letter → ValidationError (line 65)."""
    with pytest.raises(Exception, match="lowercase"):
        UserCreate(
            first_name="Test",
            last_name="User",
            email="t@example.com",
            username="testuser",
            password="UPPERCASE1!",
            confirm_password="UPPERCASE1!",
        )


def test_user_create_password_no_digit():
    """Password without digit → ValidationError (line 67)."""
    with pytest.raises(Exception, match="digit"):
        UserCreate(
            first_name="Test",
            last_name="User",
            email="t@example.com",
            username="testuser",
            password="NoDigitsHere!",
            confirm_password="NoDigitsHere!",
        )


def test_user_create_password_no_special_char():
    """Password without special character → ValidationError (line 69-70)."""
    with pytest.raises(Exception, match="special"):
        UserCreate(
            first_name="Test",
            last_name="User",
            email="t@example.com",
            username="testuser",
            password="NoSpecial123",
            confirm_password="NoSpecial123",
        )


def test_user_create_valid():
    """Valid UserCreate passes all validators."""
    u = UserCreate(
        first_name="Valid",
        last_name="User",
        email="valid@example.com",
        username="validuser",
        password="SecurePass123!",
        confirm_password="SecurePass123!",
    )
    assert u.username == "validuser"


def test_password_update_new_matches_confirm():
    """new_password != confirm_new_password → ValidationError (line 184-185)."""
    with pytest.raises(Exception, match="do not match"):
        PasswordUpdate(
            current_password="OldPass123!",
            new_password="NewPass123!",
            confirm_new_password="DifferentPass1!",
        )


def test_password_update_same_as_current():
    """new_password == current_password → ValidationError (line 186-187)."""
    with pytest.raises(Exception, match="different from current"):
        PasswordUpdate(
            current_password="SamePass123!",
            new_password="SamePass123!",
            confirm_new_password="SamePass123!",
        )


def test_password_update_valid():
    """Valid PasswordUpdate passes all validators."""
    p = PasswordUpdate(
        current_password="OldPass123!",
        new_password="NewPass456!",
        confirm_new_password="NewPass456!",
    )
    assert p.new_password == "NewPass456!"


def test_user_update_method(db_session, fake_user_data):
    """User.update() sets attributes and refreshes updated_at (line 48, 65-68)."""
    fake_user_data["password"] = "TestPass123"
    user = User.register(db_session, fake_user_data)
    db_session.commit()
    db_session.refresh(user)

    original_updated_at = user.updated_at
    user.update(first_name="Updated")
    assert user.first_name == "Updated"
    assert user.updated_at >= original_updated_at
    logger.info("User.update() sets attributes correctly")


def test_user_hashed_password_property(fake_user_data):
    """hashed_password property returns the stored password string (line 65-68)."""
    hashed = User.hash_password("TestPass123")
    user = User(
        first_name=fake_user_data["first_name"],
        last_name=fake_user_data["last_name"],
        email=fake_user_data["email"],
        username=fake_user_data["username"],
        password=hashed,
    )
    assert user.hashed_password == hashed


def test_user_hash_password_classmethod():
    """User.hash_password returns a bcrypt hash, not the plain text (line 73)."""
    plain = "TestPass123"
    hashed = User.hash_password(plain)
    assert hashed != plain
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    logger.info("hash_password produces a valid bcrypt hash")


def test_user_init_with_hashed_password_kwarg(fake_user_data):
    """Passing hashed_password= to __init__ remaps it to password (line 48 init)."""
    hashed = User.hash_password("TestPass123")
    user = User(
        first_name=fake_user_data["first_name"],
        last_name=fake_user_data["last_name"],
        email=fake_user_data["email"],
        username=fake_user_data["username"],
        hashed_password=hashed,
    )
    assert user.password == hashed
