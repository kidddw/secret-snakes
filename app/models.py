from sqlalchemy import Column, Boolean, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import UniqueConstraint, CheckConstraint


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    # User attributes
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    # reset_token = Column(String, nullable=True)
    # reset_token_expiry = Column(DateTime, nullable=True)
    created_at = Column(DateTime)
    is_admin = Column(Boolean, default=False)
    first_name = Column(String)
    last_name = Column(String)
    shipping_street_address = Column(String)
    shipping_unit = Column(String)
    shipping_city = Column(String)
    shipping_zipcode = Column(String)
    shipping_state = Column(String)


class Assignment(Base):
    __tablename__ = "assignments"

    # Assignment attributes
    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer)
    assigned_user_id = Column(Integer, ForeignKey("users.id"))
    assignee_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime)

    assigned_user = relationship("User", foreign_keys=[assigned_user_id])
    assignee_user = relationship("User", foreign_keys=[assignee_user_id])


class Tip(Base):
    __tablename__ = "tips"

    # Tip attributes
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    year = Column(Integer)
    subject_user_id = Column(Integer, ForeignKey("users.id"))
    contributor_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime)

    subject_user = relationship("User", foreign_keys=[subject_user_id])
    contributor_user = relationship("User", foreign_keys=[contributor_user_id])


class Config(Base):
    __tablename__ = "config"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String)
    value = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime, nullable=True)

    # Enforce only one active config per key (end_time = NULL)
    __table_args__ = (
        UniqueConstraint("key", "end_time", name="uq_key_end_time"),
        CheckConstraint(
            "(end_time IS NULL) OR (start_time < end_time)",
            name="chk_valid_time_range"
        ),
    )

