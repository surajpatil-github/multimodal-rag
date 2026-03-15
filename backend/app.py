from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from ingest import ingest_text, ingest_image, ingest_pdf_images, embed_text
from rag import retrieve_text, retrieve_images, rag_answer
from tools import TOOLS
from openai import OpenAI
from urllib.parse import urlparse, parse_qs
from pinecone_client import text_index, image_index
import json
import io
import uuid
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI()



def _extract_youtube_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in {"www.youtube.com", "youtube.com", "m.youtube.com"}:
        qs = parse_qs(parsed.query)
        return (qs.get("v") or [None])[0]
    if host == "youtu.be":
        return parsed.path.lstrip("/") or None
    return None


@app.post("/youtube_ingest")
async def youtube_ingest(payload: dict):
    url = payload.get("url")
    if not url:
        return {"error": "Missing YouTube URL."}

    video_id = _extract_youtube_id(url)
    if not video_id:
        return {"error": "Could not parse YouTube video ID from URL."}

    try:
        from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
        from youtube_transcript_api.proxies import WebshareProxyConfig
    except ImportError:
        return {"error": "youtube-transcript-api is not installed on the server."}

    try:
        proxy_username = os.getenv("WEBSHARE_USERNAME")
        proxy_password = os.getenv("WEBSHARE_PASSWORD")
        if proxy_username and proxy_password:
            proxy_config = WebshareProxyConfig(
                proxy_username=proxy_username,
                proxy_password=proxy_password,
            )
            api = YouTubeTranscriptApi(proxy_config=proxy_config)
        else:
            api = YouTubeTranscriptApi()
        fetched = api.fetch(
            video_id,
            languages=["en", "en-US", "en-GB", "en-IN"],
        )
        parts = [getattr(s, "text", "") for s in fetched if getattr(s, "text", "")]
    except (TranscriptsDisabled, NoTranscriptFound):
        return {"error": "Transcript is not available for this YouTube video (no subtitles found)."}
    except Exception as e:
        return {"error": f"Failed to fetch transcript from YouTube: {e}"}

    full_text = " ".join(parts).strip()
    if not full_text:
        return {"error": "Transcript for this video was empty."}

    doc_id = str(uuid.uuid4())
    ingest_text(full_text, doc_id=doc_id)

    snippet = full_text[:6000]
    summary_prompt = f"Summarize the following YouTube video transcript in 5 concise bullet points:\n\n{snippet}"
    try:
        summary_resp = client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.3,
        )
        summary = (summary_resp.choices[0].message.content or "").strip()
    except Exception:
        summary = "Summary generation failed, but the transcript has been indexed. You can still ask questions about this video."

    title = f"YouTube video ({video_id})"

    return {"status": "indexed", "doc_id": doc_id, "title": title, "summary": summary}


@app.post("/delete_document")
async def delete_document(payload: dict):
    doc_id = payload.get("doc_id")
    if not doc_id:
        return {"error": "Missing doc_id"}

    try:
        text_index.delete(filter={"doc_id": doc_id})
    except Exception:
        pass

    try:
        image_index.delete(filter={"doc_id": doc_id})
    except Exception:
        pass

    return {"status": "deleted", "doc_id": doc_id}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    data = await file.read()
    doc_id = str(uuid.uuid4())

    if file.content_type.startswith("image"):
        ingest_image(data, doc_id=doc_id)
    elif file.content_type == "application/pdf" or file.filename.lower().endswith(".pdf"):
        from PyPDF2 import PdfReader

        pdf_file = io.BytesIO(data)
        reader = PdfReader(pdf_file)
        pages_text = []
        for page in reader.pages:
            text = page.extract_text() or ""
            pages_text.append(text)
        full_text = "\n".join(pages_text)
        ingest_text(full_text, doc_id=doc_id)
        ingest_pdf_images(data, doc_id=doc_id)
    else:
        ingest_text(data.decode("utf-8", errors="ignore"), doc_id=doc_id)

    return {"status": "uploaded", "doc_id": doc_id, "file_name": file.filename}

@app.post("/chat")
async def chat(payload: dict):
    query = payload["message"]
    doc_id = payload.get("doc_id")
    mode = payload.get("mode")

    if mode == "web_search":
        if "web_search" in TOOLS:
            result = TOOLS["web_search"](query)
            return {"response": result, "source": "web_search"}

    if mode == "ui_generator":
        if "generate_ui" in TOOLS:
            result = TOOLS["generate_ui"](query)
            return {"response": result, "source": "ui_generator"}

    # ---------- RAG ----------
    q_vec = embed_text(query)
    text_context = retrieve_text(q_vec, doc_id=doc_id)

    image_captions = retrieve_images(q_vec, doc_id=doc_id)

    # ---------- TOOL DECISION ----------
    tool_prompt = f"""
User query: {query}

If a tool is needed respond ONLY in JSON:
{{"tool":"name","input":"..."}}  
Else respond: none
"""
    resp = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role":"user","content":tool_prompt}]
    )
    decision = (resp.choices[0].message.content or "").strip()

    if decision and decision.lower() != "none":
        try:
            data = json.loads(decision)
            tool_name = data.get("tool")
            tool_input = data.get("input")
            if tool_name in TOOLS and tool_input is not None:
                result = TOOLS[tool_name](tool_input)
                return {"response": result, "source": "tool"}
        except json.JSONDecodeError:
            pass

    # ---------- RAG ANSWER ----------
    answer = rag_answer(query, text_context, image_captions)
    return {"response": answer, "source": "rag"}
