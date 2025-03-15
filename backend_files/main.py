"""
FastAPI Backend for AI Paper Retrieval & Querying

This module provides:
1. **Paper Storage & Retrieval APIs**
   - Store new papers in recent/daily/weekly tables.
   - Fetch top-scoring papers.
   - Fetch papers by date.

2. **Retrieval-Augmented Generation (RAG) API**
   - Queries AI papers using OpenAI embeddings & Gemini.

3. **CORS Configuration**
   - Allows cross-origin requests for frontend compatibility.
"""

from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base
import crud
from chat_paper_workbench import query_with_context, preload_paper, query_gemini_stream, GLOBAL_VECTOR_DB
from pydantic import BaseModel
from datetime import date
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import Optional
from scheduler import run_scheduled_tasks
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Enable CORS (Development Mode: Allows All Origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://calculator5329.github.io", "https://calculator5329.github.io/ai-papers/"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure database tables are created
Base.metadata.create_all(bind=engine)


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class QueryRequest(BaseModel):
    """
    Request model for querying a research paper.
    """
    user_query: str
    title: str
    pdf_link: Optional[str] = None 


class PaperRequest(BaseModel):
    """
    Request model for adding a new paper.
    """
    title: str
    summary: str
    pdf_summary: str
    ai_summary: str
    authors: str
    link: str
    published: date
    score: float

@app.get("/run_scheduler/")
def run_scheduler():
    """Triggers scheduled tasks manually via HTTP."""
    logger.info("🚀 Received request at /run_scheduler/")
    
    try:
        run_scheduled_tasks()
        logger.info("✅ Successfully executed scheduled tasks!")
        return {"message": "Scheduled tasks executed successfully."}
    except Exception as e:
        logger.error(f"❌ Error executing scheduled tasks: {e}")
        return {"error": str(e)}

@app.post("/add_paper/{table}/")
def add_paper(table: str, paper_data: PaperRequest, db: Session = Depends(get_db)):
    """
    Adds a paper to the specified database table.
    """
    if table not in ["recent", "daily", "weekly"]:
        raise HTTPException(status_code=400, detail="Invalid table name")
    
    paper_dict = paper_data.dict()
    return crud.create_paper(db, paper_dict, table)


async def stream_response(user_query, title):
    """
    Wraps the Gemini streaming function for FastAPI.
    """
    async for chunk in query_gemini_stream(user_query, title):
        yield chunk

@app.post("/query_paper/")
async def query_paper(request: QueryRequest):
    """
    Streams AI-generated responses from Gemini in real time.
    """
    return StreamingResponse(
        stream_response(request.user_query, request.title),
        media_type="text/plain"
    )

@app.get("/top_papers/{table}/")
def top_papers(table: str, limit: int = 5, db: Session = Depends(get_db)):
    """
    Fetches the top-scoring papers from a specific table.
    """
    if table not in ["recent", "daily", "weekly"]:
        raise HTTPException(status_code=400, detail="Invalid table name")

    return crud.get_papers(db, table, limit)


@app.get("/top_papers_by_date/{table}/")
def top_papers_by_date(
    table: str,
    target_date: date = Query(None),
    limit: int = 5,
    db: Session = Depends(get_db),
):
    """
    Fetches the top-scoring papers for a specific date from a given table.
    """
    if table not in ["recent", "daily", "weekly"]:
        raise HTTPException(status_code=400, detail="Invalid table name")

    return crud.get_papers_by_date(db, table, target_date, limit)

class PreloadRequest(BaseModel):
    title: str
    pdf_link: str

@app.post("/preload_paper/")
async def preload_paper_api(request: PreloadRequest, background_tasks: BackgroundTasks):
    print(f"Received: title={request.title}, pdf_link={request.pdf_link}")  # ✅ Debugging log
    background_tasks.add_task(preload_paper, request.title, request.pdf_link)
    return {"message": f"Preloading started for '{request.title}'"}
