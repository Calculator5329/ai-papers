"""
CRUD operations for AI research papers stored in the database.

This module provides functions to:
- Insert papers into the database.
- Retrieve papers based on recency or a specific date.
- Sort retrieved papers by score.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
from models import RecentPaper, DailyPaper, WeeklyPaper

# Mapping for dynamic table selection
MODEL_MAP = {
    "recent": RecentPaper,
    "daily": DailyPaper,
    "weekly": WeeklyPaper
}

def create_paper(db: Session, paper_data: dict, table: str = "recent"):
    """
    Inserts a paper into the specified table.
    """
    PaperModel = MODEL_MAP.get(table, RecentPaper)

    db_paper = PaperModel(**paper_data)
    db.add(db_paper)
    db.commit()
    db.refresh(db_paper)
    return db_paper

def get_papers(db: Session, table: str = "recent", limit: int = 5):
    """
    Retrieves the most recent papers from the specified table, ordered by date.
    """
    PaperModel = MODEL_MAP.get(table, RecentPaper)

    recent_papers = (
        db.query(PaperModel)
        .order_by(PaperModel.date.desc())
        .limit(limit)
        .all()
    )

    # Sort by score in descending order
    return sorted(recent_papers, key=lambda paper: paper.score, reverse=True)

def get_papers_by_date(db: Session, table: str = "recent", target_date: date = None, limit: int = 5):
    """
    Retrieves papers from the specified table for a given date.
    If no date is provided, it defaults to retrieving the most recent papers.
    """
    PaperModel = MODEL_MAP.get(table, RecentPaper)
    query = db.query(PaperModel)

    # Convert target_date to a date object if it's a string
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
    
    # Ensure we are comparing only the date part of `published`
    if target_date:
        query = query.filter(func.date(PaperModel.published) == target_date)

    recent_papers = (
        query.order_by(PaperModel.date.desc())
        .limit(limit)
        .all()
    )

    # Sort by score in descending order
    return sorted(recent_papers, key=lambda paper: paper.score, reverse=True)