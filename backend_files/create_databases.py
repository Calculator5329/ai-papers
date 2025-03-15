"""
Database initialization script.

This script:
- Imports the database configuration and ORM models.
- Creates all necessary tables in the database if they do not exist.
"""
from database import Base, engine
import models  # Ensure ORM models are imported before creating tables

def create_tables():
    """Creates database tables based on ORM models."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database and tables created successfully.")

if __name__ == "__main__":
    create_tables()