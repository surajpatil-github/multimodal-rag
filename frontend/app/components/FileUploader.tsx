import axios from "axios";
import { useState, useRef, useEffect } from "react";
import DocumentInspector from "./DocumentInspector";

const API = process.env.NEXT_PUBLIC_API_URL!;

type FileUploaderProps = {
  onUploaded?: (docId: string, fileName: string) => void;
  existingNames?: string[];
  activeDocName?: string | null;
};

type LocalDoc = {
  name: string;
  file: File;
  url: string;
};

export default function FileUploader({
  onUploaded,
  existingNames,
  activeDocName,
}: FileUploaderProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [localDocs, setLocalDocs] = useState<LocalDoc[]>([]);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!activeDocName) return;
    const match = localDocs.find(d => d.name === activeDocName);
    if (!match) {
      setShowPreview(false);
      return;
    }
    setSelectedFile(match.file);
    setPreviewUrl(match.url);
  }, [activeDocName, localDocs]);

  const upload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (existingNames && existingNames.includes(file.name)) {
      alert("This document has already been uploaded.");
      return;
    }

    const form = new FormData();
    form.append("file", file);

    const res = await axios.post(`${API}/upload`, form);
    const data = res.data as { doc_id?: string; file_name?: string };
    if (data.doc_id && onUploaded) {
      onUploaded(data.doc_id, data.file_name ?? file.name);
    }
    alert("File uploaded and ingested.");

    const url = URL.createObjectURL(file);
    setLocalDocs(prev => [...prev, { name: file.name, file, url }]);
    setSelectedFile(file);
    setPreviewUrl(url);
    setShowPreview(false);
  };

  const openNewUpload = () => {
    inputRef.current?.click();
  };

  return (
    <div className="uploader">
      <div className="uploader-row">
        <label className="uploader-label">
          <span className="uploader-title">Upload document</span>
          <span className="uploader-help">PDFs or images up to a few MB.</span>
          <input
            ref={inputRef}
            type="file"
            onChange={upload}
            className="uploader-input"
          />
        </label>
        {selectedFile && (
          <>
            <button type="button" className="uploader-secondary" onClick={openNewUpload}>
              Upload new document
            </button>
            <button
              type="button"
              className="uploader-secondary"
              onClick={() => setShowPreview(p => !p)}
            >
              {showPreview ? "Hide preview" : "Show preview"}
            </button>
          </>
        )}
      </div>

      {selectedFile && showPreview && previewUrl && (
        <div className="uploader-preview">
          <DocumentInspector file={selectedFile} previewUrl={previewUrl} />
        </div>
      )}
    </div>
  );
}