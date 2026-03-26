# tools/research.py — Deep research tools.
#
# All functions are synchronous (v3 uses sync httpx throughout).
# Output capped at 3000 chars. Prompt injection patterns stripped from all external content.
#
# Tools: wikipedia_search, hn_search, reddit_search, rss_fetch, wayback_fetch,
#        google_trends, github_trending, github_search, whois_lookup,
#        opencorporates_search, url_safety_check, arxiv_search, youtube_transcript

import os
import random
import re
import urllib.robotparser
from urllib.parse import quote, urlparse

import httpx

_TIMEOUT = 15.0
_MAX_CHARS = 3000

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]

_INJECTION_RE = re.compile(
    r"(ignore\s+(all\s+)?(previous|prior|above)\s+instructions?|"
    r"you\s+are\s+now\s+a|new\s+instructions?:|system\s*:|"
    r"<\s*/?system\s*>|disregard\s+(all\s+)?previous|"
    r"act\s+as\s+if\s+you|your\s+new\s+(role|instructions?|persona)|"
    r"pretend\s+you\s+are)",
    re.IGNORECASE,
)


def _headers() -> dict:
    return {"User-Agent": random.choice(_USER_AGENTS)}


def _sanitize(text: str) -> str:
    return _INJECTION_RE.sub("[REDACTED]", text)


def _finalize(text: str) -> str:
    text = _sanitize(text)
    if len(text) > _MAX_CHARS:
        return text[:_MAX_CHARS] + "\n[truncated]"
    return text


def _can_fetch(url: str) -> bool:
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch("*", url)
    except Exception:
        return True


def _strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html)


# ── Wikipedia ─────────────────────────────────────────────────────────────────

def wikipedia_search(query: str, sentences: int = 5) -> str:
    try:
        search_url = (
            "https://en.wikipedia.org/w/api.php"
            f"?action=query&list=search&srsearch={quote(query)}&format=json&srlimit=1"
        )
        r = httpx.get(search_url, headers=_headers(), timeout=_TIMEOUT, follow_redirects=True)
        r.raise_for_status()
        results = r.json().get("query", {}).get("search", [])
        if not results:
            return f"No Wikipedia results for: {query}"

        title = results[0]["title"]
        summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title)}"
        r = httpx.get(summary_url, headers=_headers(), timeout=_TIMEOUT, follow_redirects=True)
        r.raise_for_status()
        data = r.json()

        extract = data.get("extract", "")
        if not extract:
            return f"Wikipedia page found for '{title}' but summary was empty."

        parts = re.split(r"(?<=[.!?])\s+", extract)
        trimmed = " ".join(parts[:sentences])
        page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
        out = f"Wikipedia — {title}\n{trimmed}"
        if page_url:
            out += f"\nSource: {page_url}"
        return _finalize(out)
    except Exception:
        return "Wikipedia lookup failed."


# ── Hacker News ───────────────────────────────────────────────────────────────

def hn_search(query: str, limit: int = 10) -> str:
    try:
        limit = min(max(1, limit), 20)
        url = f"https://hn.algolia.com/api/v1/search?query={quote(query)}&tags=story&hitsPerPage={limit}"
        r = httpx.get(url, headers=_headers(), timeout=_TIMEOUT, follow_redirects=True)
        r.raise_for_status()
        hits = r.json().get("hits", [])
        if not hits:
            return f"No Hacker News results for: {query}"

        lines = [f"Hacker News — top {len(hits)} results for '{query}':"]
        for h in hits:
            title = h.get("title", "(no title)")
            points = h.get("points") or 0
            comments = h.get("num_comments") or 0
            link = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID','')}"
            lines.append(f"• {title} ({points}pts, {comments} comments)\n  {link}")
        return _finalize("\n\n".join(lines))
    except Exception:
        return "Hacker News search failed."


# ── Reddit ────────────────────────────────────────────────────────────────────

