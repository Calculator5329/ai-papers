"""
SQLAlchemy models for storing AI research papers and their scores.

This module defines:
- A `PaperBase` abstract class for paper-related models.
- `RecentPaper`, `DailyPaper`, and `WeeklyPaper` tables for different categories.
- A `PaperScore` table to store paper scoring data.
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Text
from database import Base
from datetime import datetime, timezone

class PaperBase(Base):
    """
    Abstract base class for AI research papers.

    This class defines common fields used in `RecentPaper`, `DailyPaper`, and `WeeklyPaper`.
    """
    __abstract__ = True  # Allows this class to be inherited without creating a table
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, index=True, nullable=False)  # Ensure uniqueness for titles
    summary = Column(Text, nullable=True)  # Main paper summary
    pdf_summary = Column(Text, nullable=True)  # Summary extracted from PDF
    ai_summary = Column(Text, nullable=True)  # AI-generated summary
    authors = Column(Text, nullable=True)  # Store as comma-separated names
    link = Column(String, unique=True, nullable=False)  # Ensure unique links
    published = Column(DateTime, nullable=True)  # Published date (from arXiv)
    score = Column(Float, nullable=True)  # Paper's score (can be updated)
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)  # Timestamp of entry

class RecentPaper(PaperBase):
    __tablename__ = "recent_papers"

class DailyPaper(PaperBase):
    __tablename__ = "daily_papers"

class WeeklyPaper(PaperBase):
    __tablename__ = "weekly_papers"

class PaperScore(Base):
    """
    Table for storing paper scores separately.
    """
    __tablename__ = "paper_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, index=True, nullable=False)
    score = Column(Float, nullable=False)
