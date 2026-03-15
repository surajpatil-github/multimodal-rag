import uuid, io, base64
from openai import OpenAI
from pinecone_client import text_index, image_index
from PIL import Image

client = OpenAI()

MAX_CHARS_PER_CHUNK = 2000

def embed_text(text: str):
    res = client.embeddings.create(
        model="text-embedding-3-large",
        input=text
    )
    return res.data[0].embedding   # 3072-dim

def chunk_text(text: str, max_chars: int = MAX_CHARS_PER_CHUNK):
    for i in range(0, len(text), max_chars):
        yield text[i : i + max_chars]

def ingest_text(text: str, doc_id: str | None = None):
    vectors = []
    for chunk in chunk_text(text):
        vec = embed_text(chunk)
        metadata = {"type": "text", "content": chunk}
        if doc_id:
            metadata["doc_id"] = doc_id
        vectors.append((str(uuid.uuid4()), vec, metadata))

    if vectors:
        text_index.upsert(vectors)

def caption_image(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")

    res = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Describe this image concisely as if for a science textbook caption.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{b64}",
                        },
                    },
                ],
            }
        ],
    )
    return res.choices[0].message.content


def ingest_image(image_bytes: bytes, doc_id: str | None = None):
    img = Image.open(io.BytesIO(image_bytes))
    caption = caption_image(img)
    vec = embed_text(caption)
    metadata = {"type": "image", "caption": caption}
    if doc_id:
        metadata["doc_id"] = doc_id
    image_index.upsert([
        (str(uuid.uuid4()), vec, metadata)
    ])


def ingest_pdf_images(pdf_bytes: bytes, doc_id: str | None = None):
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_bytes = pix.tobytes("png")
            ingest_image(img_bytes, doc_id=doc_id)
    finally:
        doc.close()
