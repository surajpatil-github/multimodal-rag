from pinecone_client import text_index, image_index
from openai import OpenAI

client = OpenAI()

def retrieve_text(query_vec, k=5, doc_id: str | None = None):
    kwargs = {"vector": query_vec, "top_k": k, "include_metadata": True}
    if doc_id:
        kwargs["filter"] = {"doc_id": doc_id}
    res = text_index.query(**kwargs)
    return [m["metadata"]["content"] for m in res["matches"]]

def retrieve_images(query_vec, k=4, doc_id: str | None = None):
    kwargs = {"vector": query_vec, "top_k": k, "include_metadata": True}
    if doc_id:
        kwargs["filter"] = {"doc_id": doc_id}
    res = image_index.query(**kwargs)
    captions = []
    for m in res["matches"]:
        md = m.get("metadata", {})
        caption = md.get("caption")
        if caption:
            captions.append(caption)
    return captions


def rag_answer(query, text_context_chunks, image_captions=None):
    text_context = "\n".join(text_context_chunks)

    images_section = ""
    if image_captions:
        images_section = "\n\nImage descriptions (from similar figures or diagrams):\n" + "\n".join(
            f"- {c}" for c in image_captions
        )

    prompt = f"""
You are a helpful teaching assistant.
Use ONLY the text context and image descriptions below to answer the user's question.
If the answer is not in the context, say you don't know.

When you answer:
- Be clear and concise.
- Use simple language.
- Use bullet points when they make the answer easier to read.
- When possible, mention the section title or page number if it appears in the context you relied on.

Text context:
{text_context}{images_section}

Question:
{query}
"""
    res = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role":"user","content":prompt}]
    )
    return res.choices[0].message.content
