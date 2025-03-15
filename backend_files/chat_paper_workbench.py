"""
AI Paper Embedding & Retrieval System

This script provides functions for the following:
- Extracts text from PDFs.
- Chunks text for embedding.
- Stores and retrieves embeddings using FAISS.
- Uses OpenAI for embedding generation.
- Uses Gemini to generate contextual responses.

Supports retrieval-augmented generation (RAG) by querying relevant context.
"""

import aiohttp
import aiofiles
import fitz  # PyMuPDF for PDF handling
import tiktoken
from openai import OpenAI
import google.generativeai as genai
import faiss
import numpy as np
import asyncio
import time
import os

# Configure API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
llm_model = genai.GenerativeModel('gemini-2.0-flash')
client = OpenAI(api_key=OPENAI_API_KEY)


class VectorDB:
    """
    FAISS-based vector database for storing and retrieving embeddings by paper title.
    """
    def __init__(self, embedding_dim=1536):
        self.indexes = {}  # Dictionary to store separate FAISS indexes per paper title
        self.metadata = {}  # Metadata for each paper

    def add(self, paper_title, embeddings, metadata):
        """
        Adds embeddings and metadata to a FAISS index specific to a paper.
        """
        if paper_title not in self.indexes:
            self.indexes[paper_title] = faiss.IndexFlatL2(len(embeddings[0]))  # Create new index
            self.metadata[paper_title] = []

        self.indexes[paper_title].add(np.array(embeddings, dtype=np.float32))
        self.metadata[paper_title].extend(metadata)

        print(f"✅ Added {len(embeddings)} embeddings for paper '{paper_title}'.")

    def search(self, paper_title, query_embedding, top_k=5):
        """
        Searches for relevant embeddings within the FAISS index of a specific paper.
        """
        if paper_title not in self.indexes or self.indexes[paper_title].ntotal == 0:
            print(f"⚠️ No FAISS index found for '{paper_title}'.")
            return []

        query_embedding = np.array([query_embedding], dtype=np.float32)
        distances, indices = self.indexes[paper_title].search(query_embedding, top_k)

        results = []
        for j, i in enumerate(indices[0]):
            if i < len(self.metadata[paper_title]):
                results.append((self.metadata[paper_title][i], distances[0][j]))

        return results


def chunk_text(text, max_tokens=1024):
    """
    Splits text into smaller chunks for embedding.
    """
    tokenizer = tiktoken.get_encoding("cl100k_base")
    words = text.split()

    chunks, current_chunk = [], []
    token_count = 0

    for word in words:
        token_count += len(tokenizer.encode(word))
        if token_count > max_tokens:
            chunks.append(" ".join(current_chunk))
            current_chunk, token_count = [], len(tokenizer.encode(word))
        current_chunk.append(word)

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


async def pdf_to_text_async(pdf_url):
    """
    Asynchronously downloads and extracts text from a PDF.
    """
    local_pdf = "temp_paper.pdf"
    
    if pdf_url.startswith("http"):
        start_download = time.time()
        async with aiohttp.ClientSession() as session:
            async with session.get(pdf_url, timeout=5) as response:
                if response.status != 200:
                    print("Error: PDF download failed.")
                    return None
                async with aiofiles.open(local_pdf, "wb") as file:
                    await file.write(await response.read())

        download_time = time.time() - start_download
        print(f"⏳ PDF async download took {download_time:.4f} seconds")
        pdf_path = local_pdf
    else:
        pdf_path = pdf_url

    try:
        start_text_extract = time.time()
        doc = fitz.open(pdf_path)
        text = []
        for page in doc:
            page_text = page.get_text("text", flags=1)
            if "REFERENCES\n[1]" in page_text:
                text.append(page_text.split("REFERENCES\n[1]")[0])
                break
            text.append(page_text)
        doc.close()
        extract_time = time.time() - start_text_extract
        print(f"⏳ PDF text extraction took {extract_time:.4f} seconds")
        return "\n".join(text)
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return None


async def generate_embeddings_batch_async(text_chunks):
    """
    Generates embeddings asynchronously for multiple text chunks in a single API call.
    """
    if not text_chunks:
        return []

    try:
        response = await asyncio.to_thread(
            client.embeddings.create,
            model="text-embedding-3-small",
            input=text_chunks
        )
        return [item.embedding for item in response.data]
    except Exception as e:
        print(f"Error generating batch embeddings: {e}")
        return [None] * len(text_chunks)


async def process_paper(title, text, vector_db):
    """
    Asynchronously embeds and stores a paper in the vector database using batch processing.
    """
    if title in vector_db.metadata:
        print(f"✅ Paper '{title}' already processed. Skipping.")
        return

    chunks = chunk_text(text)
    embeddings = await generate_embeddings_batch_async(chunks)

    valid_embeddings = [emb for emb in embeddings if emb is not None]
    valid_metadata = [{"title": title, "chunk_index": i, "text": chunk} for i, chunk in enumerate(chunks)]

    if valid_embeddings:
        vector_db.add(title, valid_embeddings, valid_metadata)  # ✅ Now uses title-specific FAISS index
        print(f"✅ Paper '{title}' embedded and stored in VectorDB.")
    else:
        print(f"❌ No valid embeddings for '{title}'.")



