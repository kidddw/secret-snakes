import os
import uuid
import datetime
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt, ExpiredSignatureError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from pydantic import ValidationError
import logging

from app import models, schemas, database, config


# Security configuration
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', 15))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Adding logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verify_password(plain_password, hashed_password):
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    """Generate a hash from a password"""
    return pwd_context.hash(password)


def create_reset_password_token():
    return str(uuid.uuid4())


def set_user_reset_state(db: Session, user: models.User, reset_token: str = None):
    """
    Set the reset token and expiry for a user.
    This function generates a unique reset token and sets its expiry to 1 hour from now.
    """

    reset_token_expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)

    user.reset_token = reset_token
    user.reset_token_expiry = reset_token_expiry

    db.commit()
    db.refresh(user)

    return user


def authenticate_user_by_reset_token(db: Session, reset_token: str):
    """
    Authenticate a user by reset token.
    This function checks if the provided reset token is valid and not expired.
    If valid, it returns the user object; otherwise, it returns None.
    """

    # Query for this reset token in the users table
    user = db.query(models.User).filter(
        models.User.reset_token == reset_token,
        models.User.reset_token_expiry > datetime.datetime.now(datetime.timezone.utc)
    ).first()

    # If User is not found in the table or the token is expired, return None
    if not user:
        logger.warning(f"Authentication failed for reset token: {reset_token}. Token not found or expired.")
        return None

    return user


def update_user_password(db: Session, user: models.User, new_password: str):
    """
    Update the user's password.
    This function hashes the new password and updates the user's hashed_password field.
    It also clears the reset token and expiry to prevent further use of the reset token.
    """

    # Hash the new password
    hashed_password = get_password_hash(new_password)
    logger.info(f"Updating password for user: {user.username}")

    # Update user object
    user.hashed_password = hashed_password
    user.reset_token = None
    user.reset_token_expiry = None

    logger.info(f"Password updated successfully for user: {user.username}")

    # Commit changes to the database
    db.commit()
    db.refresh(user)

    logger.info(f"User {user.username} password updated and reset token cleared.")

    return user


def authenticate_user(db: Session, username: str, password: str):
    """Authenticate a user by username and password."""

    # Query for this username in the users table
    user = db.query(models.User).filter(models.User.username == username).first()

    # If User is not found in the table, return boolean False
    if not user:
        logger.warning(f"Authentication failed for user: {username}. User not found.")
        return False

    # Check if the password matches what is in the user table for this user
    password_verified = verify_password(password, user.hashed_password)

    # If User is not found in the table or the password entered does not match, return boolean False
    if not password_verified:
        logger.warning(f"Authentication failed for user: {username}. Incorrect password.")
        return False

    return user


def create_access_token(data: dict, expires_delta: datetime.timedelta = None):
    """
    Create a new access token.
    Create a JSON Web Token
    Encodes the payload into a JWT string, which consists of three parts separated by dots:
        header, payload, and signature.
    The header typically contains the token type and the algorithm used
    The payload contains the claims, which in this case includes the original data plus an expiration time.
    The signature is created using the specified algorithm and secret key to ensure the token's integrity.

    This string is URL-safe and can be easily transmitted in HTTP headers or as URL parameters.
    The returned JWT can later be decoded and verified using the same secret key and algorithm.
    """

    # Declare data to encode
    to_encode = data.copy()

    # Set expiration time
    # Use expires_delta if provided else use 15 minutes as default
    expiration_time = datetime.datetime.now(datetime.timezone.utc) + (expires_delta or datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

    # Add expiration time to the data dictionary
    to_encode.update({"exp": expiration_time})

    # Create a JSON Web Token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def get_current_user(db: Session = Depends(database.get_db), token: str = Depends(oauth2_scheme)):
    """Get the current user from the provided token."""

    # Design exception in case of invalid credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")

        # If no username found in json web token, raise invalid credentials exception
        if username is None:
            raise credentials_exception

        # Create TokenData class instance
        token_data = schemas.TokenData(username=username)

    except (JWTError, ValidationError):
        logger.warning("Could not validate credentials")
        return None

    except ExpiredSignatureError:
        logger.warning("Token expired.")
        return None

    # Query for this username in the users table
    user = db.query(models.User).filter(models.User.username == token_data.username).first()

    return user


def get_user_for_reset(db: Session = Depends(database.get_db), token: str = Depends(oauth2_scheme)):
    """Get the current user from the provided token."""

    # Design exception in case of invalid credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")

        # If no username found in json web token, raise invalid credentials exception
        if username is None:
            raise credentials_exception

        # Create TokenData class instance
        token_data = schemas.TokenData(username=username)

    except (JWTError, ValidationError):
        logger.warning("Could not validate credentials")
        return None

    except ExpiredSignatureError:
        logger.warning("Token expired.")
        return None

    # Query for this username in the users table
    user = db.query(models.User).filter(
        models.User.username == token_data.username,
        models.User.reset_token == token,
        models.User.reset_token_expiry > datetime.datetime.now(datetime.timezone.utc)
    ).first()

    return user


def get_current_admin_user(current_user: models.User):
    """Check if current user is admin"""

    # Check is admin status on current user object
    # If not admin, raise exception
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )

    return current_user


def get_allowed_registration(db: Session = Depends(database.get_db)):

    # Check if registration is allowed
    allow_registration = config.get_config(db).get("allow_registration", "True")
    allow_registration = (allow_registration == "True")

    if not allow_registration:
        raise HTTPException(
            status_code=403, 
            detail="Registration is currently disabled by the administrator."
        )
    
    return allow_registration
