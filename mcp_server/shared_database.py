from sqlmodel import SQLModel, create_engine, Session
from typing import Optional
from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    database_url: str = "sqlite:///../backend/todo.db"  # Changed to point to backend's database file
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    class Config:
        env_file = ".env"

settings = Settings()

import sys
from pathlib import Path
# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import all models to register them with SQLModel
from backend.models.task_models import Task
from backend.models.user_model import User
from backend.models.conversation_models import Conversation, Message, ToolInvocation

# Create database engine
engine = create_engine(
    settings.database_url,
    echo=False,  # Set to False to reduce logs
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

# Create all tables
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# Session generator
def get_session():
    with Session(engine) as session:
        yield session

# Direct session getter for async contexts
def get_direct_session():
    return Session(engine)