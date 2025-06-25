import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base

SQLITE_DATABASE_FILEPATH = os.environ.get("SQLITE_DATABASE_FILEPATH", "./database.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{SQLITE_DATABASE_FILEPATH}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def init_db():
    """
    If no database exists, create all tables in the database.
    """
    if not os.path.exists(SQLITE_DATABASE_FILEPATH):
    
        # Initialize the database
        Base.metadata.create_all(bind=engine)
        print(f"Database created at {SQLITE_DATABASE_FILEPATH}.")

    else:
        print("Database already exists.")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
