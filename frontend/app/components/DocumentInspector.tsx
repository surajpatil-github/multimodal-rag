import { useState } from "react";

type DocumentInspectorProps = {
  file: File;
  previewUrl: string;
};

export default function DocumentInspector({ file, previewUrl }: DocumentInspectorProps) {
  // Document Inspector local state
  const [activeTab, setActiveTab] = useState<"preview" | "text" | "images" | "pages">("preview");
  const [zoomed, setZoomed] = useState(false);
  const [focusOpen, setFocusOpen] = useState(false);

  const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
  const isPdf = file.type === "application/pdf";
  const isImage = file.type.startsWith("image/");

  const toggleZoom = () => {
    setZoomed(z => !z);
  };

  const openFocus = () => {
    setFocusOpen(true);
  };

  const closeFocus = () => {
    setFocusOpen(false);
  };

  const downloadFile = () => {
    // Simple client-side download using the existing preview URL
    const link = document.createElement("a");
    link.href = previewUrl;
    link.download = file.name;
    link.click();
  };

  const askAiAboutThis = () => {
    // Placeholder hook into the chat experience
    alert("Ask a specific question about this document in the chat panel.");
  };

  return (
    <>
      <div className="doc-inspector">
        {/* Document Inspector card */}
        <div className="inspector-card">
        <div className="inspector-header">
          <div className="inspector-header-main">
            <div className="inspector-file-icon">📄</div>
            <div className="inspector-file-meta">
              <div className="inspector-file-name">{file.name}</div>
              <div className="inspector-file-sub">
                {isPdf ? "PDF" : isImage ? "Image" : "File"} · Pages: 0· Size: {sizeMb} MB
              </div>
            </div>
          </div>
          <div className="inspector-badge-current">In use</div>
        </div>

        {/* Tabs */}
        <div className="inspector-tabs">
          <button
            type="button"
            className={
              "inspector-tab" + (activeTab === "preview" ? " inspector-tab-active" : "")
            }
            onClick={() => setActiveTab("preview")}
          >
            Preview
          </button>
          <button
            type="button"
            className={
              "inspector-tab" + (activeTab === "text" ? " inspector-tab-active" : "")
            }
            onClick={() => setActiveTab("text")}
          >
            Text
          </button>
          <button
            type="button"
            className={
              "inspector-tab" + (activeTab === "images" ? " inspector-tab-active" : "")
            }
            onClick={() => setActiveTab("images")}
          >
            Images
          </button>
          <button
            type="button"
            className={
              "inspector-tab" + (activeTab === "pages" ? " inspector-tab-active" : "")
            }
            onClick={() => setActiveTab("pages")}
          >
            Pages
          </button>
        </div>

        {/* AI context badge */}
        <div className="inspector-ai-context">
          <span className="inspector-ai-dot" />
          <span className="inspector-ai-text">AI is currently using this document for answers</span>
        </div>

        {activeTab === "preview" && (
          <div className="inspector-preview-shell">
            <div className="inspector-preview-frame">
              <div
                className={
                  "inspector-preview-inner" +
                  (zoomed ? " inspector-preview-inner-zoomed" : "")
                }
              >
                {isImage && (
                  <img
                    src={previewUrl}
                    alt={file.name}
                    className="uploader-preview-image inspector-preview-media"
                  />
                )}
                {isPdf && (
                  <iframe
                    src={previewUrl}
                    title={file.name}
                    className="uploader-preview-pdf inspector-preview-media"
                  />
                )}
              </div>

              {/* Action bar overlay */}
              <div className="inspector-actions">
                <button
                  type="button"
                  className="inspector-action-btn"
                  onClick={toggleZoom}
                >
                  {zoomed ? "Reset" : "Zoom"}
                </button>
                <button
                  type="button"
                  className="inspector-action-btn"
                  onClick={downloadFile}
                >
                  Download
                </button>
                <button
                  type="button"
                  className="inspector-action-btn"
                  onClick={openFocus}
                >
                  Open full view
                </button>
                <button
                  type="button"
                  className="inspector-action-btn"
                  onClick={askAiAboutThis}
                >
                  Ask AI about this
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab !== "preview" && (
          <div className="inspector-tab-placeholder">
            {activeTab === "text" && "Text view will appear here."}
            {activeTab === "images" && "Detected images will appear here."}
            {activeTab === "pages" && "Page overview will appear here."}
          </div>
        )}
      </div>
      </div>

      {/* Focus Mode modal */}
      {focusOpen && (
        <div className="inspector-modal-backdrop" onClick={closeFocus}>
          <div className="inspector-modal" onClick={e => e.stopPropagation()}>
            <div className="inspector-modal-header">
              <span className="inspector-modal-title">{file.name}</span>
              <button
                type="button"
                className="inspector-modal-close"
                onClick={closeFocus}
              >
                ✕
              </button>
            </div>
            <div className="inspector-modal-body">
              {isImage && (
                <img
                  src={previewUrl}
                  alt={file.name}
                  className="uploader-preview-image inspector-modal-media"
                />
              )}
              {isPdf && (
                <iframe
                  src={previewUrl}
                  title={file.name}
                  className="uploader-preview-pdf inspector-modal-media"
                />
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}