def reddit_search(subreddit: str, query: str = "", limit: int = 10, sort: str = "hot") -> str:
    try:
        limit = min(max(1, limit), 25)
        headers = dict(_headers())
        headers["User-Agent"] = "Jarvis/3.0 research-bot"
        if query:
            url = f"https://www.reddit.com/r/{subreddit}/search.json?q={quote(query)}&restrict_sr=1&sort={sort}&limit={limit}"
        else:
            url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}"
        r = httpx.get(url, headers=headers, timeout=_TIMEOUT, follow_redirects=True)
        r.raise_for_status()
        posts = r.json().get("data", {}).get("children", [])
        if not posts:
            return f"No posts found in r/{subreddit}" + (f" for '{query}'" if query else "")

        label = f"r/{subreddit}" + (f" search '{query}'" if query else f" [{sort}]")
        lines = [f"Reddit — {label} ({len(posts)} posts):"]
        for p in posts:
            d = p.get("data", {})
            title = d.get("title", "(no title)")
            score = d.get("score") or 0
            comments = d.get("num_comments") or 0
            selftext = (d.get("selftext") or "")[:200].replace("\n", " ")
            permalink = "https://www.reddit.com" + d.get("permalink", "")
            entry = f"• {title} ({score}pts, {comments} comments)\n  {permalink}"
            if selftext:
                entry += f"\n  {selftext}"
            lines.append(entry)
        return _finalize("\n\n".join(lines))
    except Exception:
        return "Reddit fetch failed. Subreddit may be private or rate-limited."


# ── RSS feed ──────────────────────────────────────────────────────────────────

def rss_fetch(feed_url: str, limit: int = 10) -> str:
    try:
        import feedparser  # type: ignore
    except ImportError:
        return "feedparser not installed — add 'feedparser' to requirements.txt."

    try:
        feed = feedparser.parse(feed_url)
        if not feed.entries:
            return f"No entries found in feed: {feed_url}"

        title = feed.feed.get("title", feed_url)
        entries = feed.entries[:min(max(1, limit), 25)]
        lines = [f"RSS — {title} ({len(entries)} entries):"]
        for entry in entries:
            e_title = entry.get("title", "(no title)")
            e_link = entry.get("link", "")
            e_pub = entry.get("published", entry.get("updated", ""))
            e_summary = re.sub(r"<[^>]+>", "", entry.get("summary", ""))[:300].strip()
            block = f"• {e_title}"
            if e_pub:
                block += f" [{e_pub}]"
            if e_link:
                block += f"\n  {e_link}"
            if e_summary:
                block += f"\n  {e_summary}"
            lines.append(block)
        return _finalize("\n\n".join(lines))
    except Exception as e:
        return f"RSS feed fetch failed: {e}"


# ── Wayback Machine ───────────────────────────────────────────────────────────

def wayback_fetch(url: str) -> str:
    try:
        avail_url = f"https://archive.org/wayback/available?url={quote(url, safe=':/?=&')}"
        r = httpx.get(avail_url, headers=_headers(), timeout=_TIMEOUT, follow_redirects=True)
        r.raise_for_status()
        snapshot = r.json().get("archived_snapshots", {}).get("closest", {})
        if not snapshot or not snapshot.get("available"):
            return f"No Wayback Machine snapshot found for: {url}"

        snapshot_url = snapshot["url"]
        timestamp = snapshot.get("timestamp", "unknown")

        if not _can_fetch(snapshot_url):
            return f"Wayback snapshot exists (timestamp {timestamp}) but robots.txt disallows scraping."

        r = httpx.get(snapshot_url, headers=_headers(), timeout=_TIMEOUT, follow_redirects=True)
        r.raise_for_status()
        html = r.text

        html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<(br|p|div|h[1-6]|li|tr)[^>]*>", "\n", html, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", html)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))

        return _finalize(f"Wayback Machine snapshot (timestamp: {timestamp})\nOriginal URL: {url}\n\n{text}")
    except Exception:
        return "Wayback Machine lookup failed."


