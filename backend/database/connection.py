# backend/database/connection.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database.models import Base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://amis_user:amis_pass@localhost:5432/amis_db"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def create_tables():
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        