/**
 * API Wrapper for interacting with the backend's paper-related endpoints.
 * Provides functions to:
 * - Fetch top AI research papers
 * - Fetch top papers by date
 * - Add a new research paper
 * - Query a paper using AI for insights (RAG)
 */

import axios from "axios";

const API_URL = "https://fastapi-backend-6f6whpbwma-uc.a.run.app"; // Backend API base URL

/**
 * Fetches the top research papers from a specified database table.
 *
 * @param {string} table - The database table to query (default: "recent").
 *                         Options: "recent", "daily", "weekly".
 * @param {number} limit - Number of papers to retrieve (default: 5).
 * @returns {Promise<Array>} - An array of paper objects.
 */
export const getTopPapers = async (table = "recent", limit = 5) => {
  try {
    const response = await axios.get(`${API_URL}/top_papers/${table}/`, {
      params: { limit },
    });
    return response.data;
  } catch (error) {
    console.error(`❌ Error fetching top papers from '${table}':`, error);
    return [];
  }
};

/**
 * Fetches top research papers from a specified table for a given date.
 *
 * @param {string} table - The database table to query (default: "recent").
 *                         Options: "recent", "daily", "weekly".
 * @param {string} selectedDate - The target date (format: "YYYY-MM-DD").
 * @param {number} limit - Number of papers to retrieve (default: 5).
 * @returns {Promise<Array>} - An array of paper objects.
 */
export const getTopPapersByDate = async (
  table = "recent",
  selectedDate,
  limit = 5
) => {
  try {
    const response = await axios.get(
      `${API_URL}/top_papers_by_date/${table}/`,
      {
        params: { target_date: selectedDate, limit },
      }
    );
    return response.data;
  } catch (error) {
    console.error(
      `❌ Error fetching papers for date ${selectedDate} in '${table}':`,
      error
    );
    return [];
  }
};

/**
 * Adds a new research paper entry to the specified database table.
 *
 * @param {string} table - The database table to insert into ("recent", "daily", "weekly").
 * @param {Object} paperData - The paper details (title, summary, authors, link, etc.).
 * @returns {Promise<Object|null>} - The newly added paper object or null on failure.
 */
export const addPaper = async (table, paperData) => {
  try {
    const response = await axios.post(
      `${API_URL}/add_paper/${table}/`,
      paperData
    );
    return response.data;
  } catch (error) {
    console.error(`❌ Error adding paper to '${table}':`, error);
    return null;
  }
};

/**
 * Queries a research paper using AI to extract insights based on a user query.
 *
 * @param {string} userQuery - The question/query about the paper.
 * @param {string} pdfLink - The URL of the paper's PDF.
 * @param {string} title - The title of the research paper.
 * @returns {Promise<string>} - AI-generated response or an error message.
 */
export const queryPaper = async (userQuery, title, onChunk) => {
  try {
    const response = await fetch(`${API_URL}/query_paper/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_query: userQuery, title }),
    });

    if (!response.body) throw new Error("No response body found.");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      console.log("🔹 Received Chunk:", chunk); // Debugging output
      onChunk(chunk); // Update UI with streamed data
    }
  } catch (error) {
    console.error("❌ Error querying paper:", error);
  }
};
