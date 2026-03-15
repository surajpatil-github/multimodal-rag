import { useState, useRef, useEffect } from "react";
import axios from "axios";

const API = process.env.NEXT_PUBLIC_API_URL!;

type ChatMessage = {
  role: "user" | "bot";
  content: string;
};

type ChatBoxProps = {
  docId?: string | null;
  docName?: string | null;
  onDocumentChange?: (docId: string, fileName: string) => void;
  existingNames?: string[];
};

const urlRegex = /(https?:\/\/[^\s]+)/g;

function renderMessageContent(text: string) {
  const parts = text.split(urlRegex);
  return parts.map((part, index) => {
    if (part.startsWith("http://") || part.startsWith("https://")) {
      return (
        <a
          key={index}
          href={part}
          target="_blank"
          rel="noreferrer"
          className="chat-link"
        >
          {part}
        </a>
      );
    }
    return <span key={index}>{part}</span>;
  });
}

export default function ChatBox({ docId, docName, onDocumentChange, existingNames }: ChatBoxProps) {
  const [msg, setMsg] = useState("");
  const [chat, setChat] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [mode, setMode] = useState<"rag" | "web_search" | "ui_generator" | "youtube">("rag");
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [youtubeLoading, setYoutubeLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [chat]);

  const send = async () => {
    const trimmed = msg.trim();
    if (!trimmed || loading || uploadingImage) return;

    const userMessage: ChatMessage = { role: "user", content: trimmed };
    setChat(prev => [...prev, userMessage]);
    setMsg("");
    setLoading(true);

    try {
      const res = await axios.post(`${API}/chat`, { message: trimmed, doc_id: docId, mode });
      const botMessage: ChatMessage = {
        role: "bot",
        content: res.data.response ?? "No response received.",
      };
      setChat(prev => [...prev, botMessage]);
    } catch (err) {
      setChat(prev => [
        ...prev,
        { role: "bot", content: "Something went wrong while contacting the server." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    send();
  };

  const ingestYoutube = async () => {
    const url = youtubeUrl.trim();
    if (!url || youtubeLoading) return;

    setYoutubeLoading(true);
    try {
      const res = await axios.post(`${API}/youtube_ingest`, { url });
      const data = res.data as {
        doc_id?: string;
        title?: string;
        summary?: string;
        error?: string;
      };

      if (data.error) {
        setChat(prev => [
          ...prev,
          { role: "bot", content: `YouTube error: ${data.error}` },
        ]);
        return;
      }

      if (data.doc_id && onDocumentChange) {
        onDocumentChange(data.doc_id, data.title ?? url);
      }

      if (data.summary) {
        setChat(prev => [
          ...prev,
          {
            role: "bot",
            content: `Loaded YouTube video${data.title ? `: ${data.title}` : ""}.\n\nSummary:\n${data.summary}`,
          },
        ]);
      }

      setYoutubeUrl("");
    } catch {
      setChat(prev => [
        ...prev,
        { role: "bot", content: "Failed to load YouTube video." },
      ]);
    } finally {
      setYoutubeLoading(false);
    }
  };

  const openImagePicker = () => {
    if (loading || uploadingImage || youtubeLoading) return;
    fileInputRef.current?.click();
  };

  const handleImageChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || youtubeLoading) return;

    if (existingNames && existingNames.includes(file.name)) {
      alert("This document has already been uploaded.");
      return;
    }

    const form = new FormData();
    form.append("file", file);

    setUploadingImage(true);
    try {
      const res = await axios.post(`${API}/upload`, form);
      const data = res.data as { doc_id?: string; file_name?: string };
      if (data.doc_id && onDocumentChange) {
        onDocumentChange(data.doc_id, data.file_name ?? file.name);
      }
      setChat(prev => [
        ...prev,
        {
          role: "bot",
          content: `Image "${file.name}" uploaded. Ask a question about this image or document.`,
        },
      ]);
    } catch {
      setChat(prev => [
        ...prev,
        { role: "bot", content: "Image upload failed." },
      ]);
    } finally {
      setUploadingImage(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <div className="chat-box">
      {docName && mode === "rag" && (
        <p className="chat-empty" style={{ marginBottom: 4 }}>
          Answering using: <strong>{docName}</strong>
        </p>
      )}
      <div className="chat-mode-row">
        <span className="chat-mode-label">Source:</span>
        <button
          type="button"
          className={
            "chat-mode-pill" + (mode === "rag" ? " chat-mode-pill-active" : "")
          }
          onClick={() => setMode("rag")}
          disabled={loading}
        >
          Documents
        </button>
        <button
          type="button"
          className={
            "chat-mode-pill" + (mode === "web_search" ? " chat-mode-pill-active" : "")
          }
          onClick={() => setMode("web_search")}
          disabled={loading}
        >
          Web search
        </button>
        <button
          type="button"
          className={
            "chat-mode-pill" + (mode === "ui_generator" ? " chat-mode-pill-active" : "")
          }
          onClick={() => setMode("ui_generator")}
          disabled={loading}
        >
          UI generator
        </button>
        <button
          type="button"
          className={
            "chat-mode-pill" + (mode === "youtube" ? " chat-mode-pill-active" : "")
          }
          onClick={() => setMode("youtube")}
          disabled={loading}
        >
          YouTube video
        </button>
      </div>
      {mode === "youtube" && (
        <div className="chat-youtube-row">
          <div className="chat-youtube-field">
            <div className="chat-youtube-label">YouTube video URL</div>
            <input
              className="chat-youtube-input"
              placeholder="Paste YouTube URL to index the video..."
              value={youtubeUrl}
              onChange={e => setYoutubeUrl(e.target.value)}
            />
          </div>
          <button
            type="button"
            className="chat-youtube-btn"
            onClick={ingestYoutube}
            disabled={!youtubeUrl.trim() || youtubeLoading}
          >
            {youtubeLoading ? "Loading..." : "Load video"}
          </button>
        </div>
      )}
      <div className="chat-messages">
        {chat.length === 0 && (
          <p className="chat-empty">Ask a question about your uploaded document to get started.</p>
        )}
        {chat.map((m, i) => (
          <div
            key={i}
            className={`message-row ${m.role === "user" ? "message-row-user" : "message-row-bot"}`}
          >
            <div className={`message-bubble message-bubble-${m.role}`}>
              <span className="message-author">{m.role === "user" ? "You" : "Bot"}</span>
              <p className="message-text">{renderMessageContent(m.content)}</p>
            </div>
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>
      <form className="chat-input-row" onSubmit={handleSubmit}>
        <input
          className="chat-input"
          placeholder={
            mode === "web_search"
              ? "Search the web with AI..."
              : mode === "ui_generator"
              ? "Describe the UI component you want (e.g. a login card)..."
              : mode === "youtube"
              ? "Ask a question about this YouTube video..."
              : "Ask a question about your document..."
          }
          value={msg}
          onChange={e => setMsg(e.target.value)}
        />
        <button
          type="button"
          className="chat-attach-btn"
          onClick={openImagePicker}
          disabled={loading || uploadingImage || youtubeLoading}
        >
          {uploadingImage ? "Uploading..." : "Add image"}
        </button>
        <button
          type="submit"
          className="chat-send-btn"
          disabled={!msg.trim() || loading || uploadingImage || youtubeLoading}
        >
          {loading ? "Thinking..." : "Send"}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleImageChange}
          style={{ display: "none" }}
        />
      </form>
    </div>
  );
}
