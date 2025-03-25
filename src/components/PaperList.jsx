import React, { useState, useEffect } from "react";
import axios from "axios";
import "../styles/paperList.css"; // Component-specific styles

const API_URL = "https://fastapi-backend-6f6whpbwma-uc.a.run.app/"; // Backend API endpoint

const PaperList = ({ onSelectPaper }) => {
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTable, setSelectedTable] = useState("recent");
  const [availableDates, setAvailableDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState(null);

  useEffect(() => {
    const fetchPapers = async () => {
      try {
        setLoading(true);
        let response;

        if (selectedTable === "daily") {
          response = await axios.get(
            `${API_URL}/top_papers_by_date/${selectedTable}/`,
            { params: { target_date: selectedDate, limit: 5 } }
          );
        } else {
          response = await axios.get(
            `${API_URL}/top_papers/${selectedTable}/`,
            {
              params: { limit: 5 },
            }
          );
        }

        setPapers(response.data);
      } catch (error) {
        console.error("Error fetching papers:", error);
        setPapers([]);
      } finally {
        setLoading(false);
      }
    };

    fetchPapers();
  }, [selectedTable, selectedDate]);

  useEffect(() => {
    const fetchAvailableDates = async () => {
      try {
        const response = await axios.get(`${API_URL}/available_daily_dates/`);
        setAvailableDates(response.data);

        // If current selectedDate is invalid (e.g. defaulted to a date with no data), fix it
        if (response.data.length > 0) {
          setAvailableDates(response.data);
          setSelectedDate((prev) =>
            response.data.includes(prev) ? prev : response.data[0]
          );
        }
      } catch (error) {
        console.error("Error fetching available daily dates:", error);
      }
    };

    if (selectedTable === "daily") {
      fetchAvailableDates();
    }
  }, [selectedTable]);

  /**
   * Preloads a paper's embeddings when "Chat About Paper" is clicked.
   */
  const preloadPaper = async (paper) => {
    try {
      const response = await fetch(`${API_URL}/preload_paper/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: paper.title, pdf_link: paper.link }),
      });

      const data = await response.json();
      console.log(data.message);
    } catch (error) {
      console.error("Error preloading paper:", error);
    }
  };

  return (
    <div className="papers_section">
      {/* Dropdown to select the paper category */}
      <select
        className="database_selector"
        value={selectedTable}
        onChange={(e) => setSelectedTable(e.target.value)}
      >
        <option value="recent">Recent Papers</option>
        <option value="daily">Daily Top Papers</option>
        <option value="weekly">Top Papers This Week</option>
      </select>

      <div className="papers_list_container">
        {/* Date picker for daily papers */}
        {selectedTable === "daily" && selectedDate && (
          <select
            className="date_picker"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            style={{ marginBottom: "10px" }}
          >
            {availableDates.map((date) => (
              <option key={date} value={date}>
                {date}
              </option>
            ))}
          </select>
        )}

        <div className="papers_scroll">
          {loading ? (
            <p>Loading...</p>
          ) : papers.length > 0 ? (
            papers.map((paper) => (
              <div key={paper.id} className="paper_container">
                <h3>{paper.title}</h3>
                <p>
                  {paper.summary.length > 500
                    ? `${paper.summary.substring(0, 200)}...`
                    : paper.summary}
                </p>
                <p>
                  <strong>Authors:</strong>{" "}
                  {paper.authors.split(",").slice(0, 3).join(", ")}
                  {paper.authors.split(",").length > 3 && " ..."}
                </p>

                {/* Paper action links */}
                <div style={{ textAlign: "center" }}>
                  <a
                    href="#"
                    className="summary_link"
                    onClick={(e) => {
                      e.preventDefault();
                      onSelectPaper(paper, false);
                    }}
                  >
                    Paper Summary
                  </a>
                  <span className="separator">|</span>
                  <a
                    href="#"
                    className="summary_link"
                    onClick={async (e) => {
                      e.preventDefault();
                      await preloadPaper(paper); // ✅ Preload paper first
                      onSelectPaper(paper, true);
                    }}
                  >
                    Chat About Paper
                  </a>
                  <span className="separator">|</span>
                  <a
                    href={paper.link}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    View Paper
                  </a>
                </div>
              </div>
            ))
          ) : (
            <p>No papers found for this date.</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default PaperList;
