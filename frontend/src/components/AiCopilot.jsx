import { useState, useRef, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { analyzeText, analyzeFile, addUserMessage } from '../store/complaintSlice';
import './AiCopilot.css';

function renderContent(content) {
  return content
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br/>');
}

function ChatMessage({ msg }) {
  const isUser = msg.role === 'user';
  const isError = msg.isError;

  return (
    <div className={`chat-msg ${isUser ? 'chat-msg-user' : 'chat-msg-ai'} fade-in-up`}>
      {!isUser && (
        <div className={`chat-avatar ${msg.isSave ? 'avatar-save' : msg.isError ? 'avatar-error' : 'avatar-ai'}`}>
          {msg.isSave ? '✓' : msg.isError ? '!' : '✦'}
        </div>
      )}
      <div className={`chat-bubble ${isUser ? 'bubble-user' : isError ? 'bubble-error' : 'bubble-ai'}`}>
        <span dangerouslySetInnerHTML={{ __html: renderContent(msg.content) }} />
        {msg.isAnalysis && msg.severity && (
          <div className={`inline-severity severity-tag-${msg.severity.toLowerCase()}`}>
            {msg.severity}
          </div>
        )}
      </div>
      {isUser && (
        <div className="chat-avatar avatar-user">U</div>
      )}
    </div>
  );
}

function ProgressiveLoadingIndicator() {
  const stages = [
    'Extracting Complaint Details',
    'Running Risk Assessment',
    'Generating Executive Summary',
    'Root Cause Analysis (RCA)',
    'CAPA Action Recommendation',
    'Duplicate Complaint Detection',
  ];
  const [currentStage, setCurrentStage] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentStage((prev) => (prev < stages.length - 1 ? prev + 1 : prev));
    }, 700);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="chat-msg chat-msg-ai fade-in">
      <div className="chat-avatar avatar-ai">✦</div>
      <div className="chat-bubble bubble-ai processing-bubble">
        <div className="processing-header">
          <span className="spinner-sm" />
          <span className="processing-title">Analyzing Complaint...</span>
        </div>
        <div className="processing-stages-list">
          {stages.map((stage, idx) => {
            const isDone = idx < currentStage;
            const isCurrent = idx === currentStage;
            return (
              <div
                key={stage}
                className={`stage-item ${isDone ? 'stage-done' : isCurrent ? 'stage-current' : 'stage-pending'}`}
              >
                <span className="stage-icon">{isDone ? '✓' : isCurrent ? '⚡' : '○'}</span>
                <span className="stage-text">{stage}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default function AiCopilot() {
  const dispatch = useDispatch();
  const chat = useSelector(s => s.complaint.chat);
  const analysisStatus = useSelector(s => s.complaint.analysis.status);
  const [input, setInput] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const fileRef = useRef(null);
  const chatEndRef = useRef(null);

  // Auto-scroll on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chat, analysisStatus]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || analysisStatus === 'loading') return;
    dispatch(addUserMessage(trimmed));
    dispatch(analyzeText(trimmed));
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      dispatch(addUserMessage(`📎 Uploaded: ${file.name}`));
      dispatch(analyzeFile(file));
      e.target.value = '';
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      dispatch(addUserMessage(`📎 Dropped: ${file.name}`));
      dispatch(analyzeFile(file));
    }
  };

  const isLoading = analysisStatus === 'loading';

  return (
    <div
      className={`copilot-panel ${isDragging ? 'copilot-dragging' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
    >
      {/* ── Header ── */}
      <div className="copilot-header">
        <div className="copilot-title-row">
          <span className="copilot-icon">⬡</span>
          <div>
            <span className="copilot-title">AIVOA Copilot</span>
            <span className="copilot-subtitle">Powered by LangGraph + Groq</span>
          </div>
          <div className="copilot-online">
            <span className="online-dot" />
            <span>Online</span>
          </div>
        </div>
        <p className="copilot-hint">Drop complaint files or paste text below.</p>
      </div>

      {/* ── Drop Overlay ── */}
      {isDragging && (
        <div className="drop-overlay">
          <div className="drop-overlay-inner">
            <span className="drop-icon">📂</span>
            <span>Drop your file to analyze</span>
          </div>
        </div>
      )}

      {/* ── Chat Messages ── */}
      <div className="chat-messages">
        {chat.map(msg => (
          <ChatMessage key={msg.id} msg={msg} />
        ))}
        {isLoading && <ProgressiveLoadingIndicator />}
        <div ref={chatEndRef} />
      </div>

      {/* ── Input Area ── */}
      <div className="chat-input-area">
        <div className={`chat-input-wrapper ${isLoading ? 'input-loading' : ''}`}>
          <button
            id="attach-btn"
            className="attach-btn"
            title="Upload PDF, DOCX, or TXT"
            onClick={() => fileRef.current?.click()}
            disabled={isLoading}
          >
            📎
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.docx,.txt,.eml"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
          <textarea
            id="chat-input"
            className="chat-textarea"
            placeholder="Type a message or paste a complaint…"
            rows={1}
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              // Auto-grow
              e.target.style.height = 'auto';
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
            }}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
          />
          <button
            id="send-btn"
            className={`send-btn ${isLoading ? 'send-loading' : ''}`}
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
          >
            {isLoading ? <span className="spinner" /> : '↑'}
          </button>
        </div>
        <div className="powered-by">POWERED BY LANGGRAPH</div>
      </div>
    </div>
  );
}
