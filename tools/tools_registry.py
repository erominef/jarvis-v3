# tools/tools_registry.py — Tool schemas and dispatch.
#
# get_tool_schemas() → list of Ollama/OpenAI-format tool dicts.
# dispatch_tool(name, args) → str result (never raises).

import json as _json

from tools.web import web_search, web_fetch
from tools.memory_tools import knowledge_add, knowledge_search, memory_note
from tools.research import (
    wikipedia_search, hn_search, reddit_search, rss_fetch, wayback_fetch,
    google_trends, github_trending, github_search, whois_lookup,
    opencorporates_search, url_safety_check, arxiv_search, youtube_transcript,
)
from tools.services import (
    searxng_search, playwright_scrape, n8n_trigger, docuseal_send,
    comfyui_generate, stripe_op, http_request,
)
from tools.documents import (
    draft_pptx, draft_docx, draft_xlsx, generate_qr,
    render_diagram, render_template, financial_calc, pdf_extract,
)
from tools.shell import shell_run
from tools.git_tools import git_op
from tools.files import file_read, file_write, file_list
from tools.finance import stock_price, crypto_price, exchange_rate
from tools.data import data_analyze
from tools.goals import goal_manager
from tools.tasks import task_manager
from tools.notify import telegram_notify
from tools.code_runner import code_execute
from tools.email_tools import email_send, email_read
from tools.infra import system_health, docker_restart

