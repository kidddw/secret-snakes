import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SQLITE_DATABASE_FILEPATH = os.environ.get("SQLITE_DATABASE_FILEPATH", "./database.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{SQLITE_DATABASE_FILEPATH}"
logger.info(f"Using database URL: {SQLALCHEMY_DATABASE_URL}")

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
    logger.info("Checking for and creating any missing database tables.")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialization complete.")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
