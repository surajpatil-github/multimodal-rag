"use client";
import { useState, useEffect } from "react";
import axios from "axios";
import ChatBox from "./components/ChatBox";
import FileUploader from "./components/FileUploader";

const API = process.env.NEXT_PUBLIC_API_URL!;

type DocMeta = {
  id: string;
  name: string;
};

export default function Home() {
  const [docId, setDocId] = useState<string | null>(null);
  const [docName, setDocName] = useState<string | null>(null);
  const [docs, setDocs] = useState<DocMeta[]>([]);
  const [search, setSearch] = useState("");
  const [theme, setTheme] = useState<"light" | "dark">("light");

  const filteredDocs = docs.filter(d =>
    d.name.toLowerCase().includes(search.toLowerCase())
  );

  const handleDocumentChange = (id: string, name: string) => {
    setDocId(id);
    setDocName(name);
    setDocs(prev => {
      if (prev.some(d => d.id === id)) return prev;
      return [...prev, { id, name }];
    });
  };

  const toggleTheme = () => {
    setTheme(prev => (prev === "light" ? "dark" : "light"));
  };

  const handleDeleteDocument = async (id: string) => {
    const target = docs.find(d => d.id === id);
    if (!target) return;
    if (typeof window !== "undefined") {
      const ok = window.confirm(`Delete "${target.name}" from your documents?`);
      if (!ok) return;
    }

    try {
      await axios.post(`${API}/delete_document`, { doc_id: id });
    } catch {
    }

    setDocs(prev => prev.filter(d => d.id !== id));
    setDocId(prev => (prev === id ? null : prev));
    setDocName(prev => (prev === target.name ? null : prev));
  };

  useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem("theme");
    if (stored === "light" || stored === "dark") {
      setTheme(stored);
      document.documentElement.setAttribute("data-theme", stored);
      return;
    }
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const initial = prefersDark ? "dark" : "light";
    setTheme(initial);
    document.documentElement.setAttribute("data-theme", initial);
  }, []);

  useEffect(() => {
    if (typeof document === "undefined") return;
    document.documentElement.setAttribute("data-theme", theme);
    if (typeof window !== "undefined") {
      window.localStorage.setItem("theme", theme);
    }
  }, [theme]);

  return (
    <main className="app-root">
      <div className="chat-shell">
        <header className="chat-header">
          <div>
            <h1 className="chat-title">Insight AI</h1>
            <p className="chat-subtitle">Your AI-powered knowledge partner.</p>
          </div>
          <div className="chat-theme-toggle">
            <button
              type="button"
              className="theme-toggle-btn"
              onClick={toggleTheme}
            >
              {theme === "light" ? "🌙 Dark" : "☀️ Light"}
            </button>
          </div>
        </header>
        <section className="chat-content">
          <div className="doc-pane">
            <div className="doc-history">
            <div className="doc-history-header-row">
              <div className="doc-history-title">
                <span className="doc-panel-icon">📄</span>
                <span>Your Documents</span>
                <span className="doc-count-pill">{docs.length}</span>
              </div>
            </div>

            <div className="doc-panel-controls">
              <input
                className="doc-search-input"
                placeholder="Search documents..."
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
              <FileUploader
                onUploaded={handleDocumentChange}
                existingNames={docs.map(d => d.name)}
                activeDocName={docName}
              />
            </div>

            {docs.length > 0 && (
              <div className="doc-list-grid">
                {filteredDocs.map(d => (
                  <div
                    key={d.id}
                    className={
                      "doc-row" + (d.id === docId ? " doc-row-active" : "")
                    }
                  >
                    <button
                      type="button"
                      className="doc-row-main"
                      onClick={() => {
                        setDocId(d.id);
                        setDocName(d.name);
                      }}
                    >
                      <span className="doc-row-main-left">
                        <span
                          className={
                            "doc-radio" + (d.id === docId ? " doc-radio-active" : "")
                          }
                        />
                        <span className="doc-file-icon">📄</span>
                        <span className="doc-name">{d.name}</span>
                      </span>
                      {d.id === docId && <span className="doc-inuse-badge">In use</span>}
                    </button>
                    <button
                      type="button"
                      className="doc-row-delete"
                      onClick={() => handleDeleteDocument(d.id)}
                      aria-label="Delete document"
                    >
                      <svg
                        viewBox="0 0 24 24"
                        aria-hidden="true"
                        className="doc-row-delete-icon"
                      >
                        <path
                          d="M8 4.5c0-.83.67-1.5 1.5-1.5h5c.83 0 1.5.67 1.5 1.5V6h3v2H5V6h3V4.5Z"
                          fill="currentColor"
                        />
                        <path
                          d="M7 8h10l-.7 9.2A2 2 0 0 1 14.32 19H9.68A2 2 0 0 1 7.7 17.2L7 8Z"
                          fill="currentColor"
                        />
                        <rect x="10" y="10" width="1.6" height="6" rx="0.8" fill="#fef2f2" />
                        <rect x="12.4" y="10" width="1.6" height="6" rx="0.8" fill="#fef2f2" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}
            </div>
          </div>

          <div className="chat-pane">
            <ChatBox
              docId={docId}
              docName={docName}
              onDocumentChange={handleDocumentChange}
              existingNames={docs.map(d => d.name)}
            />
          </div>
        </section>
      </div>
    </main>
  );
}
