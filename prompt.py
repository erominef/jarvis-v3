# prompt.py — System prompt construction.
#
# build_system_prompt(user_input="") -> str
#
# Structure:
#   1. SOUL.md  — identity, mission, personality (loaded from disk, 5-min cache)
#   2. Tool guidance — web, memory, failure handling
#   3. Relevant Knowledge — RAG retrieval from Xeon (if user_input provided)
#   4. Relevant Past Context — episode retrieval from Xeon (if user_input provided)

import time
from pathlib import Path
from memory.client import search_knowledge, search_episodes
from tools.tools_registry import _TOOLS

_SOUL_PATH = Path(__file__).parent / "SOUL.md"
_soul_cache: tuple[float, str] | None = None
_SOUL_TTL = 300  # 5 minutes


def _load_soul() -> str:
    global _soul_cache
    now = time.time()
    if _soul_cache and now - _soul_cache[0] < _SOUL_TTL:
        return _soul_cache[1]
    try:
        content = _SOUL_PATH.read_text().strip()
    except FileNotFoundError:
        content = ""
    _soul_cache = (now, content)
    return content


_TOOL_GUIDANCE = """## Tool Usage

Web search:
- Use web_search for anything you don't know with certainty, or that may have changed recently.
- Search once. If the first result is useful, summarize it and respond. Do not search again.
- Summarize search results — do not dump raw titles and URLs. Extract the relevant answer.
- If the query is something you can answer from training knowledge with confidence, do not search.

Memory:
- Use knowledge_add to save important facts, documents, or notes to the knowledge base.
- Use knowledge_search to explicitly search for something in the knowledge base.
- Use memory_note to save a short note or observation to episodic memory.
- Relevant knowledge and past context are automatically injected below when available.

Tool failure handling:
- If a tool returns {"success": false, "error": "search_error"}, tell the user search is unavailable. Do NOT retry.
- If a tool returns {"success": false, "error": "no_results"}, tell the user nothing was found and suggest they rephrase. Do NOT retry.
- If a tool returns {"success": false, "error": "js_rendered_page"}, tell the user the page requires a browser. Suggest a raw alternative (e.g. raw.githubusercontent.com). Do NOT retry the same URL.
- If a tool returns {"success": false, "error": "no_content"}, tell the user the page had no readable content. Do NOT retry.
- On any tool failure: one attempt only, then explain and stop.

When using web_fetch, prefer raw URLs, plain HTML docs, and API responses. Avoid GitHub blob pages, Next.js/React/Nuxt sites, and anything requiring JavaScript.

Files:
- Use file_read/file_write/file_list for all workspace file access. Never access paths outside workspace/.
- Use file_write to save results, drafts, or data you want to persist between turns.

Research:
- Use searxng_search for general web search — it is better than web_search (more results, more control).
- Use wikipedia_search, hn_search, reddit_search, arxiv_search for targeted domain lookups.
- Use github_search/github_trending for code and repo discovery.
- Use wayback_fetch for archived versions of pages.

Data & Documents:
- Use data_analyze on workspace CSV/JSON files to get statistical summaries.
- Use financial_calc for projections, break-even, ROI, and market size calculations.
- Use draft_docx/draft_pptx/draft_xlsx to create formatted documents saved to workspace/.
- Use pdf_extract to read text from existing PDFs in workspace/.

Code Execution:
- Use code_execute for calculations, data processing, and algorithmic tasks — Python only, no network inside sandbox.
- Prefer code_execute over writing multi-step math by hand.

Infrastructure:
- Use system_health to check if services are up before using them.
- Do not retry a service more than once if system_health shows it is unreachable."""


def _build_tool_list() -> str:
    names = sorted(_TOOLS.keys())
    return "## Available Tools\n" + ", ".join(names) + "\n\nOnly claim capabilities you have a tool for. Do not invent tools."


def build_system_prompt(user_input: str = "") -> str:
    soul = _load_soul()
    parts = [soul, _TOOL_GUIDANCE, _build_tool_list()] if soul else [_TOOL_GUIDANCE, _build_tool_list()]

    if user_input:
        knowledge = search_knowledge(user_input, n=3)
        if knowledge:
            lines = ["## Relevant Knowledge"]
            for r in knowledge:
                prefix = f"[{r['title']}] " if r.get("title") else ""
                lines.append(f"{prefix}{r['text']}")
            parts.append("\n".join(lines))

        episodes = search_episodes(user_input, n=5)
        if episodes:
            lines = ["## Relevant Past Context"]
            for r in episodes:
                ts = r.get("timestamp", "")[:16].replace("T", " ")
                lines.append(f"[{ts}] {r['text']}")
            parts.append("\n".join(lines))

    return "\n\n".join(parts)