# ── Google Trends ─────────────────────────────────────────────────────────────

def google_trends(keywords: list, timeframe: str = "today 12-m") -> str:
    try:
        from pytrends.request import TrendReq  # type: ignore
    except ImportError:
        return "pytrends not installed — add 'pytrends' to requirements.txt."

    if not keywords:
        return "No keywords provided."
    keywords = keywords[:5]

    try:
        pt = TrendReq(hl="en-US", tz=360)
        pt.build_payload(keywords, timeframe=timeframe)
        df = pt.interest_over_time()
        if df.empty:
            return "No trend data returned."

        lines = []
        for kw in keywords:
            if kw not in df.columns:
                continue
            series = df[kw]
            peak_date = series.idxmax()
            peak_val = int(series.max())
            current = int(series.iloc[-1])
            prev = int(series.iloc[-2]) if len(series) > 1 else current
            direction = "up" if current > prev else ("down" if current < prev else "flat")
            lines.append(
                f"  {kw}: peak {peak_date.strftime('%Y-%m')} ({peak_val}/100), "
                f"current {current}/100 [{direction}]"
            )
        return _finalize("Google Trends interest (relative, 0-100):\n" + "\n".join(lines))
    except Exception as e:
        return f"Trends fetch failed: {e}"


# ── GitHub Trending ───────────────────────────────────────────────────────────

def github_trending(language: str = "", period: str = "daily") -> str:
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except ImportError:
        return "beautifulsoup4 not installed — add 'beautifulsoup4' to requirements.txt."

    try:
        lang_path = f"/{quote(language)}" if language else ""
        url = f"https://github.com/trending{lang_path}?since={period}"
        if not _can_fetch(url):
            return "robots.txt disallows scraping GitHub trending."

        r = httpx.get(url, headers=_headers(), timeout=_TIMEOUT, follow_redirects=True)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        repos = soup.select("article.Box-row")[:10]

        if not repos:
            return "No trending repos found. GitHub may have changed its page structure."

        label = f"language={language}" if language else "all languages"
        lines = [f"GitHub Trending ({label}, {period}):"]
        for repo in repos:
            name_tag = repo.select_one("h2 a")
            name = name_tag.get_text(separator="/", strip=True).replace(" ", "").replace("\n", "") if name_tag else "?"
            desc_tag = repo.select_one("p")
            desc = desc_tag.get_text(strip=True) if desc_tag else ""
            stars_tag = repo.select_one("a[href$='/stargazers']")
            stars = stars_tag.get_text(strip=True).replace(",", "").strip() if stars_tag else "?"
            lang_tag = repo.select_one("span[itemprop='programmingLanguage']")
            lang = lang_tag.get_text(strip=True) if lang_tag else ""
            entry = f"• {name} ★{stars}" + (f" [{lang}]" if lang else "")
            if desc:
                entry += f"\n  {desc}"
            lines.append(entry)
        return _finalize("\n\n".join(lines))
    except Exception:
        return "GitHub trending scrape failed."


# ── GitHub Search ─────────────────────────────────────────────────────────────

def github_search(query: str, type: str = "repositories", limit: int = 5) -> str:
    try:
        limit = min(max(1, limit), 10)
        valid_types = {"repositories", "code", "issues", "users"}
        if type not in valid_types:
            type = "repositories"
        url = f"https://api.github.com/search/{type}?q={quote(query)}&per_page={limit}"
        headers = dict(_headers())
        headers["Accept"] = "application/vnd.github.v3+json"
        r = httpx.get(url, headers=headers, timeout=_TIMEOUT)
        r.raise_for_status()
        items = r.json().get("items", [])
        if not items:
            return f"No GitHub {type} results for: {query}"

        lines = [f"GitHub {type} search — '{query}':"]
        for item in items:
            if type == "repositories":
                name = item.get("full_name", "?")
                desc = item.get("description", "")[:100]
                stars = item.get("stargazers_count", 0)
                lang = item.get("language", "")
                url_html = item.get("html_url", "")
                entry = f"• {name} ★{stars}" + (f" [{lang}]" if lang else "")
                if desc:
                    entry += f"\n  {desc}"
                entry += f"\n  {url_html}"
            else:
                name = item.get("full_name") or item.get("title") or item.get("login") or "?"
                html_url = item.get("html_url", "")
                entry = f"• {name}\n  {html_url}"
            lines.append(entry)
        return _finalize("\n\n".join(lines))
    except Exception:
        return "GitHub search failed."


