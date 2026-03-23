"""
Unit tests for the multimodal RAG backend.

Run with:
    cd backend
    pytest tests/ -v --cov=. --cov-report=term-missing
"""

import pytest
from unittest.mock import MagicMock, patch


class TestChunkText:
    """Tests for the chunk_text generator."""

    def test_single_chunk_when_text_is_short(self):
        from ingest import chunk_text
        result = list(chunk_text("hello world", max_chars=100))
        assert result == ["hello world"]

    def test_splits_into_correct_number_of_chunks(self):
        from ingest import chunk_text
        # 5000 chars / 2000 per chunk = 3 chunks
        text = "a" * 5000
        chunks = list(chunk_text(text, max_chars=2000))
        assert len(chunks) == 3

    def test_last_chunk_can_be_shorter(self):
        from ingest import chunk_text
        text = "x" * 2500
        chunks = list(chunk_text(text, max_chars=2000))
        assert len(chunks[0]) == 2000
        assert len(chunks[1]) == 500

    def test_empty_string_yields_nothing(self):
        from ingest import chunk_text
        result = list(chunk_text("", max_chars=2000))
        assert result == []


class TestEmbedText:
    """Tests for embed_text — mocks the OpenAI client."""

    @patch("ingest.client")
    def test_returns_list_of_floats(self, mock_client):
        mock_embedding = MagicMock()
        mock_embedding.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
        mock_client.embeddings.create.return_value = mock_embedding

        from ingest import embed_text
        result = embed_text("test text")

        assert result == [0.1, 0.2, 0.3]
        mock_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-large",
            input="test text"
        )

    @patch("ingest.client")
    def test_passes_correct_model(self, mock_client):
        mock_client.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.0] * 3072)]
        )
        from ingest import embed_text
        embed_text("anything")
        call_kwargs = mock_client.embeddings.create.call_args[1]
        assert call_kwargs["model"] == "text-embedding-3-large"


class TestIngestText:
    """Tests for ingest_text — mocks OpenAI and Pinecone."""

    @patch("ingest.text_index")
    @patch("ingest.embed_text", return_value=[0.1] * 3072)
    def test_upserts_correct_number_of_vectors(self, mock_embed, mock_index):
        from ingest import ingest_text
        # 4500 chars → 3 chunks of 2000/2000/500
        ingest_text("a" * 4500, doc_id="doc-001")
        mock_index.upsert.assert_called_once()
        vectors = mock_index.upsert.call_args[0][0]
        assert len(vectors) == 3

    @patch("ingest.text_index")
    @patch("ingest.embed_text", return_value=[0.1] * 3072)
    def test_metadata_contains_doc_id(self, mock_embed, mock_index):
        from ingest import ingest_text
        ingest_text("some text", doc_id="my-doc")
        vectors = mock_index.upsert.call_args[0][0]
        for _, _, metadata in vectors:
            assert metadata["doc_id"] == "my-doc"

    @patch("ingest.text_index")
    @patch("ingest.embed_text", return_value=[0.1] * 3072)
    def test_does_not_upsert_empty_text(self, mock_embed, mock_index):
        from ingest import ingest_text
        ingest_text("")
        mock_index.upsert.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# rag.py tests
# ─────────────────────────────────────────────────────────────────────────────

class TestRetrieveText:
    """Tests for retrieve_text."""

    @patch("rag.text_index")
    def test_returns_list_of_content_strings(self, mock_index):
        mock_index.query.return_value = {
            "matches": [
                {"metadata": {"content": "chunk one"}},
                {"metadata": {"content": "chunk two"}},
            ]
        }
        from rag import retrieve_text
        result = retrieve_text([0.1] * 3072)
        assert result == ["chunk one", "chunk two"]

    @patch("rag.text_index")
    def test_applies_doc_id_filter(self, mock_index):
        mock_index.query.return_value = {"matches": []}
        from rag import retrieve_text
        retrieve_text([0.1] * 3072, doc_id="abc")
        call_kwargs = mock_index.query.call_args[1]
        assert call_kwargs["filter"] == {"doc_id": "abc"}

    @patch("rag.text_index")
    def test_no_filter_when_doc_id_is_none(self, mock_index):
        mock_index.query.return_value = {"matches": []}
        from rag import retrieve_text
        retrieve_text([0.1] * 3072)
        call_kwargs = mock_index.query.call_args[1]
        assert "filter" not in call_kwargs


class TestRagAnswer:
    """Tests for rag_answer."""

    @patch("rag.client")
    def test_returns_string_answer(self, mock_client):
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="The answer is 42."))]
        )
        from rag import rag_answer
        result = rag_answer("What is the answer?", ["context chunk"])
        assert result == "The answer is 42."

    @patch("rag.client")
    def test_includes_image_captions_in_prompt(self, mock_client):
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="answer"))]
        )
        from rag import rag_answer
        rag_answer("query", ["text ctx"], image_captions=["a diagram of X"])

        prompt = mock_client.chat.completions.create.call_args[1]["messages"][0]["content"]
        assert "a diagram of X" in prompt


# ─────────────────────────────────────────────────────────────────────────────
# app.py  (FastAPI endpoint) tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def test_client():
    """FastAPI test client with mocked external services."""
    with patch("app.text_index"), \
         patch("app.image_index"), \
         patch("app.client"):
        from fastapi.testclient import TestClient
        from app import app
        return TestClient(app)


class TestChatEndpoint:

    def test_chat_returns_200(self, test_client):
        with patch("app.embed_text", return_value=[0.1] * 3072), \
             patch("app.retrieve_text", return_value=["ctx"]), \
             patch("app.retrieve_images", return_value=[]), \
             patch("app.rag_answer", return_value="mocked answer"), \
             patch("app.client") as mock_openai:

            mock_openai.chat.completions.create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content="none"))]
            )

            response = test_client.post("/chat", json={
                "message": "What is RAG?",
                "doc_id": None
            })
        assert response.status_code == 200

    def test_chat_response_has_response_key(self, test_client):
        with patch("app.embed_text", return_value=[0.1] * 3072), \
             patch("app.retrieve_text", return_value=[]), \
             patch("app.retrieve_images", return_value=[]), \
             patch("app.rag_answer", return_value="test answer"), \
             patch("app.client") as mock_openai:

            mock_openai.chat.completions.create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content="none"))]
            )

            response = test_client.post("/chat", json={"message": "hello"})
        assert "response" in response.json()