async def fetch_relevant_context(query, paper_title, vector_db):
    """
    Retrieves the most relevant document chunks for a query within the given paper's FAISS index.
    """
    start_time = time.time()
    query_embedding = await generate_embeddings_batch_async([query])
    if not query_embedding:
        print(f"⚠️ Failed to generate embedding for query: {query}")
        return "No relevant context found."

    query_embedding = query_embedding[0]

    start_faiss = time.time()
    relevant_chunks = vector_db.search(paper_title, query_embedding, top_k=5)  # ✅ Now only searches within this paper's index
    faiss_time = time.time() - start_faiss

    if not relevant_chunks:
        print(f"⚠️ No relevant context found for '{paper_title}'!")
        return "No relevant context found."

    print(f"⏳ FAISS search took {faiss_time:.4f} seconds")
    print(f"✅ Retrieved {len(relevant_chunks)} chunks for '{paper_title}':")

    return "\n".join([chunk[0]["text"] for chunk in relevant_chunks])


async def query_gemini(user_input, vector_db, title):
    """
    Retrieves relevant chunks and queries Gemini for a response.
    """
    context = await fetch_relevant_context(f"Paper title: {title}\nUser input: {user_input}", vector_db)

    prompt = f"""
    ### Paper: **{title}**
    **Context:**
    {context}

    **User Question:**
    {user_input}

    """

    start_gemini = time.time()
    response = llm_model.generate_content(
        prompt,
        generation_config={"max_output_tokens": 512}  # Limiting response length
    )
    gemini_time = time.time() - start_gemini
    print(f"⏳ Gemini response took {gemini_time:.4f} seconds")

    return response.text.strip()


async def query_gemini_stream(user_input, title):
    """
    Streams AI-generated responses using Google's Gemini API with context retrieval.
    """
    try:
        # ✅ Retrieve context from VectorDB
        context = await fetch_relevant_context(user_input, title, GLOBAL_VECTOR_DB)
        
        print("User input" + str(user_input))

        print(f"✅ Using Context:\n{context[:500]}...")  # Debugging: Show first 500 chars

        # ✅ Start a chat session
        chat = llm_model.start_chat(history=[])

        # ✅ Include context in the query
        full_prompt = f"""
        ### Paper: **{title}**
        **Context:**
        {context}

        **User Question:**
        {user_input}
        """

        response = chat.send_message(full_prompt, stream=False) 

        if not response.text:
            yield "Error: No response from Gemini."
            return

        # ✅ Simulate streaming by chunking response
        chunk_size = 50  # Adjust chunk size
        response_text = response.text.strip()
        
        for i in range(0, len(response_text), chunk_size):
            yield response_text[i : i + chunk_size]
            await asyncio.sleep(0.025)  # Simulate network delay

    except Exception as e:
        print(f"❌ Error in streaming Gemini response: {e}")
        yield "Error generating response."

async def query_with_context(user_input, pdf_link, title, debug=False):
    """
    Queries the VectorDB and Gemini for a response.
    Assumes the paper is already preprocessed.
    """
    start_total = time.time()

    # ✅ Ensure the paper is already processed
    if not any(meta["title"] == title for meta in GLOBAL_VECTOR_DB.metadata):
        print(f"⚠️ Paper '{title}' was not preloaded! Preloading now...")
        await preload_paper(title, pdf_link)

    # ✅ Retrieve relevant context and query Gemini
    start_gemini = time.time()
    response = await query_gemini_stream(user_input, GLOBAL_VECTOR_DB, title)
    gemini_time = time.time() - start_gemini
    print(f"⏳ Gemini response took {gemini_time:.4f} seconds")

    total_time = time.time() - start_total
    print(f"⏳ Total API response time: {total_time:.4f} seconds")

    return response

async def preload_paper(title, pdf_link):
    """
    Pre-processes a paper when the chat window opens.
    Extracts text and stores embeddings in VectorDB.
    """
    # ✅ Check if the paper is already processed
    if title in GLOBAL_VECTOR_DB.metadata:
        print(f"✅ Skipping preprocessing: Paper '{title}' already in VectorDB.")
        return

    print(f"🔄 Preloading paper '{title}' in background...")

    # ✅ Extract text from PDF
    start_pdf = time.time()
    text = await pdf_to_text_async(pdf_link)
    pdf_time = time.time() - start_pdf
    print(f"⏳ PDF processing took {pdf_time:.4f} seconds")

    if not text:
        print(f"❌ Error: Unable to extract text for '{title}'.")
        return

    # ✅ Generate embeddings and store in FAISS
    start_embed = time.time()
    await process_paper(title, text, GLOBAL_VECTOR_DB)
    embed_time = time.time() - start_embed
    print(f"⏳ Embedding processing took {embed_time:.4f} seconds")

    print(f"✅ Preloaded '{title}' successfully!")


# Global instance of the vector database to avoid reprocessing papers on every query.
GLOBAL_VECTOR_DB = VectorDB()