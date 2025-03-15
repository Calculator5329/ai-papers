"""
This module provides core database functions for handling AI research papers.

Originally used for testing API functions and backend development, it now:
- Fetches AI papers from arXiv.
- Stores papers in the appropriate database tables.
- Retrieves and ranks top papers.

These functions are used throughout the backend to manage paper storage, retrieval, and ranking.
"""

import arxiv
import re
from datetime import datetime, timedelta, timezone
import math
import google.generativeai as genai
import pytz
import fitz
from sqlalchemy.orm import Session
from database import SessionLocal
from models import RecentPaper, DailyPaper, WeeklyPaper, PaperScore
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, date
import json
import os


# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
llm_model = genai.GenerativeModel('gemini-2.0-flash')

# Define a global arXiv client
client = arxiv.Client()



def ensure_datetime_utc(date_value):
    """Converts a date, datetime, or string into a timezone-aware UTC datetime object."""

    if isinstance(date_value, datetime):
        return date_value.astimezone(timezone.utc)  # Ensure UTC
    elif isinstance(date_value, date):  # If it's a date object, convert it to datetime at midnight UTC
        return datetime.combine(date_value, datetime.min.time(), tzinfo=timezone.utc)
    elif isinstance(date_value, str):  # If it's a string, try to parse it
        try:
            return datetime.strptime(date_value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            print(f"⚠️ Warning: Unexpected date format: {date_value}")
            return None
    else:
        print(f"⚠️ Warning: Unknown date type: {type(date_value)} - {date_value}")
        return None


def fetch_ai_papers(max_results=10, debug=False, scrape=False):
    """
    Fetches recent AI papers from arXiv using both the API and, optionally, web scraping (Recent Submissions section).
    """

    
    # Sometimes the pages that we query are blank, giving an error. This loop ensures we keep trying, with a lower value for max_results until it works.
    while max_results > 0:
        try:
            # Step 1: Fetch from the API
            search = arxiv.Search(
                query="cat:cs.AI OR cat:cs.CL OR cat:cs.LG OR cat:cs.CV OR cat:cs.RO OR cat:cs.MA OR cat:cs.HC OR cat:cs.IR OR cat:cs.NE OR cat:eess.SP",
                max_results=max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate
            )

            if debug:
                print(f"🔍 Searching arXiv for AI papers: {search}")

            papers = []
            today_utc = datetime.now(timezone.utc).date()  # Get today's date in UTC
            first_paper_date = None

            for result in arxiv.Client().results(search):
                # Get published date
                published_date = result.published.date()

                # Stop appending if this paper is from a different day than the first paper
                if first_paper_date is None:
                    first_paper_date = published_date
                elif published_date != first_paper_date:
                    break
                
                # Add to list
                papers.append({
                        'title': result.title,
                        'summary': result.summary,
                        'authors': [author.name for author in result.authors],
                        'link': result.pdf_url,
                        'published': result.published
                })
            # If everything worked, we want out of the loop, so we set max_results to 0
            max_results = 0
        except arxiv.UnexpectedEmptyPageError:
            print("Empty page error, retrying...")
            max_results -= round(max_results / 8) + 10  # Reduce the number of results and retry
            continue 

        if debug:
            print(f"📚 Fetched {len(papers)} AI papers from the arXiv API.")

    recent_papers = []
    
    # Only web scrape if specified
    if scrape:
        # Step 2: Scrape New Submissions from arXiv
        url = "https://arxiv.org/list/cs.AI/new"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        if debug:
            print(f"🔍 Scraping arXiv for New Submissions: {url}")

        # Find all the paper entries
        for dt in soup.find_all("dt"):
            link_tag = dt.find("a", {"title": "Abstract"})
            if link_tag:
                paper_id = link_tag.text.strip()
                pdf_url = f"https://arxiv.org/pdf/{paper_id}.pdf"

                # Find corresponding title
                dd = dt.find_next_sibling("dd")
                title_tag = dd.find("div", class_="list-title mathjax")
                title = title_tag.text.replace("Title:", "").strip() if title_tag else "Unknown Title"

                # Find authors
                authors_tag = dd.find("div", class_="list-authors")
                authors = []
                if authors_tag:
                    authors = [a.text.strip() for a in authors_tag.find_all("a")]

                # Find summary
                summary_tag = dd.find("p", class_="mathjax")
                summary = summary_tag.text.strip() if summary_tag else "No summary available."

                # Append to recent papers list
                recent_papers.append({
                    'title': title,
                    'summary': summary,
                    'authors': authors,
                    'link': pdf_url,
                    'published': ensure_datetime_utc(today_utc)  # Ensure UTC datetime
                })

        if debug:
            print(f"📚 Fetched {len(recent_papers)} AI papers from arXiv New Submissions.")

    return [papers, recent_papers]


def fetch_papers_historical(debug=False, start_day=None, end_day=None, max_results=250):
    """
    Fetches AI papers from arXiv for a given date range and organizes them into daily sublists.
    """
    if start_day is None or end_day is None:
        raise ValueError("Both start_day and end_day must be provided.")
    
    # Convert strings to date objects.
    start_date = datetime.strptime(start_day, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_day, "%Y-%m-%d").date()
    
    if start_date > end_date:
        raise ValueError("start_day must be before or equal to end_day.")
    
    search = arxiv.Search(
        query="cat:cs.AI OR cat:cs.CL OR cat:cs.LG OR cat:cs.CV OR cat:cs.RO OR cat:cs.MA OR cat:cs.HC OR cat:cs.IR OR cat:cs.NE OR cat:eess.SP",
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    
    if debug:
        print("Fetching papers with max_results =", max_results)
    
    # Attempt to fetch all results with one retry.
    max_retries = 1
    retries = 0
    all_results = []
    client = arxiv.Client()
    while retries <= max_retries:
        try:
            all_results = list(client.results(search))
            break  # Success; exit loop.
        except arxiv.UnexpectedEmptyPageError as e:
            if retries < max_retries:
                if debug:
                    print(f"Retrying after error: {e}")
                retries += 1
            else:
                if debug:
                    print(f"Skipping API call after error: {e}")
                all_results = []
                break

    if debug:
        print("Total results fetched:", len(all_results))
    
    # Group the papers by their published date.
    papers_by_day = {}
    for result in all_results:
        pub_date = result.published.date()
        # Only include papers within our desired date range.
        if start_date <= pub_date <= end_date:
            paper_dict = {
                'title': result.title,
                'summary': result.summary,
                'authors': [author.name for author in result.authors],
                'link': result.pdf_url,
                'published': result.published
            }
            papers_by_day.setdefault(pub_date, []).append(paper_dict)
            if debug:
                print(f"Added paper from {pub_date}: {result.title}")
    
    # Build a list of sublists, one for each day in the range.
    all_papers = []
    current_day = start_date
    while current_day <= end_date:
        day_papers = papers_by_day.get(current_day, [])
        if debug:
            print(f"📅 {current_day}: {len(day_papers)} papers")
        all_papers.append(day_papers)
        current_day += timedelta(days=1)

    print("✅ All papers fetched successfully.")
    
    return all_papers


def store_papers_in_db(papers, table="recent", debug=False):
    """
    Stores fetched AI papers into the specified database table.
    """
    db = SessionLocal()

    model_map = {
        "recent": RecentPaper,
        "daily": DailyPaper,
        "weekly": WeeklyPaper
    }
    
    PaperModel = model_map.get(table, RecentPaper)
    
    for paper in papers:
        # Check if the paper already exists in the selected table (avoid duplicates)
        existing_paper = db.query(PaperModel).filter(PaperModel.title == paper['title']).first()
        if existing_paper:
            print(f"Skipping duplicate: {paper['title']}")
            continue
        if debug:
            print(f"📄 Storing paper: {paper['title']}")
        
        # Score paper if not scored
        if 'score' not in paper or paper['score'] == 0:
            score, _ = score_paper(paper)
            paper['score'] = score

        # Generate AI Summary if not generated
        if 'ai_summary' not in paper or not paper['ai_summary']:
            ai_summ = ai_summary(paper['title'], paper['summary'])
            paper['ai_summary'] = ai_summ if ai_summ else "Summary not available."

        # Generate PDF Summary if not generated
        if 'pdf_summary' not in paper or not paper['pdf_summary']:
            pdf_summ = pdf_summary(paper['link'])
            paper['pdf_summary'] = pdf_summ if pdf_summ else "Summary not available."

        # Convert authors list to a comma-separated string
        paper['authors'] = ", ".join(paper['authors'])

        # Ensure the date is timezone-aware
        if isinstance(paper['published'], datetime):
            paper['published'] = paper['published'].astimezone(timezone.utc)

        # Store in the selected table
        db_paper = PaperModel(
            title=paper['title'],
            summary=paper['summary'],
            ai_summary=paper['ai_summary'],
            pdf_summary=paper['pdf_summary'],
            authors=paper['authors'],
            link=paper['link'],
            published=paper['published'],
            score=paper['score'],
            date=datetime.now(timezone.utc)  # Store the date when added, the strategy for scraping does not get date published.
        )
        db.add(db_paper)
    db.commit()
    db.close()
    print(f"✅ Papers stored in `{table}` table successfully.")


def load_top_ai_researchers():
    """
    Loads a curated list of top AI researchers from a JSON file.
    """
    try:
        with open("./backend/top_ai_researchers.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        with open("./top_ai_researchers.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading top AI researchers: {e}")
        return []
    

def evaluate_paper_with_gemini(title, summary):
    """
    Uses Gemini 2.0 Flash to evaluate a paper's relevance, insight, novelty, and impact.
    """
    prompt = f"""
    You are an expert AI researcher reviewing recent AI papers. 
    Given the following paper title and summary, rate it on the following factors (1-10):
    
    - **Relevance:** How relevant is this to cutting-edge AI?
    - **Insightfulness:** Does it provide new insights?
    - **Novelty:** Is this a genuinely new idea?
    - **Impact:** How likely is this to influence AI research significantly?

    Your scores should be based on a system with a normal distribution of scores, with a mean of 5 and a standard deviation of 3.
    If you are very suprised by a paper, you might give it a 9 or 10. If you are very unimpressed, you might give it a 1 or 2.
    Often, Large Language Models (LLMs) like yourself only provide scores in the 6-8 range for most papers.
    Ensure your scores are not all within the same range, but reflect the true quality of the paper.
    Ensure you only give scores, not feedback, comments, or explanation.

    Return your response as JSON:
    {{"relevance": <score>, "insightfulness": <score>, "novelty": <score>, "impact": <score>}}

    **Title:** {title}
    **Summary:** {summary}
    """

    try:
        
        response = llm_model.generate_content(prompt)
        
        if not response or not response.text:
            raise ValueError("Gemini returned an empty response.")

        response_text = response.text.strip().strip("```json").strip("```").strip()  # ✅ Clean JSON response

        # Ensure the response is valid JSON
        scores = json.loads(response_text)
        
        return scores
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from Gemini: {e}\nResponse: {response.text if response else 'None'}")
    except Exception as e:
        print(f"Error with Gemini evaluation: {e}")


def ai_summary(title, summary):
    """
    Generates a summary of an AI paper using Gemini 2.0 Flash.
    """
    prompt = f"""
    You are an AI researcher reviewing a recent AI paper. 
    Summarize the following paper using 3-5 sentences:
    
    **Title:** {title}
    **Summary:** {summary}
    """

    try:
        response = llm_model.generate_content(prompt)
        
        if not response or not response.text:
            raise ValueError("Gemini returned an empty response.")

        return response.text.strip()
    except Exception as e:
        print(f"Error with Gemini summary generation: {e}")


def pdf_summary(pdf_path):
    """
    Extracts text from a given PDF file and generates a summary using Gemini.
    """
    
    # Check if the PDF path is a URL
    if pdf_path.startswith("http"):
        local_pdf = "temp_paper.pdf"
        try:
            # Download the PDF file
            response = requests.get(pdf_path, stream=True)
            response.raise_for_status()  # Raise error if request fails
            
            # Save the downloaded PDF to a local file
            with open(local_pdf, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            pdf_path = local_pdf  # Set path to downloaded file
        except requests.RequestException as e:
            print(f"Error downloading PDF: {e}")
            return None

    # Extract text from the PDF
    try:
        doc = fitz.open(pdf_path)
        text = "\n".join([page.get_text("text") for page in doc])
        doc.close()  # ✅ Properly close the document before returning
    except Exception as e:
        print(f"Error extracting text: {e}")
        return None
    
    # Prompt for consistent Gemini summaries
    prompt = """
        You are an expert AI researcher and technical writer. Your task is to analyze and summarize the following AI research paper, focusing on new discoveries, theoretical advancements, practical applications, and potential impact.

        ### **Instructions:**
        **Identify Key Contributions:**
           - What are the paper's major findings or innovations?
           - How does it compare to prior work in the field?
           - What are the implications for future research or real-world applications?

        **Explain Complex Concepts Clearly:**
           - Break down difficult ideas in an accessible way without oversimplifying.
           - Provide analogies or context when needed.
           - Reference specific passages or sentences from the paper to support explanations.

        **Evaluate Benchmarks & Experimental Results (if applicable):**
           - If benchmarks are tested, summarize performance improvements over previous models.
           - Highlight any significant progress made in areas such as accuracy, efficiency, or scalability.
           - Quantify improvements using specific metrics (e.g., "achieved a 5.2% increase in accuracy on ImageNet").

        **Discuss Limitations & Open Questions:**
           - What are the limitations acknowledged by the authors?
           - Are there any concerns or gaps in their methodology?
           - What follow-up research questions emerge from this work?

        **Assess Broader Impact:**
           - How might this research influence AI development, industry applications, or scientific understanding?
           - Are there ethical, societal, or safety concerns?
           - Could this be a stepping stone toward AGI, better interpretability, or more efficient computing?

        ---
        ### **Response Format (Example Structure)**
        **Title & Authors:**  
           "Title of the Paper" by [Authors]

        **Summary of Key Findings**  
           - [Summarize the most important contributions]  
           - Reference supporting sections: "According to section 3.2, the method introduced improves..."

        **Complex Concepts Explained**  
           - "The authors introduce X, which functions as... (Reference: Page 5, Section 4.1)"  
           - Provide accessible explanations.

        **Benchmark Results & Comparisons**  
           - "On the SuperGLUE benchmark, this model achieved X% improvement over previous state-of-the-art (Reference: Table 2)."

        **Limitations & Future Work**  
           - "The authors acknowledge that... (Reference: Section 6)"  
           - Discuss research gaps or unresolved questions.

        **Potential Impact**  
           - "This research could impact AI scaling laws by... (Reference: Section 7)"  
           - Consider long-term implications.

        ---
        Please structure your response following this format, referencing specific sections when possible.
        """
    
    try:
        response = llm_model.generate_content(prompt + text)
        
        if not response or not response.text:
            raise ValueError("Gemini returned an empty response.")

        return response.text.strip()
    except Exception as e:
        print(f"Error with Gemini text extraction: {e}")
        return None


def get_top_papers(papers, num, debug=False):
    """
    Retrieves the top-ranked papers based on their scores.
    """
    if debug:
        print(f"📊 Scoring {len(papers)} papers...")

    with SessionLocal() as db:  # Open DB session
        for paper in papers:
            if 'score' not in paper or paper['score'] == 0:
                paper['score'] = float(score_paper(paper)[0])  # Score has not been generated, generate and ensure it's a float
            else:
                existing_score = db.query(PaperScore.score).filter(PaperScore.title == paper['title']).scalar()
                if existing_score is not None:
                    print("Paper already scored")
                    paper['score'] = float(existing_score)  # ✅ Convert score to float

    if debug:
        print(f"📈 Scoring complete.")

    # Sort papers by score
    papers = sorted(papers, key=lambda x: float(x['score']), reverse=True)  # ✅ Ensure float before sorting

    # Select the top N papers
    top_papers = papers[:num]

    return top_papers

TOP_RESEARCHERS = set(load_top_ai_researchers())  # Store as a set for fast lookup
TRENDING_KEYWORDS = [
    # Core AI & LLM Scaling
    "LLM", "large language model", "scaling laws", "sparse models", 
    "transformer efficiency", "neural network pruning", "model compression", 
    "parameter-efficient fine-tuning", "PEFT", "mixture of experts", "MoE", 
    "low-rank adaptation", "LoRA", "efficient training", "gradient accumulation", 
    "distributed training", "TPU optimization", "GPU optimization", 
    "adaptive computation", "RLHF", "reinforcement learning from human feedback", 
    "chain-of-thought", "CoT", "self-supervised learning", "continual learning", 
    "auto-regressive models", "zero-shot learning", "few-shot learning", 
    "memory-augmented neural networks", "attention mechanisms", 
    "transformer alternatives", "state space models", "SSM", "Mamba", 
    "retrieval-augmented generation", "RAG", "latent variable models", 
    "knowledge distillation", "contrastive learning", "tokenizer-free models", 
    "multi-modal AI", "multi-modal learning", "open source", "open-source", "open source model"
]

def score_paper(paper, debug=False):
    """
    Assigns a score to an AI paper based on authorship, topic relevance, and clarity.
    """
    
    if debug:
        print("Scoring paper" + paper['title'])
    
    score = 0
    score_breakdown = {
        "Top Researcher Bonus": 0,
        "Trending Keywords Bonus": 0,
        "Recency Boost": 0,
        "Relevance Score": 0,
        "Insightfulness Score": 0,
        "Novelty Score": 0,
        "Impact Score": 0,
        "Final Score": 0
    }
    
    # If paper has already been scored, save some tokens and take existing score.   
    with SessionLocal() as db:
        existing_score = db.query(PaperScore.score).filter(PaperScore.title == paper['title']).scalar()
        if existing_score is not None:
            print("Paper already scored")
            return float(existing_score), score_breakdown 
    
    

    # Boost if a top AI researcher is an author
    if any(author in TOP_RESEARCHERS for author in paper['authors']):
        score_breakdown["Top Researcher Bonus"] = 5
        score += 5  # High weight for top AI researchers

    # 2Boost papers covering trending AI research topics
    for keyword in TRENDING_KEYWORDS:
        if re.search(rf"\b{keyword}\b", paper['title'], re.IGNORECASE) or \
           re.search(rf"\b{keyword}\b", paper['summary'], re.IGNORECASE):
            if score_breakdown["Trending Keywords Bonus"] < 12:
                score_breakdown["Trending Keywords Bonus"] += 3  # Accumulate topic relevance
                score += 3  # Medium weight for trending topics

    # Boost newer papers (favor those in the last 2-3 weeks)
    try:
        today = datetime.now(pytz.utc)  # ✅ Ensure `today` is timezone-aware (UTC)
        
        # ✅ Convert `paper['published']` to a timezone-aware datetime (UTC)
        if isinstance(paper['published'], datetime):
            published_date = paper['published'].astimezone(pytz.utc)
        else:
            published_date = datetime.strptime(paper['published'], "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.utc)
        
        days_since_published = (today - published_date).days

        if days_since_published <= 100:
            recency_boost = math.log10(100/(days_since_published+1)) * 2
            score_breakdown["Recency Boost"] = recency_boost
            score += recency_boost
    except Exception as e:
        print(f"Error parsing date: {e}")

    # Evaluate paper with Gemini 2.0 Flash
    gemini_scores = evaluate_paper_with_gemini(paper['title'], paper['summary'])

    if gemini_scores:
        score_breakdown["Relevance Score"] = gemini_scores["relevance"]
        score_breakdown["Insightfulness Score"] = gemini_scores["insightfulness"]
        score_breakdown["Novelty Score"] = gemini_scores["novelty"]
        score_breakdown["Impact Score"] = gemini_scores["impact"]

        # Adjust score based on LLM evaluation
        llm_score = (
            gemini_scores["relevance"] * 1.2 +  
            gemini_scores["insightfulness"] * 1.3 +  
            gemini_scores["novelty"] * 1.5 +  
            gemini_scores["impact"] * 1.4  
        ) / 12  # Normalize scores
        
        score += llm_score

    score_breakdown["Final Score"] = score
    
    # Write score to database
    with SessionLocal() as db:
        db_paper = PaperScore(title=paper['title'], score=score)
        db.add(db_paper)
        db.commit()


    return score, score_breakdown

# The following code was used in testing functions and remains for future debugging purposes
# This code contributes no functionality to the program, as this file is primarily for function exports

you_are_testing = False

if you_are_testing:
    weekly_fill = False

    if weekly_fill:
        from sqlalchemy import and_
        from models import DailyPaper, WeeklyPaper
        from datetime import datetime, timedelta, timezone

        # Create a new session
        db = SessionLocal()

        # Define the time range: from one week ago to now (in UTC)
        today = datetime.now(timezone.utc)
        week_ago = today - timedelta(days=7)

        # Query all DailyPaper records in the past week
        daily_papers_db = db.query(DailyPaper).filter(
            and_(
                DailyPaper.published >= week_ago,
                DailyPaper.published <= today
            )
        ).all()

        # Convert the SQLAlchemy models to dictionaries
        papers_list = []
        for paper in daily_papers_db:
            papers_list.append({
                "title": paper.title,
                "summary": paper.summary,
                "authors": paper.authors.split(", "),  # assuming authors stored as comma-separated string
                "link": paper.link,
                "published": paper.published,
                # Optionally use existing score, or recalc using your scoring function:
                "score": paper.score if paper.score is not None else 0
            })

        # Recalculate the scores (if needed)
        for paper in papers_list:
            if paper["score"] == 0:
                calculated_score, _ = score_paper(paper)
                paper["score"] = calculated_score

        # Sort papers by score (highest first)
        papers_list = sorted(papers_list, key=lambda p: p["score"], reverse=True)

        # Select the top 5 papers
        top_weekly_papers = papers_list[:5]

        # Store these top weekly papers in the WeeklyPaper table
        store_papers_in_db(top_weekly_papers, "weekly", debug=True)

        db.close()


    historic_fill = False

    if historic_fill:
        papers = fetch_papers_historical(debug=True, start_day="2025-03-05", end_day="2025-03-11", max_results=2000)

        print("Got papers, storing in database...")

        database_papers = []

        for day_papers in papers:
            top_papers = get_top_papers(day_papers, 5, debug=True)
            print("Scored top papers for the day.")

            for paper in top_papers:
                database_papers.append(paper)

        print("Storing all papers in the database...")


        store_papers_in_db(database_papers, "daily", debug=True)


    normal_fill = False

    if normal_fill:
        papers = fetch_ai_papers(250, debug=True)

        while len(papers) < 1:
            papers = fetch_ai_papers(250, debug=True)

        day_papers = papers[0]
        recent_papers = papers[1]

        top_papers = get_top_papers(day_papers, 5, debug=True)
        top_recent_papers = get_top_papers(recent_papers, 5, debug=True)

        store_papers_in_db(top_papers, "daily", debug=True)
        store_papers_in_db(top_recent_papers, "recent", debug=True)