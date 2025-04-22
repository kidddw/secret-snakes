import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app import models, tips, auth


# Create a test database
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables in the test database
models.Base.metadata.create_all(bind=engine)


# Build a function that will override get_db
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override get_db
app.dependency_overrides[get_db] = override_get_db

# Initialize testing client
client = TestClient(app)


def test_create_user():
    """Test the register user functionality."""

    # Send a test post through
    response = client.post(
        "/register",
        json={
            "username": "testuser",
            "is_admin": False,
            "email": "test@example.com",
            "password": "testpassword",
            "first_name": "test",
            "last_name": "user",
            "shipping_street_address": "test_address",
            "shipping_city": "test_city",
            "shipping_zipcode": "37032",
            "shipping_state": "TN"
        }
    )

    # Make sure we got a healthy response
    assert response.status_code == 200

    # Check the response data
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "id" in data


def test_create_user_duplicate_username():
    """
    Test that duplicate user registry throws exception.
    To be run after test_create_user.
    """

    # Send a test post through
    response = client.post(
        "/register",
        json={
            "username": "testuser",
            "email": "another@example.com",
            "password": "testpassword",
            "first_name": "test2",
            "last_name": "user2",
            "shipping_street_address": "test_address2",
            "shipping_city": "test_city2",
            "shipping_zipcode": "37032",
            "shipping_state": "TN"
        }
    )

    # Make sure we got an exception
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already registered"


def test_login():
    """
    Test user login functionality.
    To be run after test_create_user.
    """

    # Send a test post through
    response = client.post(
        "/token",
        data={
            "username": "testuser",
            "password": "testpassword"
        }
    )

    # Make sure we got a healthy response
    assert response.status_code == 200

    # Check the response data
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_incorrect_password():
    """
    Test that wrong password login throws exception.
    To be run after test_create_user.
    """

    # Send a test post through
    response = client.post(
        "/token",
        data={
            "username": "testuser",
            "password": "wrongpassword"
        }
    )

    # Make sure we got an exception
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


def test_read_users_me():
    """
    Test the check current user functionality.
    To be run after test_create_user.
    """

    # First, get a token
    login_response = client.post(
        "/token",
        data={
            "username": "testuser",
            "password": "testpassword"
        }
    )
    token = login_response.json()["access_token"]

    # Then use the token to access the /users/me endpoint
    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    # Make sure we got a healthy response
    assert response.status_code == 200

    # Check the response data
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"


if __name__ == "__main__":
    pytest.main([__file__])
