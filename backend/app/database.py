import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

def _get_db_path():
    env_path = os.environ.get("TUTORING_DB", "")
    if env_path:
        return env_path
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), "tutoring.db")
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "..", "tutoring.db")

DATABASE_URL = f"sqlite:///{_get_db_path()}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