# ── WHOIS ─────────────────────────────────────────────────────────────────────

def whois_lookup(domain: str) -> str:
    try:
        import whois  # type: ignore
    except ImportError:
        return "python-whois not installed — add 'python-whois' to requirements.txt."

    try:
        w = whois.whois(domain)
        if not w or not w.domain_name:
            return f"Domain '{domain}' appears to be available (no registration found)."

        def _fmt_date(val) -> str:
            if val is None:
                return "unknown"
            if isinstance(val, list):
                val = val[0]
            try:
                return val.strftime("%Y-%m-%d")
            except Exception:
                return str(val)

        lines = [f"WHOIS — {domain}"]
        lines.append(f"Registrar:       {w.registrar or 'unknown'}")
        lines.append(f"Creation date:   {_fmt_date(w.creation_date)}")
        lines.append(f"Expiration date: {_fmt_date(w.expiration_date)}")
        if w.name:
            lines.append(f"Registrant:      {w.name}")
        elif w.org:
            lines.append(f"Organization:    {w.org}")
        return _finalize("\n".join(lines))
    except Exception as e:
        msg = str(e).lower()
        if any(x in msg for x in ("no match", "not found", "nxdomain")):
            return f"Domain '{domain}' appears to be available."
        return f"WHOIS lookup failed for '{domain}'."


# ── OpenCorporates ────────────────────────────────────────────────────────────

def opencorporates_search(company_name: str, jurisdiction: str = "") -> str:
    try:
        params = f"q={quote(company_name)}"
        if jurisdiction:
            params += f"&jurisdiction_code={quote(jurisdiction)}"
        url = f"https://api.opencorporates.com/v0.4/companies/search?{params}"
        r = httpx.get(url, headers=_headers(), timeout=_TIMEOUT, follow_redirects=True)
        r.raise_for_status()
        companies = r.json().get("results", {}).get("companies", [])
        if not companies:
            return f"No company registrations found for: {company_name}"

        lines = [f"OpenCorporates — top results for '{company_name}':"]
        for entry in companies[:5]:
            co = entry.get("company", {})
            name = co.get("name", "?")
            jur = co.get("jurisdiction_code", "?").upper()
            number = co.get("company_number", "?")
            inc = co.get("incorporation_date") or "unknown"
            status = co.get("current_status") or "unknown"
            oc_url = co.get("opencorporates_url", "")
            line = f"• {name} [{jur}] #{number} — incorporated {inc}, status: {status}"
            if oc_url:
                line += f"\n  {oc_url}"
            lines.append(line)
        return _finalize("\n\n".join(lines))
    except Exception:
        return "OpenCorporates search failed."


# ── URL Safety Check ──────────────────────────────────────────────────────────

