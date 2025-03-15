"""
Scrapes recent AI papers from arXiv's "New Submissions" page and stores them in the database.

This script:
1. Scrapes recent AI papers using BeautifulSoup.
2. Extracts metadata (title, authors, summary, date, link).
3. Scores and stores the most relevant papers in the "recent" database table.

Run this script to keep the "recent" database up to date with the latest AI research papers.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from fill_databases import store_papers_in_db, get_top_papers

def ensure_datetime_utc(date_value):
    """
    Ensures the given date is a timezone-aware datetime object in UTC.
    """
    if isinstance(date_value, datetime):
        return date_value.astimezone(timezone.utc)

    if isinstance(date_value, str):
        try:
            return datetime.strptime(date_value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            print(f"⚠️ Warning: Unexpected date format: {date_value}")
            return None
    
    return None

def fetch_recent_papers(debug=False):
    """
    Scrapes recent AI papers from arXiv's "New Submissions" page.
    """
    url = "https://arxiv.org/list/cs.AI/new"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    if debug:
        print(f"🔍 Scraping arXiv for New Submissions: {url}")

    recent_papers = []

    # Iterate through all paper entries
    for dt in soup.find_all("dt"):
        link_tag = dt.find("a", {"title": "Abstract"})
        if not link_tag:
            continue  # Skip if no valid link found

        paper_id = link_tag.text.strip()
        pdf_url = f"https://arxiv.org/pdf/{paper_id}.pdf"

        # Find corresponding title
        dd = dt.find_next_sibling("dd")
        title_tag = dd.find("div", class_="list-title mathjax")
        title = title_tag.text.replace("Title:", "").strip() if title_tag else "Unknown Title"

        # Find authors
        authors_tag = dd.find("div", class_="list-authors")
        authors = [a.text.strip() for a in authors_tag.find_all("a")] if authors_tag else []

        # Find summary
        summary_tag = dd.find("p", class_="mathjax")
        summary = summary_tag.text.strip() if summary_tag else "No summary available."

        # Ensure valid metadata before appending
        if not title or not pdf_url:
            print(f"⚠️ Skipping paper with missing metadata: {title}")
            continue

        recent_papers.append({
            "title": title,
            "summary": summary,
            "authors": authors,
            "link": pdf_url,
            "date": datetime.now(timezone.utc),  # Time of scraping
            "published": datetime.now(timezone.utc),  # Placeholder, as arXiv new submissions lack exact dates
        })

    if debug:
        print(f"📚 Fetched {len(recent_papers)} recent AI papers from arXiv.")

    return recent_papers

def fill_recent_db():
    """
    Fetches and stores recent AI papers from arXiv's "New Submissions" page in the database.
    """
    print("Fetching recent AI papers from arXiv web scraping...")
    recent_papers = fetch_recent_papers(debug=True)

    if not recent_papers:
        print("❌ No recent papers available, exiting.")
        return

    # Select the top 10 papers by score
    top_recent_papers = get_top_papers(recent_papers, 10)

    print("📊 Scoring and storing recent papers...")
    store_papers_in_db(top_recent_papers, table="recent", debug=True)
    print("✅ Recent papers stored successfully.")

if __name__ == "__main__":
    fill_recent_db()
