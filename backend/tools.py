import os
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

client = OpenAI()


def web_search(q: str) -> str:
    if not TAVILY_API_KEY:
        return "Web search is not configured. Please set TAVILY_API_KEY in your environment or .env file."

    q_lower = q.lower()

    try:
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": q,
            "max_results": 8,
            "search_depth": "advanced",
            "include_answer": False,
            "include_raw_content": True,
        }

        if any(word in q_lower for word in ["latest", "recent", "current", "today", "this year", "this month"]):
            payload["time_filter"] = "year"

        resp = requests.post("https://api.tavily.com/search", json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return "Web search failed while contacting Tavily."

    results = data.get("results") or []
    if not results:
        return "No reliable web search results were found for this query."

    snippets = []
    for i, item in enumerate(results[:5], start=1):
        title = item.get("title", "Untitled")
        url = item.get("url") or ""
        content = item.get("content") or ""
        snippets.append(f"{i}. {title}\nURL: {url}\n{content}")

    context = "\n\n".join(snippets)

    system_prompt = (
        "You are a web research agent using Tavily search.\n\n"
        "Your job is to use the provided Tavily search results to answer the user's question with the most accurate, "
        "up-to-date, and reliable information available.\n\n"
        "Follow these rules strictly:\n\n"
        "1. Prefer authoritative sources such as official websites, government portals, technical documentation, "
        "reputable news outlets, and academic or industry blogs.\n"
        "2. Avoid low-quality SEO blogs and clickbait. Only rely on forums if no better sources are present "
        "in the provided results.\n"
        "3. Base your answer only on the given search results. If they are insufficient or conflicting, say so explicitly.\n\n"
        "Output format:\n"
        "- First, a concise factual answer in 2-4 sentences.\n"
        "- Then 3-5 bullet-point key findings.\n"
        "- Then a short 'Sources:' list with titles and URLs.\n"
        "- If information is uncertain or conflicting, mention that clearly.\n"
    )

    user_prompt = (
        f"User question:\n{q}\n\n"
        f"Tavily web search results:\n{context}\n\n"
        "Now write the answer following the required format."
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
        )
        text = (resp.choices[0].message.content or "").strip()
        if text:
            return text
    except Exception:
        pass

    return context


def generate_ui(spec: str) -> str:
    prompt = f"""You are an expert frontend UI engineer.
Generate a single self-contained UI component based on this request:

{spec}

Constraints:
- Prefer React (TSX) suitable for a Next.js app
- Use simple className strings, no external UI libraries
- Include minimal inline styles or Tailwind-like utility classes
- Return code inside Markdown fences so it is easy to copy.
"""
    try:
        resp = client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content = resp.choices[0].message.content or ""
        text = content.strip()
        if not text:
            return "UI generator did not return any code. Try rephrasing your request."
        return text
    except Exception:
        return "UI generator failed while contacting OpenAI."


TOOLS = {
    "web_search": web_search,
    "generate_ui": generate_ui
}
