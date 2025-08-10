from pydantic import BaseModel, EmailStr, Field, constr
from datetime import datetime
from typing import List, Optional


class UserBase(BaseModel):
    """
    Serves as the foundation for user-related data models.
    Contains the common fields that are shared across different user representations
    """

    username: str
    is_admin: bool = False

    # Requires email-validator to be installed
    # The input string must be a valid email address, and the output is a simple string
    email: EmailStr

    # First and last name
    first_name: str
    last_name: str

    # Shipping street address
    shipping_street_address: str = Field(..., min_length=1, max_length=100)
    shipping_unit: Optional[str]

    # Shipping City
    shipping_city: str = Field(..., min_length=1, max_length=50)

    # US or Canadian formats
    shipping_zipcode: constr(regex=r"^\d{5}(-\d{4})?$|^[A-Za-z]\d[A-Za-z] \d[A-Za-z]\d$")

    # US state or Canadian provinces abbreviation
    shipping_state: str = Field(..., min_length=2, max_length=2)


class UserCreate(UserBase):
    """
    Extends UserBase and is specifically designed for user registration or creation.
    Allows for a clear distinction between data needed for user creation and data used in other contexts.
    Keeps sensitive information (like passwords) isolated to specific operations, enhancing security
    """
    password: str


class UserUpdate(BaseModel):
    """
    Extends UserBase and is specifically designed for user updates.
    """
    email: EmailStr | None = None
    first_name: str | None = None
    last_name: str | None = None
    shipping_street_address: str | None = None
    shipping_unit: str | None = None
    shipping_city: str | None = None
    shipping_zipcode: str | None = None
    shipping_state: str | None = None


class User(UserBase):
    """
    Extends UserBase but represents a fully formed user entity as it exists in the system.
    Adds system-generated fields like id and created_at, which are typically assigned by the backend.
    To be used in API responses, excluding sensitive information like passwords.
    """
    id: int
    created_at: datetime

    # Integration with SQLAlchemy ORM models
    class Config:
        # Essentially telling Pydantic that this model will be used to represent SQLAlchemy ORM instances
        # Allowing for seamless integration between database models and API models
        orm_mode = True


class UserEmail(BaseModel):
    """
    User email for username recovery.
    """
    email: EmailStr


class PasswordReset(BaseModel):
    token: str
    password: str
    password_confirm: str
    

class ExclusionCreate(BaseModel):
    year: int
    giver_id: int
    excluded_receivers: List[int]
    

class AssignmentBase(BaseModel):
    """
    Serves as the foundation for assignment-related data models.
    Contains the common fields that are shared across different assignment representations
    """
    year: int


class AssignmentCreate(AssignmentBase):
    """
    Extends AssignmentBase and is specifically designed for assignment creation.
    Allows for a clear distinction between data needed for assignment creation and data used in other contexts.
    Keeps sensitive information isolated to specific operations, enhancing security
    """
    participants: List[int]


class Assignment(AssignmentBase):
    """
    Extends AssignmentBase but represents a fully formed assignment entity as it exists in the system.
    Adds system-generated fields like id and created_at, which are typically assigned by the backend.
    To be used in API responses, excluding sensitive information like passwords.
    """
    id: int
    created_at: datetime
    assignee_user_id: int
    assigned_user_id: int

    # Integration with SQLAlchemy ORM models
    class Config:
        # Essentially telling Pydantic that this model will be used to represent SQLAlchemy ORM instances
        # Allowing for seamless integration between database models and API models
        orm_mode = True


class TipBase(BaseModel):
    """
    Serves as the foundation for tip-related data models.
    Contains the common fields that are shared across different tip representations
    """
    content: str
    subject_user_id: int
    year: int


class TipCreate(TipBase):
    """
    Extends TipBase and is specifically designed for tip creation.
    Allows for a clear distinction between data needed for tip creation and data used in other contexts.
    Keeps sensitive information isolated to specific operations, enhancing security
    """
    pass


class Tip(TipBase):
    """
    Extends TipBase but represents a fully formed tip entity as it exists in the system.
    Adds system-generated fields like id and created_at, which are typically assigned by the backend.
    To be used in API responses, excluding sensitive information like passwords.
    """
    id: int
    created_at: datetime
    contributor_user_id: int

    # Integration with SQLAlchemy ORM models
    class Config:
        # Essentially telling Pydantic that this model will be used to represent SQLAlchemy ORM instances
        # Allowing for seamless integration between database models and API models
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class AssignmentYearUpdate(BaseModel):
    assignment_year: int