def url_safety_check(url: str) -> str:
    vt_key = os.environ.get("VIRUSTOTAL_API_KEY", "")

    if vt_key:
        try:
            r = httpx.get(
                "https://www.virustotal.com/vtapi/v2/url/report",
                params={"apikey": vt_key, "resource": url},
                headers=_headers(),
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            data = r.json()
            if data.get("response_code") == 1:
                positives = data.get("positives", 0)
                total = data.get("total", 0)
                scan_date = data.get("scan_date", "unknown")
                verdict = "safe" if positives == 0 else ("suspicious" if positives <= 3 else "dangerous")
                return _finalize(f"URL safety (VirusTotal): {verdict}\n{url}\nReason: {positives}/{total} engines flagged (as of {scan_date})")
        except Exception:
            pass

    # Heuristic fallback
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().lstrip("www.")
        tld = "." + domain.rsplit(".", 1)[-1] if "." in domain else ""
        flags = []
        _SUSPICIOUS_TLDS = {".xyz", ".tk", ".ml", ".ga", ".cf", ".gq", ".pw", ".top", ".click", ".loan"}
        if tld in _SUSPICIOUS_TLDS:
            flags.append(f"suspicious TLD ({tld})")
        _PHISHING_RE = re.compile(
            r"(paypa[l1]|[a@]pp[l1]e|[a@]mazon|micr[o0]s[o0]ft|[a@]ccount.{0,10}verif|"
            r"[a@]ccount.{0,10}suspend|login.{0,10}secure|secure.{0,10}login)",
            re.IGNORECASE,
        )
        if _PHISHING_RE.search(url):
            flags.append("matches phishing URL pattern")
        verdict = "suspicious (heuristic)" if flags else "safe (heuristic)"
        reason = "; ".join(flags) if flags else "No suspicious patterns detected."
        return _finalize(f"URL safety (heuristic): {verdict}\n{url}\nReason: {reason}\n(Set VIRUSTOTAL_API_KEY for authoritative results.)")
    except Exception:
        return "URL safety check failed."


# ── Arxiv ─────────────────────────────────────────────────────────────────────

def arxiv_search(query: str, limit: int = 5) -> str:
    try:
        limit = min(max(1, limit), 10)
        url = (
            f"https://export.arxiv.org/api/query"
            f"?search_query=all:{quote(query)}&start=0&max_results={limit}"
        )
        r = httpx.get(url, headers=_headers(), timeout=_TIMEOUT, follow_redirects=True)
        r.raise_for_status()

        import xml.etree.ElementTree as ET
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(r.text)
        entries = root.findall("atom:entry", ns)
        if not entries:
            return f"No arxiv results for: {query}"

        lines = [f"Arxiv — '{query}' ({len(entries)} results):"]
        for entry in entries:
            title = (entry.findtext("atom:title", "", ns) or "").strip().replace("\n", " ")
            summary = (entry.findtext("atom:summary", "", ns) or "").strip()[:300].replace("\n", " ")
            link = ""
            for link_el in entry.findall("atom:link", ns):
                if link_el.get("rel") == "alternate":
                    link = link_el.get("href", "")
                    break
            authors = [a.findtext("atom:name", "", ns) for a in entry.findall("atom:author", ns)]
            author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
            block = f"• {title}\n  {author_str}"
            if link:
                block += f"\n  {link}"
            if summary:
                block += f"\n  {summary}"
            lines.append(block)
        return _finalize("\n\n".join(lines))
    except Exception as e:
        return f"Arxiv search failed: {e}"


# ── YouTube Transcript ────────────────────────────────────────────────────────

def youtube_transcript(video_id_or_url: str) -> str:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
        from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound  # type: ignore
    except ImportError:
        return "youtube-transcript-api not installed — add 'youtube-transcript-api' to requirements.txt."

    # Extract video ID from URL if needed
    video_id = video_id_or_url.strip()
    if "youtube.com" in video_id or "youtu.be" in video_id:
        import re as _re
        m = _re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", video_id)
        if m:
            video_id = m.group(1)
        else:
            return "Could not extract video ID from URL."

    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join(item["text"] for item in transcript_list)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > _MAX_CHARS:
            text = text[:_MAX_CHARS] + "\n[truncated]"
        return _finalize(f"YouTube transcript ({video_id}):\n\n{text}")
    except TranscriptsDisabled:
        return f"Transcripts are disabled for video: {video_id}"
    except NoTranscriptFound:
        return f"No transcript found for video: {video_id}"
    except Exception as e:
        return f"Transcript fetch failed: {e}"
