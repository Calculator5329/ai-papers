import arxiv
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from database import SessionLocal
from models import DailyPaper
from fill_databases import fetch_ai_papers, store_papers_in_db, get_top_papers

MAX_RESULTS = 250
MAX_RETRIES = 3

def fill_daily_db():
    """
    This script fetches recent AI papers from arXiv and stores the top-ranked 
    papers in the 'DailyPaper' database.

    The script:
    1. Fetches AI research papers from arXiv using an API.
    2. Ranks the papers based on their scores.
    3. Stores the top papers in the database under the "daily" table.

    If fetching fails, it retries up to `MAX_RETRIES` times before giving up.
    """
    
    print("Fetching daily AI papers from arXiv API...")
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            papers = fetch_ai_papers(max_results=MAX_RESULTS, debug=True)
            if papers and papers[0]:  # Ensure we have valid results
                break
            print(f"Attempt {attempt}: No papers fetched, retrying...")
        except Exception as e:
            print(f"Attempt {attempt}: Error fetching papers: {e}")

    if not papers or not papers[0]:  # Final check if all attempts failed
        print("❌ No papers fetched after multiple attempts, exiting.")
        return

    day_papers = papers[0]  # Papers from API
    
    if not day_papers:
        print("No daily papers available, exiting.")
        return
    
    day_papers = get_top_papers(day_papers, 5)
    
    print("Scoring and storing top daily papers...")
    store_papers_in_db(day_papers, table="daily", debug=True)
    print("✅ Daily papers stored successfully.")

if __name__ == "__main__":
    fill_daily_db()
