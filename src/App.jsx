import React, { useState } from "react";
import PaperList from "./components/PaperList";
import PaperDetail from "./components/PaperDetail";
import "./global.css"; // make sure this includes your new global styles

function App() {
  const [selectedPaper, setSelectedPaper] = useState(null);
  const [chatMode, setChatMode] = useState(false);
  const [selectedSummary, setSelectedSummary] = useState(null);

  const handleSelectPaper = (paper, mode) => {
    setSelectedPaper(paper);
    setChatMode(mode);
    setSelectedSummary(mode ? paper.summary : paper.pdf_summary);
  };

  return (
    <div className="main_container">
      <PaperList onSelectPaper={handleSelectPaper} />
      <PaperDetail
        paper={selectedPaper}
        chatMode={chatMode}
        selectedSummary={selectedSummary}
      />
    </div>
  );
}

export default App;
