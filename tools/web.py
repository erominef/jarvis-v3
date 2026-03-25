# tools/web.py — Web search and fetch tools.
#
# web_search: SearXNG API at SEARXNG_URL. Returns structured dict.
#   {success, results: [{title, url, snippet}]}
#   error values: "no_results" | "search_error"
#   Timeout: 3s. Limit: 5 results.
#
# web_fetch: Returns structured dict {success, error?, content?}.
#   error values: "js_rendered_page" | "no_content" | "fetch_error"
#
#   JS detection: flags pages where <script> tags dominate the raw HTML
#   (script_ratio > 0.6) or known SPA markers are present.
#   No-content detection: readable text after tag-stripping is under 100 chars.

import re
import httpx

from config import SEARXNG_URL, PLAYWRIGHT_URL

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Jarvis/3.0)"}
_TIMEOUT = 15

# Markers that indicate a JS-rendered SPA with no server-side content
_SPA_MARKERS = [
    "__NEXT_DATA__", "__nuxt__", "window.__",
    "ReactDOM.render", "createRoot(", "ng-version",
    "<div id=\"app\"></div>", "<div id=\"root\"></div>",
]


def _is_js_heavy(raw_html: str) -> bool:
    """Return True if the page is dominated by JS and has little readable HTML."""
    script_content = "".join(re.findall(r"<script[^>]*>.*?</script>", raw_html, re.DOTALL))
    if len(raw_html) > 0 and len(script_content) / len(raw_html) > 0.6:
        return True
    lower = raw_html.lower()
    if any(marker.lower() in lower for marker in _SPA_MARKERS):
        return True
    return False


def web_search(query: str) -> dict:
    try:
        resp = httpx.get(
            f"{SEARXNG_URL}/search",
            params={"q": query, "format": "json"},
            timeout=3,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return {"success": False, "error": "search_error"}

    hits = data.get("results", [])[:5]
    if not hits:
        return {"success": False, "error": "no_results"}

    results = [
        {"title": h.get("title", ""), "url": h.get("url", ""), "snippet": h.get("content", "")}
        for h in hits
    ]
    return {"success": True, "results": results}


def web_fetch(url: str) -> dict:
    try:
        resp = httpx.post(
            f"{PLAYWRIGHT_URL}/fetch",
            json={"url": url},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return {"success": False, "error": "fetch_error"}

    raw_html = data.get("html", "")

    if _is_js_heavy(raw_html):
        return {"success": False, "error": "js_rendered_page"}

    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) < 100:
        return {"success": False, "error": "no_content"}

    return {"success": True, "content": text[:2000]}
