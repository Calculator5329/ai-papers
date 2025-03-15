"""
Updates the weekly database by selecting the top 5 highest-scoring papers 
from the past 7 days in the DailyPaper table and storing them in the WeeklyPaper table.

This script:
1. Retrieves AI research papers published in the last 7 days.
2. Selects the top 5 papers based on their score.
3. Inserts the selected papers into the WeeklyPaper table (avoiding duplicates).
"""

from sqlalchemy import and_
from datetime import datetime, timedelta, timezone
from models import DailyPaper, WeeklyPaper
from database import SessionLocal
from crud import create_paper  # Use the existing CRUD function

def update_weekly_db():
    """
    Updates the WeeklyPaper table with the top 5 highest-scoring papers 
    from the last 7 days in the DailyPaper table.
    """
    print("📅 Updating weekly database...")

    db = SessionLocal()
    today = datetime.now(timezone.utc)
    week_ago = today - timedelta(days=7)

    # Fetch the last 7 days of daily papers
    daily_papers_db = db.query(DailyPaper).filter(
        and_(DailyPaper.published >= week_ago, DailyPaper.published <= today)
    ).all()

    if not daily_papers_db:
        print("❌ No daily papers found in the last 7 days. Exiting.")
        db.close()
        return

    # Convert SQLAlchemy objects to dictionaries
    papers_list = [
        {
            "title": paper.title,
            "summary": paper.summary,
            "pdf_summary": paper.pdf_summary,
            "ai_summary": paper.ai_summary,
            "authors": paper.authors,
            "link": paper.link,
            "published": paper.published,
            "score": paper.score or 0  # Use existing score if available
        }
        for paper in daily_papers_db
    ]

    # Sort papers by score in descending order and select the top 5
    top_weekly_papers = sorted(papers_list, key=lambda p: p["score"], reverse=True)[:5]

    if not top_weekly_papers:
        print("❌ No high-scoring papers found. Exiting.")
        db.close()
        return

    # Insert top 5 weekly papers into WeeklyPaper table (avoid duplicates)
    for paper in top_weekly_papers:
        existing_paper = db.query(WeeklyPaper).filter(WeeklyPaper.title == paper["title"]).first()
        if not existing_paper:
            create_paper(db, paper, "weekly")  # Use CRUD function to insert
            print(f"✅ Added: {paper['title']}")
        else:
            print(f"🔁 Skipping duplicate: {paper['title']}")

    db.close()
    print(f"✅ Weekly database updated with top {len(top_weekly_papers)} papers.")

if __name__ == "__main__":
    update_weekly_db()
