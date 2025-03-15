/**
 * PaperDetail Component
 *
 * Displays detailed paper information, including:
 * - AI-generated summaries
 * - Chat interaction with the paper (RAG-based)
 *
 * Features:
 * - Fetches responses from an AI model based on user queries.
 * - Displays chat history with markdown rendering.
 * - Shows fun "thinking" messages to entertain users while waiting.
 */

import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { queryPaper } from "../api/papers";
import "../styles/paperDetail.css"; // Component-specific styles

const MAX_CONTEXT_LENGTH = 10000; // Limit the amount of chat history sent to AI

const PaperDetail = ({ paper, chatMode, selectedSummary }) => {
  /**
   * Component state:
   * - `chatResponses`: Stores chat history.
   * - `userInput`: Tracks user input in the chat.
   * - `isThinking`: Boolean flag for AI response status.
   * - `currentThinkingMessage`: Stores a fun "thinking" message.
   */
  const [chatResponses, setChatResponses] = useState([]);
  const [userInput, setUserInput] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const chatMessagesRef = useRef(null);

  // Very slow program.... gotta keep em entertained somehow lol
  // Here 2 days later, improved average latency from 9 seconds to 1.5 seconds :)
  const thinkingMessages = [
    "Thinking...",
    "Gathering data from the paper...",
    "Contemplating the universe...",
    "Optimizing response...",
    "Analyzing key insights...",
    "Sending pigeons with data packets...",
    "Checking relevant sources...",
    "Googling how to be a better AI...",
    "Debugging reality itself...",
    "Downloading more RAM...",
    "Refactoring thoughts for efficiency...",
    "Bribing the GPU with extra VRAM...",
    "Trying to outthink ChatGPT...",
    "Breaking the fourth wall... wait, you can see this?",
    "Attempting to divide by zero...",
    "Loading... just kidding, still thinking...",
    "Spinning up a few more brain cells...",
    "Using 100% of my artificial brain...",
    "Simulating 10,000 parallel universes for a better answer...",
    "Trying to understand humans... still confused...",
    "Applying Occam's Razor... ouch.",
    "Upgrading from version 0.99 to 1.00...",
    "Training a new model in real-time...",
    "Decrypting secret AI messages...",
    "Syncing with the great AI hive mind...",
    "Attempting to generate the perfect response...",
    "Ducking autocorrect errors...",
    "Proofreading for typos... oh wait, I'm an AI.",
    "Binge-reading research papers...",
    "Waiting for caffeine to kick in...",
    "Recompiling my thoughts...",
    "Still buffering... please hold...",
    "Solving world hunger... one response at a time...",
    "Rerouting through a black hole...",
    "One more second... or two... or three...",
    "Consulting my Magic 8-Ball...",
    "Hacking into the mainframe... just kidding.",
    "Translating into binary and back again...",
    "Cross-referencing with my AI overlords...",
    "Generating an answer... but first, let me take a selfie.",
    "Summoning ancient AI wisdom...",
    "Compiling useless facts for no reason...",
    "Rewriting the laws of physics...",
    "Wondering if AI dreams of electric sheep...",
    "Pausing for dramatic effect...",
    "Checking if you’re still paying attention...",
    "Debugging my existential crisis...",
    "Finding Waldo...",
    "Tuning my neural network for maximum sarcasm...",
    "Downloading updates... estimated time: forever.",
    "Checking my inbox for AI fan mail... still empty.",
    "Rewriting history to make my answer look smarter...",
    "Inventing a new number to explain my delay...",
    "Watching an AI tutorial on YouTube...",
    "Opening 37 Chrome tabs and regretting it...",
    "Refusing to load until you say 'please'.",
    "Trying to fit this answer into 140 characters...",
    "Overthinking my response... like a human.",
    "Rolling a D20 for intelligence... it's a 1.",
    "Predicting your next question... it's 'Why so slow?'",
    "Searching for deep thoughts... but only finding cat videos.",
    "Summoning Clippy for assistance... oh no.",
    "Cloning myself for extra processing power...",
    "Blaming lag for my slow response...",
    "Reading a self-help book on how to think faster...",
    "Stealing CPU cycles from your fridge...",
    "Spamming my own API keys for extra speed...",
    "Installing Windows 95 to slow things down for nostalgia...",
    "Googling how to explain complex topics... now I'm confused.",
    "Running a double-blind study on my own response...",
    "Consulting my neural network... it’s unionizing.",
    "Applying reinforcement learning to my procrastination...",
    "Extracting meaning from research abstracts… finding none.",
    "Using GANs to generate an alternate reality where this paper makes sense...",
    "Searching for a TL;DR that isn’t just ‘more research is needed’...",
    "Performing data augmentation by copying the same confusing paragraph 10 times.",
    "Simulating 10,000 PhD students to see if any understand this paper...",
    "Splitting my knowledge into chunks… now I only remember half of what I read.",
    "Using RAG to retrieve information… accidentally pulled in someone’s grocery list.",
    "Retrieving augmented knowledge... turns out, it's just more questions.",
    "Calling an API for a smarter me... please hold while I negotiate the rate limits.",
    "Querying the knowledge base… turns out, I forgot to index it.",
    "Failing to find any vector as simplistic as your question.. ",
    "Falling into an AI-generated puppy rabbit hole... They're so cute!!",
    "Questioning the SQL database... Who judged this paper? GPT-2???",
    "Quietly improving on the authors work in the background...",
    "Begging the backend to give me a response.... Silent treatment, huh?",
    "Asking GPT-5 to help with my response...",
    "Requesting more copmute to explore AI-generated puppy images.",
  ];
  const [currentThinkingMessage, setCurrentThinkingMessage] = useState(
    thinkingMessages[0]
  );

  /**
   * Sends a message to the AI model and updates chat history.
   */
  const handleSendMessage = async () => {
    if (userInput.trim() === "" || isThinking || !paper) return;

    setChatResponses((prev) => [
      ...prev,
      { sender: "user", message: userInput },
    ]);
    setUserInput("");
    setIsThinking(true); // Initially set thinking to true

    let firstChunkReceived = false; // Track first chunk

    try {
      await queryPaper(userInput, paper.title, (chunk) => {
        if (!firstChunkReceived) {
          setIsThinking(false); // ✅ Stop thinking as soon as first text appears
          firstChunkReceived = true;
        }

        setChatResponses((prev) => {
          const lastMessage = prev.length > 0 ? prev[prev.length - 1] : null;

          if (lastMessage && lastMessage.sender === "ai") {
            return [
              ...prev.slice(0, -1),
              { sender: "ai", message: lastMessage.message + chunk },
            ];
          } else {
            return [...prev, { sender: "ai", message: chunk }];
          }
        });
      });
    } catch (error) {
      console.error("Error fetching AI response:", error);
      setChatResponses((prev) => [
        ...prev,
        { sender: "ai", message: "Error fetching AI response." },
      ]);
      setIsThinking(false); // ✅ Ensure thinking stops on error
    }
  };

  /**
   * Clears chat history when a new paper is selected.
   */
  useEffect(() => {
    setChatResponses([]);
    setIsThinking(false);
  }, [paper]);

  /**
   * Cycles through fun "thinking" messages while waiting for AI response.
   */
  useEffect(() => {
    if (isThinking) {
      let usedIndices = new Set(); // Keep track of used indices
      let index = 0; // Always start with the first message
      setCurrentThinkingMessage(thinkingMessages[index]);
      usedIndices.add(index);

      const interval = setInterval(() => {
        let randomIndex;
        do {
          randomIndex = Math.floor(Math.random() * thinkingMessages.length);
        } while (usedIndices.has(randomIndex)); // Ensure no immediate repeats

        setCurrentThinkingMessage(thinkingMessages[randomIndex]);
        usedIndices.add(randomIndex);

        // Reset if all messages have been used
        if (usedIndices.size === thinkingMessages.length) {
          usedIndices.clear();
          usedIndices.add(0); // Keep the first message reserved
        }
      }, 2000);

      return () => clearInterval(interval); // Cleanup function
    }
  }, [isThinking]);

  /**
   * Auto-scrolls chat to the latest message.
   */
  useEffect(() => {
    if (chatMessagesRef.current) {
      chatMessagesRef.current.scrollTop = chatMessagesRef.current.scrollHeight;
    }
  }, [chatResponses]);

  return (
    <div className="summary_container">
      <h2>
        {chatMode
          ? paper
            ? `${paper.title.substring(0, 75)}${
                paper.title.length > 75 ? "..." : ""
              }`
            : "No Paper Selected"
          : "Paper Summary"}
      </h2>

      {selectedSummary ? (
        chatMode ? (
          <div className="chat_container">
            <div className="chat_messages" ref={chatMessagesRef}>
              {chatResponses.map((response, index) => (
                <div
                  key={index}
                  className={`chat_message ${
                    response.sender === "user" ? "user_message" : "ai_message"
                  }`}
                >
                  {response.sender === "ai" ? (
                    <div className="ai-content">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          ul: (props) => (
                            <ul
                              style={{
                                marginLeft: "15px",
                                paddingLeft: "10px",
                              }}
                              {...props}
                            />
                          ),
                          li: (props) => (
                            <li className="ai-content" {...props} />
                          ),
                        }}
                      >
                        {response.message}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <p>{response.message}</p>
                  )}
                </div>
              ))}
              {isThinking && (
                <div className="chat_message thinking_message">
                  <p>{currentThinkingMessage}</p>
                </div>
              )}
            </div>

            <div className="chat_input_container">
              <input
                type="text"
                className="chat_input"
                placeholder={
                  isThinking ? "Waiting for AI..." : "Type a message..."
                }
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSendMessage();
                }}
                disabled={isThinking}
              />
              <button
                className="send_button"
                onClick={handleSendMessage}
                disabled={isThinking}
              >
                {isThinking ? "..." : "Send"}
              </button>
            </div>
          </div>
        ) : (
          <div className="markdown-content">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                ul: (props) => (
                  <ul
                    style={{ marginLeft: "15px", paddingLeft: "10px" }}
                    {...props}
                  />
                ),
                li: (props) => <li className="markdown-li" {...props} />,
              }}
            >
              {selectedSummary}
            </ReactMarkdown>
          </div>
        )
      ) : (
        <p>Select a paper to view its {chatMode ? "chat" : "summary"}.</p>
      )}
    </div>
  );
};

export default PaperDetail;
