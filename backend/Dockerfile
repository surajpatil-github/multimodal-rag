# ── Stage 1: builder ─────────────────────────────────────────────────────────
# Install all Python deps in a throwaway layer
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system deps needed by PyMuPDF and Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
        libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python requirements first (better layer caching)
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --prefix=/install --no-cache-dir -r requirements.txt

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY app.py ingest.py rag.py tools.py pinecone_client.py clip_embedder.py ./

# Non-root user for security
RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 8000

# Uvicorn with 2 workers; adjust based on server CPU count
CMD ["uvicorn", "app:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--log-level", "info"]
