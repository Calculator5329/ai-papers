"""
Database configuration module for SQLAlchemy.

This script:
- Defines the SQLite database connection.
- Configures the SQLAlchemy session (`SessionLocal`).
- Establishes the declarative base (`Base`) for defining ORM models.
"""

import os
from pathlib import Path
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine

# Define database file path using pathlib for better cross-platform support
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "papers.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Create the database engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create a session factory bound to the engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()