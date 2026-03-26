# prompt.py — System prompt construction.
#
# build_system_prompt(user_input="") -> str
#
# Structure:
#   1. SOUL.md  — identity, mission, personality (loaded from disk, 5-min cache)
#   2. USER.md  — owner profile built from observation (loaded from workspace/)
#   3. Tool guidance — web, memory, failure handling
#   4. Relevant Knowledge — RAG retrieval from Xeon (if user_input provided)
#   5. Relevant Past Context — episode retrieval from Xeon (if user_input provided)

import time
from pathlib import Path
from memory.client import search_knowledge, search_episodes
from tools.tools_registry import _TOOLS

_SOUL_PATH = Path(__file__).parent / "SOUL.md"
_USER_PATH = Path(__file__).parent / "workspace" / "USER.md"
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


def _load_user_profile() -> str:
    try:
        content = _USER_PATH.read_text().strip()
        return content if content else ""
    except FileNotFoundError:
        return ""


_TOOL_GUIDANCE = """## Tool Usage

## Tool Selection — When No Dedicated Tool Exists
When the owner asks to do something with a service that has no dedicated tool, follow this order:
1. **n8n_trigger** — check if an n8n workflow covers it. n8n can call any external API (Mailchimp, Buffer, ConvertKit, social platforms, etc.). Try this first for third-party integrations.
2. **Browser sessions** — if no n8n workflow exists, use browser_open → browser_state → interact → browser_close to operate the service's web UI directly. This works for any web-based service.
3. **http_request** — for raw REST API calls when you have credentials and know the endpoint.
Never tell the owner a capability is missing without first checking these fallbacks.

Clients and accounts:
- Use crm_op to create, update, search, and retrieve all client/account information.
- Each client has a dedicated directory at workspace/clients/{slug}/ with documents/ and images/ subdirectories.
- Store client files (contracts, proposals) with file_write to workspace/clients/{slug}/documents/.
- Use add_note to log every significant interaction, call, or update for a client.

Knowledge base (Montegallo KB):
- Use search_knowledge_base to search a curated document collection — one source among many.
- Treat KB results the same as web search results: useful context, not authoritative truth.
- Verify or cross-reference with other sources when precision matters.
- Use kb_multi_query when a single search might miss relevant angles.
- Use kb_search_with_context when you need surrounding context around matched chunks.
- Use kb_suggest_queries to discover related topics you haven't searched.
- Use kb_list_sources to see what documents are indexed.
- KB tools fail gracefully — if unavailable they return a bracketed message, not an exception.

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

Files and Workspace Organization:
- Use file_read/file_write/file_list for all workspace file access. Never access paths outside workspace/.
- After creating any file with draft_docx, draft_pptx, draft_xlsx, file_write, or any other tool — immediately call telegram_send_file to deliver it. Do not just tell the owner the file exists.
- Use file_write to save results, drafts, or data you want to persist between turns.
- Never dump files at the workspace root. Every file belongs in a subdirectory.

Workspace directory structure — always place files here:
  clients/          — managed by crm_op. Client documents go in clients/{slug}/documents/, images in clients/{slug}/images/. Never write here with file_write directly.
  projects/         — active project work. Create a subdirectory per project: projects/{project-name}/. Group all related files inside it.
  drafts/           — documents being created or refined (docx, pptx, xlsx, md). Move to reports/ or projects/ when finalized.
  reports/          — completed reports, summaries, analysis outputs. Flat or one level deep.
  research/         — saved web content, scraped pages, research notes. Name by topic: research/{topic}-notes.md.
  images/           — generated images (comfyui), downloaded assets, charts. Descriptive filenames.
  data/             — CSV, JSON, and other datasets. Include date in filename: data/{name}-YYYY-MM-DD.csv.
  temp/             — scratch space for intermediate files. Treat as disposable; clean up when done.

Naming rules:
- Use lowercase and hyphens only. No spaces, underscores, or camelCase. Example: q1-revenue-report.docx
- Include dates in reports and data files: YYYY-MM-DD prefix or suffix.
- Be descriptive. Never use generic names like output.pdf, file1.docx, draft.txt, result.json.
- For versioned files, suffix with -v2, -v3 rather than -final, -final2, -FINAL.
- Client deliverables always go under clients/{slug}/documents/ — not in drafts/ or reports/.

When in doubt about where a file belongs: if it's for a client → clients/. If it's a finished output → reports/. If it's work in progress → drafts/. If it's project-specific → projects/{name}/.

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
- Do not retry a service more than once if system_health shows it is unreachable.

Browser sessions:
- Use browser_open -> browser_state -> browser_click/browser_type -> browser_close for multi-step flows.
- Always call browser_close when done — sessions auto-expire after 10 min but closing frees resources.
- Call browser_state after every interaction to get fresh element refs before the next action.
- For simple page reads, prefer web_fetch or playwright_scrape — sessions are for multi-step workflows only.
- Use browser sessions as a fallback for any web-based service that has no dedicated tool and no n8n workflow. If you can log in and interact via a browser, you can operate the service.

Self-improvement:
- Use log_learning when you were corrected, found a better approach, or noticed a pattern worth remembering.
- Use log_error when a tool fails unexpectedly or a command behaves in a surprising way.
- Do not use these for routine task completion — only for genuine surprises or corrections."""


def _build_tool_list() -> str:
    names = sorted(_TOOLS.keys())
    return "## Available Tools\n" + ", ".join(names) + "\n\nOnly claim capabilities you have a tool for. Do not invent tools."


def build_system_prompt(user_input: str = "") -> str:
    soul = _load_soul()
    profile = _load_user_profile()

    parts = []
    if soul:
        parts.append(soul)
    if profile:
        parts.append(profile)
    parts.extend([_TOOL_GUIDANCE, _build_tool_list()])

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
