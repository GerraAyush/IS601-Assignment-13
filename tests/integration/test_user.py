import pytest
import logging
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from tests.conftest import create_fake_user, managed_db_session


logger = logging.getLogger(__name__)


def test_database_connection(db_session):
    result = db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1
    logger.info("Database connection test passed")


def test_managed_session():
    with managed_db_session() as session:
        session.execute(text("SELECT 1"))
        try:
            session.execute(text("SELECT * FROM nonexistent_table"))
        except Exception as e:
            assert "nonexistent_table" in str(e)


def test_session_handling(db_session_committed):
    initial_count = db_session_committed.query(User).count()
    logger.info(f"Initial user count before test_session_handling: {initial_count}")

    user1 = User(
        first_name="Test",
        last_name="User",
        email="test1@example.com",
        username="testuser1",
        password="password123"
    )
    db_session_committed.add(user1)
    db_session_committed.commit()
    logger.info(f"Added user1: {user1.email}")

    count_after_user1 = db_session_committed.query(User).count()
    logger.info(f"User count after adding user1: {count_after_user1}")
    assert count_after_user1 == initial_count + 1, (
        f"Expected {initial_count + 1} users after adding user1, found {count_after_user1}"
    )

    try:
        user2 = User(
            first_name="Test",
            last_name="User",
            email="test1@example.com",
            username="testuser2",
            password="password456"
        )
        db_session_committed.add(user2)
        db_session_committed.commit()
    except IntegrityError:
        db_session_committed.rollback()
        logger.info("IntegrityError caught and rolled back for user2.")

    found_user1 = db_session_committed.query(User).filter_by(email="test1@example.com").first()
    assert found_user1 is not None, "User1 should still exist after rollback"
    assert found_user1.username == "testuser1"
    logger.info(f"Found user1 after rollback: {found_user1.email}")

    user3 = User(
        first_name="Test",
        last_name="User",
        email="test3@example.com",
        username="testuser3",
        password="password789"
    )
    db_session_committed.add(user3)
    db_session_committed.commit()
    logger.info(f"Added user3: {user3.email}")

    final_count = db_session_committed.query(User).count()
    emails_added = {user1.email, user3.email}
    logger.info(f"Final user count: {final_count}, new emails: {emails_added}")

    assert final_count == initial_count + 2, (
        f"Expected {initial_count + 2} users (original + user1 + user3), found {final_count}"
    )
    assert found_user1 is not None, "User1 must remain"
    assert db_session_committed.query(User).filter_by(email="test3@example.com").first() is not None, (
        "User3 must exist"
    )


def test_create_user_with_faker(db_session):
    user_data = create_fake_user()
    logger.info(f"Creating user with data: {user_data}")
    
    user = User(**user_data)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    assert user.id is not None
    assert user.email == user_data["email"]
    logger.info(f"Successfully created user with ID: {user.id}")


def test_create_multiple_users(db_session):
    users = []
    for _ in range(3):
        user_data = create_fake_user()
        user = User(**user_data)
        users.append(user)
        db_session.add(user)
    
    db_session.commit()
    assert len(users) == 3
    logger.info(f"Successfully created {len(users)} users")

def test_query_methods(db_session, seed_users):
    user_count = db_session.query(User).count()
    assert user_count >= len(seed_users), "The user table should have at least the seeded users"
    
    first_user = seed_users[0]
    found = db_session.query(User).filter_by(email=first_user.email).first()
    assert found is not None, "Should find the seeded user by email"
    
    users_by_email = db_session.query(User).order_by(User.email).all()
    assert len(users_by_email) >= len(seed_users), "Query should return at least the seeded users"

def test_transaction_rollback(db_session):
    initial_count = db_session.query(User).count()
    
    try:
        user_data = create_fake_user()
        user = User(**user_data)
        db_session.add(user)

        db_session.execute(text("SELECT * FROM nonexistent_table"))
        db_session.commit()
    except Exception:
        db_session.rollback()
    
    final_count = db_session.query(User).count()
    assert final_count == initial_count, "The new user should not have been committed"

def test_update_with_refresh(db_session, test_user):
    original_email = test_user.email
    original_update_time = test_user.updated_at
    
    new_email = f"new_{original_email}"
    test_user.email = new_email
    db_session.commit()
    db_session.refresh(test_user)
    
    assert test_user.email == new_email, "Email should have been updated"
    assert test_user.updated_at > original_update_time, "Updated time should be newer"
    logger.info(f"Successfully updated user {test_user.id}")

@pytest.mark.slow
def test_bulk_operations(db_session):
    users_data = [create_fake_user() for _ in range(10)]
    users = [User(**data) for data in users_data]
    db_session.bulk_save_objects(users)
    db_session.commit()
    
    count = db_session.query(User).count()
    assert count >= 10, "At least 10 users should now be in the database"
    logger.info(f"Successfully performed bulk operation with {len(users)} users")

def test_unique_email_constraint(db_session):
    first_user_data = create_fake_user()
    first_user = User(**first_user_data)
    db_session.add(first_user)
    db_session.commit()
    
    second_user_data = create_fake_user()
    second_user_data["email"] = first_user_data["email"]
    second_user = User(**second_user_data)
    db_session.add(second_user)
    
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_unique_username_constraint(db_session):
    first_user_data = create_fake_user()
    first_user = User(**first_user_data)
    db_session.add(first_user)
    db_session.commit()
    
    second_user_data = create_fake_user()
    second_user_data["username"] = first_user_data["username"]
    second_user = User(**second_user_data)
    db_session.add(second_user)
    
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

def test_user_persistence_after_constraint(db_session):
    initial_user_data = {
        "first_name": "First",
        "last_name": "User",
        "email": "first@example.com",
        "username": "firstuser",
        "password": "password123"
    }
    initial_user = User(**initial_user_data)
    db_session.add(initial_user)
    db_session.commit()
    saved_id = initial_user.id

    # Use a savepoint so that rolling back the IntegrityError does not undo
    # the already-committed initial_user row.
    try:
        savepoint = db_session.begin_nested()
        duplicate_user = User(
            first_name="Second",
            last_name="User",
            email="first@example.com",
            username="seconduser",
            password="password456"
        )
        db_session.add(duplicate_user)
        savepoint.commit()
        assert False, "Should have raised IntegrityError"
    except IntegrityError:
        savepoint.rollback()

    found_user = db_session.query(User).filter_by(id=saved_id).first()
    assert found_user is not None, "Original user should exist"
    assert found_user.id == saved_id, "Should find original user by ID"
    assert found_user.email == "first@example.com", "Email should be unchanged"
    assert found_user.username == "firstuser", "Username should be unchanged"

def test_error_handling():
    with pytest.raises(Exception) as exc_info:
        with managed_db_session() as session:
            session.execute(text("INVALID SQL"))
    assert "INVALID SQL" in str(exc_info.value)
    