_TOOLS = {
    # ── Web ──────────────────────────────────────────────────────────────────
    "web_search": {
        "fn": lambda a: web_search(a["query"]),
        "schema": {"type": "function", "function": {
            "name": "web_search",
            "description": "Search the web using DuckDuckGo. Returns a summary and results.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        }},
    },
    "web_fetch": {
        "fn": lambda a: web_fetch(a["url"]),
        "schema": {"type": "function", "function": {
            "name": "web_fetch",
            "description": "Fetch and extract text content from a URL.",
            "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
        }},
    },

    # ── Memory ────────────────────────────────────────────────────────────────
    "knowledge_add": {
        "fn": lambda a: knowledge_add(a["content"], a.get("title", "")),
        "schema": {"type": "function", "function": {
            "name": "knowledge_add",
            "description": "Save a document or fact to the persistent knowledge base for future retrieval.",
            "parameters": {"type": "object", "properties": {
                "content": {"type": "string", "description": "Text content to store."},
                "title": {"type": "string", "description": "Optional title."},
            }, "required": ["content"]},
        }},
    },
    "knowledge_search": {
        "fn": lambda a: knowledge_search(a["query"]),
        "schema": {"type": "function", "function": {
            "name": "knowledge_search",
            "description": "Semantically search the knowledge base for relevant stored documents.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        }},
    },
    "memory_note": {
        "fn": lambda a: memory_note(a["content"]),
        "schema": {"type": "function", "function": {
            "name": "memory_note",
            "description": "Save a short note or observation to episodic memory.",
            "parameters": {"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]},
        }},
    },

    # ── Research ──────────────────────────────────────────────────────────────
    "searxng_search": {
        "fn": lambda a: searxng_search(a["query"], a.get("categories", "general"), int(a.get("limit", 10))),
        "schema": {"type": "function", "function": {
            "name": "searxng_search",
            "description": "Search the web using private SearXNG. Better than web_search — use this for general searches.",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string"},
                "categories": {"type": "string", "description": "general | news | science | it (default: general)"},
                "limit": {"type": "integer", "description": "Results to return (default 10)"},
            }, "required": ["query"]},
        }},
    },
    "wikipedia_search": {
        "fn": lambda a: wikipedia_search(a["query"], int(a.get("sentences", 5))),
        "schema": {"type": "function", "function": {
            "name": "wikipedia_search",
            "description": "Search Wikipedia and return a summary.",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string"},
                "sentences": {"type": "integer", "description": "Number of summary sentences (default 5)"},
            }, "required": ["query"]},
        }},
    },
    "hn_search": {
        "fn": lambda a: hn_search(a["query"], int(a.get("limit", 10))),
        "schema": {"type": "function", "function": {
            "name": "hn_search",
            "description": "Search Hacker News stories via Algolia.",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "description": "Number of results (default 10)"},
            }, "required": ["query"]},
        }},
    },
    "reddit_search": {
        "fn": lambda a: reddit_search(a["subreddit"], a.get("query", ""), int(a.get("limit", 10)), a.get("sort", "hot")),
        "schema": {"type": "function", "function": {
            "name": "reddit_search",
            "description": "Browse or search a subreddit. No auth needed for public subreddits.",
            "parameters": {"type": "object", "properties": {
                "subreddit": {"type": "string", "description": "Subreddit name (without r/)"},
                "query": {"type": "string", "description": "Search query (optional — omit to get hot posts)"},
                "limit": {"type": "integer", "description": "Number of posts (default 10)"},
                "sort": {"type": "string", "description": "hot | new | top (default hot)"},
            }, "required": ["subreddit"]},
        }},
    },
    "rss_fetch": {
        "fn": lambda a: rss_fetch(a["feed_url"], int(a.get("limit", 10))),
        "schema": {"type": "function", "function": {
            "name": "rss_fetch",
            "description": "Fetch and parse an RSS or Atom feed. Returns titles, links, and summaries.",
            "parameters": {"type": "object", "properties": {
                "feed_url": {"type": "string"},
                "limit": {"type": "integer", "description": "Number of entries (default 10)"},
            }, "required": ["feed_url"]},
        }},
    },
    "wayback_fetch": {
        "fn": lambda a: wayback_fetch(a["url"]),
        "schema": {"type": "function", "function": {
            "name": "wayback_fetch",
            "description": "Fetch the most recent Wayback Machine snapshot of a URL. Useful for historical research.",
            "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
        }},
    },
    "google_trends": {
        "fn": lambda a: google_trends(a["keywords"], a.get("timeframe", "today 12-m")),
        "schema": {"type": "function", "function": {
            "name": "google_trends",
            "description": "Get Google Trends interest data for up to 5 keywords.",
            "parameters": {"type": "object", "properties": {
                "keywords": {"type": "array", "items": {"type": "string"}, "description": "Up to 5 keywords"},
                "timeframe": {"type": "string", "description": "e.g. 'today 12-m', 'today 3-m' (default: today 12-m)"},
            }, "required": ["keywords"]},
        }},
    },
    "github_trending": {
        "fn": lambda a: github_trending(a.get("language", ""), a.get("period", "daily")),
        "schema": {"type": "function", "function": {
            "name": "github_trending",
            "description": "Get trending GitHub repos. Filter by language and period.",
            "parameters": {"type": "object", "properties": {
                "language": {"type": "string", "description": "Programming language filter (optional)"},
                "period": {"type": "string", "description": "daily | weekly | monthly (default daily)"},
            }},
        }},
    },
    "github_search": {
        "fn": lambda a: github_search(a["query"], a.get("type", "repositories"), int(a.get("limit", 5))),
        "schema": {"type": "function", "function": {
            "name": "github_search",
            "description": "Search public GitHub repositories, issues, or users.",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string"},
                "type": {"type": "string", "description": "repositories | issues | users (default: repositories)"},
                "limit": {"type": "integer", "description": "Number of results (default 5)"},
            }, "required": ["query"]},
        }},
    },
    "whois_lookup": {
        "fn": lambda a: whois_lookup(a["domain"]),
        "schema": {"type": "function", "function": {
            "name": "whois_lookup",
            "description": "Look up WHOIS registration info for a domain. Reports availability if unregistered.",
            "parameters": {"type": "object", "properties": {"domain": {"type": "string"}}, "required": ["domain"]},
        }},
    },
    "opencorporates_search": {
        "fn": lambda a: opencorporates_search(a["company_name"], a.get("jurisdiction", "")),
        "schema": {"type": "function", "function": {
            "name": "opencorporates_search",
            "description": "Search company registrations via OpenCorporates (free, global).",
            "parameters": {"type": "object", "properties": {
                "company_name": {"type": "string"},
                "jurisdiction": {"type": "string", "description": "e.g. 'us_de' for Delaware (optional)"},
            }, "required": ["company_name"]},
        }},
    },
    "url_safety_check": {
        "fn": lambda a: url_safety_check(a["url"]),
        "schema": {"type": "function", "function": {
            "name": "url_safety_check",
            "description": "Check if a URL is safe or suspicious using VirusTotal or heuristics.",
            "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
        }},
    },
    "arxiv_search": {
        "fn": lambda a: arxiv_search(a["query"], int(a.get("limit", 5))),
        "schema": {"type": "function", "function": {
            "name": "arxiv_search",
            "description": "Search academic papers on arxiv.org.",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "description": "Number of results (default 5)"},
            }, "required": ["query"]},
        }},
    },
    "youtube_transcript": {
        "fn": lambda a: youtube_transcript(a["video_id_or_url"]),
        "schema": {"type": "function", "function": {
            "name": "youtube_transcript",
            "description": "Fetch the transcript of a YouTube video by URL or video ID.",
            "parameters": {"type": "object", "properties": {"video_id_or_url": {"type": "string"}}, "required": ["video_id_or_url"]},
        }},
    },

    # ── Browser ───────────────────────────────────────────────────────────────
    "playwright_scrape": {
        "fn": lambda a: playwright_scrape(a["url"], a.get("action", "content")),
        "schema": {"type": "function", "function": {
            "name": "playwright_scrape",
            "description": "Scrape a JS-rendered page using Playwright. Use when web_fetch fails on JS-heavy sites.",
            "parameters": {"type": "object", "properties": {
                "url": {"type": "string"},
                "action": {"type": "string", "description": "content | screenshot (default: content)"},
            }, "required": ["url"]},
        }},
    },

    # ── Files ─────────────────────────────────────────────────────────────────
    "file_read": {
        "fn": lambda a: file_read(a["path"]),
        "schema": {"type": "function", "function": {
            "name": "file_read",
            "description": "Read a file from workspace/. Always use this for workspace file access.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Path relative to workspace/ (e.g. 'report.md')"}}, "required": ["path"]},
        }},
    },
    "file_write": {
        "fn": lambda a: file_write(a["path"], a["content"]),
        "schema": {"type": "function", "function": {
            "name": "file_write",
            "description": "Write content to a file in workspace/. Creates directories as needed.",
            "parameters": {"type": "object", "properties": {
                "path": {"type": "string", "description": "Path relative to workspace/"},
                "content": {"type": "string"},
            }, "required": ["path", "content"]},
        }},
    },
    "file_list": {
        "fn": lambda a: file_list(a.get("subpath", "")),
        "schema": {"type": "function", "function": {
            "name": "file_list",
            "description": "List files and directories under workspace/ or a subpath.",
            "parameters": {"type": "object", "properties": {
                "subpath": {"type": "string", "description": "Subdirectory within workspace/ (optional)"},
            }},
        }},
    },

    # ── Finance ───────────────────────────────────────────────────────────────
    "stock_price": {
        "fn": lambda a: stock_price(a["symbol"]),
        "schema": {"type": "function", "function": {
            "name": "stock_price",
            "description": "Get real-time stock price from Yahoo Finance. No API key required.",
            "parameters": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Ticker symbol e.g. AAPL, TSLA"}}, "required": ["symbol"]},
        }},
    },
    "crypto_price": {
        "fn": lambda a: crypto_price(a["symbol"]),
        "schema": {"type": "function", "function": {
            "name": "crypto_price",
            "description": "Get real-time crypto price from CoinGecko. No API key required.",
            "parameters": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Symbol e.g. btc, eth, sol"}}, "required": ["symbol"]},
        }},
    },
    "exchange_rate": {
        "fn": lambda a: exchange_rate(a["from_currency"], a["to_currency"]),
        "schema": {"type": "function", "function": {
            "name": "exchange_rate",
            "description": "Get current exchange rate between two currencies.",
            "parameters": {"type": "object", "properties": {
                "from_currency": {"type": "string", "description": "e.g. USD"},
                "to_currency": {"type": "string", "description": "e.g. EUR"},
            }, "required": ["from_currency", "to_currency"]},
        }},
    },

    # ── Data analysis ─────────────────────────────────────────────────────────
    "data_analyze": {
        "fn": lambda a: data_analyze(a["path"]),
        "schema": {"type": "function", "function": {
            "name": "data_analyze",
            "description": "Load a CSV or JSON file from workspace/ and return pandas summary statistics.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Path relative to workspace/"}}, "required": ["path"]},
        }},
    },

    # ── Documents ─────────────────────────────────────────────────────────────
    "draft_pptx": {
        "fn": lambda a: draft_pptx(a["filename"], a["slides"]),
        "schema": {"type": "function", "function": {
            "name": "draft_pptx",
            "description": "Generate a PowerPoint presentation and save to workspace/.",
            "parameters": {"type": "object", "properties": {
                "filename": {"type": "string", "description": "Output filename ending in .pptx"},
                "slides": {"type": "array", "items": {"type": "object", "properties": {
                    "title": {"type": "string"}, "content": {"type": "string"}, "notes": {"type": "string"},
                }}, "description": "List of slide objects with title, content, notes"},
            }, "required": ["filename", "slides"]},
        }},
    },
    "draft_docx": {
        "fn": lambda a: draft_docx(a["filename"], a["content"], a.get("title", "")),
        "schema": {"type": "function", "function": {
            "name": "draft_docx",
            "description": "Generate a Word document from Markdown-like text and save to workspace/.",
            "parameters": {"type": "object", "properties": {
                "filename": {"type": "string", "description": "Output filename ending in .docx"},
                "content": {"type": "string", "description": "Markdown-like content (# headings, - bullets, **bold**, *italic*)"},
                "title": {"type": "string", "description": "Optional document title"},
            }, "required": ["filename", "content"]},
        }},
    },
    "draft_xlsx": {
        "fn": lambda a: draft_xlsx(a["filename"], a["sheets"]),
        "schema": {"type": "function", "function": {
            "name": "draft_xlsx",
            "description": "Generate an Excel workbook and save to workspace/.",
            "parameters": {"type": "object", "properties": {
                "filename": {"type": "string", "description": "Output filename ending in .xlsx"},
                "sheets": {"type": "array", "items": {"type": "object", "properties": {
                    "name": {"type": "string"}, "headers": {"type": "array", "items": {"type": "string"}},
                    "rows": {"type": "array", "items": {"type": "array"}},
                }}},
            }, "required": ["filename", "sheets"]},
        }},
    },
    "generate_qr": {
        "fn": lambda a: generate_qr(a["filename"], a["data"], int(a.get("size", 10))),
        "schema": {"type": "function", "function": {
            "name": "generate_qr",
            "description": "Generate a QR code PNG and save to workspace/.",
            "parameters": {"type": "object", "properties": {
                "filename": {"type": "string", "description": "Output filename ending in .png"},
                "data": {"type": "string", "description": "URL or text to encode"},
                "size": {"type": "integer", "description": "Box size in pixels (default 10)"},
            }, "required": ["filename", "data"]},
        }},
    },
    "render_diagram": {
        "fn": lambda a: render_diagram(a["filename"], a["diagram_code"], a.get("diagram_type", "mermaid")),
        "schema": {"type": "function", "function": {
            "name": "render_diagram",
            "description": "Render a Mermaid or Graphviz diagram to PNG/SVG and save to workspace/.",
            "parameters": {"type": "object", "properties": {
                "filename": {"type": "string", "description": "Output filename (.png or .svg)"},
                "diagram_code": {"type": "string"},
                "diagram_type": {"type": "string", "description": "mermaid | graphviz (default: mermaid)"},
            }, "required": ["filename", "diagram_code"]},
        }},
    },
    "render_template": {
        "fn": lambda a: render_template(a["filename"], a["template_str"], a.get("variables", {})),
        "schema": {"type": "function", "function": {
            "name": "render_template",
            "description": "Render a Jinja2 template with variables and save to workspace/.",
            "parameters": {"type": "object", "properties": {
                "filename": {"type": "string"},
                "template_str": {"type": "string", "description": "Jinja2 template content"},
                "variables": {"type": "object", "description": "Template variables dict"},
            }, "required": ["filename", "template_str"]},
        }},
    },
    "financial_calc": {
        "fn": lambda a: financial_calc(a["calc_type"], a["params"], a.get("filename", "")),
        "schema": {"type": "function", "function": {
            "name": "financial_calc",
            "description": "Run financial calculations: projection, break_even, market_size, roi.",
            "parameters": {"type": "object", "properties": {
                "calc_type": {"type": "string", "description": "projection | break_even | market_size | roi"},
                "params": {"type": "object", "description": "Calculation parameters (see tool description)"},
                "filename": {"type": "string", "description": "Optional workspace path to save the output"},
            }, "required": ["calc_type", "params"]},
        }},
    },
    "pdf_extract": {
        "fn": lambda a: pdf_extract(a["path"]),
        "schema": {"type": "function", "function": {
            "name": "pdf_extract",
            "description": "Extract text from a PDF file in workspace/.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Path relative to workspace/"}}, "required": ["path"]},
        }},
    },

    # ── Shell ─────────────────────────────────────────────────────────────────
    "shell_run": {
        "fn": lambda a: shell_run(a["command"]),
        "schema": {"type": "function", "function": {
            "name": "shell_run",
            "description": "Run a whitelisted shell command on the PC (ls, df, uptime, date, etc.).",
            "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
        }},
    },

    # ── Git ───────────────────────────────────────────────────────────────────
    "git_op": {
        "fn": lambda a: git_op(a["action"], **{k: v for k, v in a.items() if k != "action"}),
        "schema": {"type": "function", "function": {
            "name": "git_op",
            "description": "Gitea git operations. Read: list_repos, get_repo, list_files, read_file, log. Write: create_repo, write_file, delete_repo.",
            "parameters": {"type": "object", "properties": {
                "action": {"type": "string"},
                "repo": {"type": "string", "description": "owner/repo format"},
                "path": {"type": "string"},
                "content": {"type": "string"},
                "message": {"type": "string", "description": "Commit message for write_file"},
                "name": {"type": "string", "description": "Repo name for create_repo"},
                "description": {"type": "string"},
                "private": {"type": "boolean"},
                "ref": {"type": "string", "description": "Branch/tag (default: main)"},
                "limit": {"type": "integer"},
            }, "required": ["action"]},
        }},
    },

    # ── Automation ────────────────────────────────────────────────────────────
    "n8n_trigger": {
        "fn": lambda a: n8n_trigger(a["workflow_name"], a.get("data", {})),
        "schema": {"type": "function", "function": {
            "name": "n8n_trigger",
            "description": "Trigger an n8n automation workflow by name.",
            "parameters": {"type": "object", "properties": {
                "workflow_name": {"type": "string", "description": "Partial workflow name match (case-insensitive)"},
                "data": {"type": "object", "description": "Payload to send (optional)"},
            }, "required": ["workflow_name"]},
        }},
    },

    # ── Documents/Signing ─────────────────────────────────────────────────────
    "docuseal_send": {
        "fn": lambda a: docuseal_send(a["filename"], a["signer_email"], a["signer_name"], a.get("document_title", "")),
        "schema": {"type": "function", "function": {
            "name": "docuseal_send",
            "description": "Send a workspace document for e-signature via DocuSeal.",
            "parameters": {"type": "object", "properties": {
                "filename": {"type": "string", "description": "Path to PDF/DOCX in workspace/"},
                "signer_email": {"type": "string"},
                "signer_name": {"type": "string"},
                "document_title": {"type": "string", "description": "Optional title override"},
            }, "required": ["filename", "signer_email", "signer_name"]},
        }},
    },

    # ── Image generation ──────────────────────────────────────────────────────
    "comfyui_generate": {
        "fn": lambda a: comfyui_generate(a["prompt"], a["filename"], a.get("negative_prompt", ""), int(a.get("steps", 20)), int(a.get("width", 512)), int(a.get("height", 512))),
        "schema": {"type": "function", "function": {
            "name": "comfyui_generate",
            "description": "Generate an image via ComfyUI on Xeon. Saves to workspace/.",
            "parameters": {"type": "object", "properties": {
                "prompt": {"type": "string"},
                "filename": {"type": "string", "description": "Output path in workspace/ (e.g. images/output.png)"},
                "negative_prompt": {"type": "string"},
                "steps": {"type": "integer", "description": "Inference steps (default 20)"},
                "width": {"type": "integer", "description": "Image width (default 512)"},
                "height": {"type": "integer", "description": "Image height (default 512)"},
            }, "required": ["prompt", "filename"]},
        }},
    },

    # ── Payments ──────────────────────────────────────────────────────────────
    "stripe_op": {
        "fn": lambda a: stripe_op(a["action"], a.get("params", {})),
        "schema": {"type": "function", "function": {
            "name": "stripe_op",
            "description": "Stripe payment operations: create_payment_link, list_payments, check_revenue.",
            "parameters": {"type": "object", "properties": {
                "action": {"type": "string", "description": "create_payment_link | list_payments | check_revenue"},
                "params": {"type": "object", "description": "For create_payment_link: {product_name, amount_cents, currency, quantity}"},
            }, "required": ["action"]},
        }},
    },

    # ── Goals/Tasks ───────────────────────────────────────────────────────────
    "goal_manager": {
        "fn": lambda a: goal_manager(a["action"], **{k: v for k, v in a.items() if k != "action"}),
        "schema": {"type": "function", "function": {
            "name": "goal_manager",
            "description": "Manage goals. Actions: list, get, add, update.",
            "parameters": {"type": "object", "properties": {
                "action": {"type": "string", "enum": ["list", "get", "add", "update"]},
                "goal_id": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "status": {"type": "string", "enum": ["active", "paused", "done"]},
                "progress": {"type": "string"},
                "priority": {"type": "integer", "minimum": 1, "maximum": 10},
            }, "required": ["action"]},
        }},
    },
    "task_manager": {
        "fn": lambda a: task_manager(a["action"], **{k: v for k, v in a.items() if k != "action"}),
        "schema": {"type": "function", "function": {
            "name": "task_manager",
            "description": "Track tasks. Actions: list_pending, list_recent, create, update_progress.",
            "parameters": {"type": "object", "properties": {
                "action": {"type": "string", "enum": ["list_pending", "list_recent", "create", "update_progress"]},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "task_id": {"type": "string"},
                "note": {"type": "string"},
                "status": {"type": "string", "description": "done | failed (for update_progress)"},
            }, "required": ["action"]},
        }},
    },

    # ── Notifications ─────────────────────────────────────────────────────────
    "telegram_notify": {
        "fn": lambda a: telegram_notify(a["message"]),
        "schema": {"type": "function", "function": {
            "name": "telegram_notify",
            "description": "Send a proactive Telegram message to the owner. Use sparingly for important updates.",
            "parameters": {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]},
        }},
    },

    # ── Code execution ────────────────────────────────────────────────────────
    "code_execute": {
        "fn": lambda a: code_execute(a["code"]),
        "schema": {"type": "function", "function": {
            "name": "code_execute",
            "description": "Execute Python code in a sandboxed environment. No network or filesystem access. Use for calculations, data processing, and logic.",
            "parameters": {"type": "object", "properties": {"code": {"type": "string", "description": "Python code to execute"}}, "required": ["code"]},
        }},
    },

    # ── Email ─────────────────────────────────────────────────────────────────
    "email_send": {
        "fn": lambda a: email_send(a["to"], a["subject"], a["body"]),
        "schema": {"type": "function", "function": {
            "name": "email_send",
            "description": "Send an email via the configured SMTP server.",
            "parameters": {"type": "object", "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            }, "required": ["to", "subject", "body"]},
        }},
    },
    "email_read": {
        "fn": lambda a: email_read(a.get("folder", "INBOX"), int(a.get("limit", 10)), bool(a.get("unread_only", True))),
        "schema": {"type": "function", "function": {
            "name": "email_read",
            "description": "Read emails from the configured inbox.",
            "parameters": {"type": "object", "properties": {
                "folder": {"type": "string", "description": "INBOX | SENT | etc (default INBOX)"},
                "limit": {"type": "integer", "description": "Number of messages (default 10)"},
                "unread_only": {"type": "boolean", "description": "Only unread messages (default true)"},
            }},
        }},
    },

    # ── HTTP ──────────────────────────────────────────────────────────────────
    "http_request": {
        "fn": lambda a: http_request(a["method"], a["url"], a.get("headers", {}), a.get("json_body", {})),
        "schema": {"type": "function", "function": {
            "name": "http_request",
            "description": "Make a GET or POST HTTP request to any external URL. Internal/private IPs are blocked.",
            "parameters": {"type": "object", "properties": {
                "method": {"type": "string", "enum": ["GET", "POST"]},
                "url": {"type": "string"},
                "headers": {"type": "object", "description": "Optional request headers"},
                "json_body": {"type": "object", "description": "Optional JSON body (POST only)"},
            }, "required": ["method", "url"]},
        }},
    },

    # ── Infrastructure ────────────────────────────────────────────────────────
    "system_health": {
        "fn": lambda a: system_health(),
        "schema": {"type": "function", "function": {
            "name": "system_health",
            "description": "Check PC system metrics (CPU, RAM, disk) and Xeon service health.",
            "parameters": {"type": "object", "properties": {}},
        }},
    },
    "docker_restart": {
        "fn": lambda a: docker_restart(a["service"]),
        "schema": {"type": "function", "function": {
            "name": "docker_restart",
            "description": "Restart an allowlisted PC Docker service (searxng, playwright, docuseal).",
            "parameters": {"type": "object", "properties": {
                "service": {"type": "string", "description": "Service name: searxng | playwright | docuseal"},
            }, "required": ["service"]},
        }},
    },
}


def get_tool_schemas() -> list:
    return [entry["schema"] for entry in _TOOLS.values()]


def dispatch_tool(name: str, args: dict) -> str:
    entry = _TOOLS.get(name)
    if not entry:
        return f"Error: unknown tool '{name}'."
    try:
        result = entry["fn"](args)
        if isinstance(result, dict):
            return _json.dumps(result)
        return str(result)
    except Exception as e:
        return f"Tool error ({name}): {e}"
