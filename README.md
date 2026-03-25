# Jarvis v3 — Minimal Core, Maximum Tooling

A ground-up rebuild focused on one question: how much of v2's architecture was solving real problems, and how much was compensating for weak models?

The answer: a lot of it was the models.

v2 ran a Manager/Planner/Executor/Evaluator pattern across three concurrent asyncio loops because local 7–14B models couldn't reliably complete multi-step tasks without scaffolding to keep them on track. Routing logic, fallback chains, lean vs. full system prompts, stuck-goal detection — all of that existed to nurse local models through work they could barely do. v3 runs a cloud-primary model capable enough that most of that machinery isn't needed anymore. The agent went from ~2,200 lines of orchestration to a 120-line sync brain loop. Tool count went from 42 to 50. Memory went from file-based keyword search to vector-embedded semantic RAG.

The system is simpler and more capable simultaneously.

**v1 (TypeScript, reactive):** https://github.com/erominef/jarvis
**v2 (Python, autonomous):** https://github.com/erominef/jarvis-v2
**v3 (Python, minimal core):** this repository

---

> **Public-safety note:** This is a sanitized case study. Source files are included as documented stubs — actual endpoints, credentials, and working configs are intentionally omitted. A private implementation can be shared on request.

---

## The Progression

### v1 — TypeScript, Reactive, Local-Only

Built on grammY. One message in, one reply out. 5 tools. 6-tier local model stack running on two machines. The routing classifier was a three-stage regex chain. It worked well for Q&A and quick tasks but did nothing without prompting.

Key limitation: it couldn't pursue work on its own. The hardware was underutilized between messages. If you wanted something done you had to ask, wait, get a partial result, ask again.

### v2 — Python, Autonomous, Cloud-Primary

Complete rewrite. The architecture changed from one-shot response to three concurrent asyncio loops:

- **Planning loop** (30-min cycle): select goal → planner decomposes into tasks → executor runs → evaluator grades → update progress
- **Initiative loop** (5-min tick): flush task completion notifications, rate-limited proactive reasoning
- **Interactive loop**: Telegram → per-chat queue → agent → streamed reply

42 tools. The full capability breakdown is in the v2 README.

The complexity worked but revealed its own problems. The Planner/Executor/Evaluator chain was fragile — a single bad evaluation could stall a goal for hours. The initiative loop needed per-action rate-limits, wall-clock persistence for dedup, workspace file injection to prevent redundant dispatches, and multiple rounds of parameter tuning before it stopped spamming. The routing matrix grew to handle every edge case of model capability vs. context window vs. task type.

Most of that complexity was load-bearing only because of local model limitations. Cloud-primary inference made the question obvious: if a single capable model can maintain context and follow multi-step instructions reliably, what's the scaffolding for?

### v3 — Minimal Core, Semantic Memory, 50 Tools

The architecture went backward in complexity, forward in capability:

- Single sync `process_turn()` — builds system prompt, sends to LLM, loops on tool calls, returns reply
- No planning loop. No evaluator. No routing matrix.
- Semantic RAG memory (ChromaDB, all-MiniLM-L6-v2) instead of keyword search over markdown files
- Episodic memory: every conversation exchange recorded to a separate vector collection, semantically searchable
- 50 tools organized across 10 domains
- All tool execution is sync — no asyncio anywhere in the tool stack

The Xeon's role changed from running inference to running microservices. Instead of a local model fallback, the Xeon hosts the memory API, code execution sandbox, email relay, and browser automation.

---

## Hardware

| Role | Machine | CPU | RAM | Notes |
|------|---------|-----|-----|-------|
| Dev | MacBook | M-series | — | Source of truth. Never runs inference or services. |
| Agent runtime | Ubuntu PC | Intel i7-6700 (Skylake, AVX2) | 16 GB | Runs jarvis-v3 in a venv. Calls cloud LLM and Xeon APIs. |
| Tool execution | Xeon workstation | 2× Intel X5670 (Westmere, SSE4.2) | 64 GB | All Docker services. Memory, code sandbox, email, browser. |

The PC's role in v3 is lightweight: it runs the Python agent process, handles the Telegram interface, and calls HTTP APIs. No Docker, no local inference.

The Xeon in v3 is a services layer, not an inference machine. Its Ollama install is no longer in the hot path — all inference goes to cloud.

---

## Model

Single cloud-hosted model via the Ollama API. Not self-hosted — a cloud-served API endpoint with a 128k context window. Local models are no longer in the runtime path.

Compared to the largest local models in v1/v2 (14B, ~1.4 tok/s on CPU), the cloud model handles tool schemas and multi-step reasoning without scaffolding. The planning loop, routing matrix, lean/full system prompt split, and Xeon context window workarounds all existed because local models needed them. None of those apply here.

v2 kept local as primary when cloud was unavailable. v3 doesn't have a local fallback — if cloud is down, the agent is down. The tradeoff is acceptable for a single-owner system.

---

## Architecture

### v2 — Three Concurrent Loops

```
┌──────────────────────────────────────────────────────┐
│                  Docker Container                     │
│                                                       │
│  Planning Loop    Initiative Loop    Interactive      │
│  (30-min cycle)   (5-min tick)       (Telegram)       │
│       │                │                 │            │
│       └────────────────┴─────────────────┘            │
│                        │                              │
│                     Manager                           │
│                        │                              │
│          ┌─────────────┼─────────────┐                │
│       Planner       Executor      Evaluator           │
└──────────────────────────────────────────────────────┘
                         │
           Cloud LLM / Local Ollama fallback
```

### v3 — Single Sync Loop

```
Telegram message
       │
       ▼
 interfaces/telegram.py
       │
  run_in_executor()          ← keeps async event loop unblocked
       │
       ▼
 brain.process_turn()
       │
  1. build_system_prompt()   ← SOUL.md + tool guidance + RAG + episodes
  2. send to cloud LLM       ← httpx, non-streaming, tools injected
  3. tool_calls in response?
       │ yes                 no
       ▼                      ▼
  dispatch_tool()          return reply
       │
  append result to messages
       │
  loop (max 10 rounds)
```

Everything is synchronous inside `process_turn()`. The Telegram handler uses `asyncio.run_in_executor()` to avoid blocking the event loop during LLM calls.

---

## Memory Architecture

This is the largest structural change from v2. v2 stored memory as markdown files on disk with keyword search — `grep`-based and brittle. v3 uses a ChromaDB vector store running on the Xeon.

```
PC (jarvis-v3)                        Xeon (port 8083)
──────────────                        ────────────────
build_system_prompt(user_input)
  │
  ├─► search_knowledge(query, n=3) ──► /knowledge/search
  │     results injected into prompt    chromadb collection
  │                                     all-MiniLM-L6-v2 embeddings
  └─► search_episodes(query, n=5)  ──► /episodes/search
        results injected into prompt    chromadb collection

After each turn:
  record_episode(user_text, reply)  ──► /episodes/add
```

**Two collections:**

- `knowledge` — static documents and facts. Chunked (500 chars / 50 overlap), embedded, stored permanently. The `knowledge_add` tool writes here.
- `episodes` — conversational memory. Every exchange is recorded as a single document with a timestamp. The `memory_note` tool also writes here. Searched at the start of every turn.

Both search before every response — the system prompt is always personalized to the current context. A Xeon outage is non-fatal: the memory client returns empty on any error and the brain continues without it.

---

## Xeon Microservices

The Xeon runs five Docker services. Each is isolated in `/opt/jarvis/services/<name>/` with its own `docker-compose.yml` and `app/` directory. No global installs, no systemd services.

| Service | Port | What it does |
|---------|------|-------------|
| `memory` | 8083 | ChromaDB + FastAPI. Knowledge and episode vector store. |
| `code-runner` | 8084 | Python execution sandbox. AST import scan, 30s timeout, no network. |
| `email` | 8085 | SMTP send + IMAP read via FastAPI. Credentials injected via env vars. |
| `playwright` | 8082 | Headless Chromium browser automation for JS-rendered pages. |
| `searxng` | 8081 | Self-hosted meta-search engine. Aggregates multiple engines. |

**Code runner security model:** The sandbox rejects any `import` not on a stdlib allowlist (`math`, `json`, `re`, `datetime`, `collections`, `itertools`, `functools`, `statistics`, `decimal`, `random`, `string`, `textwrap`, `hashlib`, `base64`, `urllib.parse`). Rejection happens at AST parse time, before execution. Output capped at 4000 chars. Subprocess timeout at 30s.

Note: `network_mode: none` was in the original plan for the code runner but was dropped — it conflicts with Docker port binding. The import allowlist alone is sufficient since `socket`, `os`, `subprocess`, `urllib.request`, and `http.client` are all blocked at the import scan stage.

**UFW rules:** Each port is open only to the PC's Tailscale IP. The services are not publicly reachable.

---

## Tools (50 total)

### Web

| Tool | Description |
|------|-------------|
| `web_search` | DuckDuckGo search, direct snippets |
| `web_fetch` | Fetches and extracts text from a URL |
| `searxng_search` | Self-hosted meta-search (preferred over web_search) |
| `playwright_scrape` | Headless browser for JS-rendered pages |

### Research

| Tool | Description |
|------|-------------|
| `wikipedia_search` | Wikipedia REST summary API |
| `hn_search` | Hacker News Algolia — points, comments |
| `reddit_search` | Reddit public JSON API, no auth |
| `rss_fetch` | feedparser wrapper with entry summaries |
| `wayback_fetch` | Wayback Machine historical snapshots |
| `google_trends` | Trend direction + peak month via pytrends |
| `github_trending` | Scrapes github.com/trending |
| `github_search` | GitHub public search API — repos, code, issues |
| `arxiv_search` | arXiv Atom feed, academic paper search |
| `youtube_transcript` | youtube-transcript-api, no key required |
| `whois_lookup` | Domain registrar, dates, registrant |
| `opencorporates_search` | Company registration lookup |
| `url_safety_check` | Heuristic safety check on URLs |

### Memory

| Tool | Description |
|------|-------------|
| `knowledge_add` | Add document to ChromaDB knowledge collection |
| `knowledge_search` | Explicit semantic search of knowledge collection |
| `memory_note` | Save a note to episodic memory |

### Files

| Tool | Description |
|------|-------------|
| `file_read` | Read file from workspace/ (max 4000 chars) |
| `file_write` | Write file to workspace/ |
| `file_list` | List files under workspace/ subtree |
| `pdf_extract` | Extract text from workspace/ PDF (pypdf) |

### Documents

| Tool | Description |
|------|-------------|
| `draft_pptx` | PowerPoint via python-pptx |
| `draft_docx` | Word document via python-docx |
| `draft_xlsx` | Excel via openpyxl, auto-filter + frozen header |
| `render_diagram` | Mermaid (mmdc) or Graphviz → PNG/SVG |
| `render_template` | Jinja2 template renderer |
| `generate_qr` | QR code PNG via qrcode + Pillow |
| `financial_calc` | projection, break-even, TAM, ROI via pandas/numpy |

### Finance & Data

| Tool | Description |
|------|-------------|
| `stock_price` | Yahoo Finance (no key) |
| `crypto_price` | CoinGecko public API (no key) |
| `exchange_rate` | api.frankfurter.app (no key) |
| `data_analyze` | pandas describe + value_counts on workspace CSV/JSON |

### Code Execution

| Tool | Description |
|------|-------------|
| `code_execute` | Python sandbox on Xeon (AST-scanned, no network) |

### Services / Integrations

| Tool | Description |
|------|-------------|
| `n8n_trigger` | Fire n8n webhook workflow |
| `docuseal_send` | Send DocuSeal e-signature request |
| `comfyui_generate` | Image generation via ComfyUI |
| `stripe_op` | Stripe: payment links, revenue check |
| `git_op` | Gitea REST API — list/read/write/log |
| `http_request` | Generic GET/POST (RFC1918 blocked) |
| `email_send` | SMTP send via Xeon email service |
| `email_read` | IMAP read via Xeon email service |

### Agent Management

| Tool | Description |
|------|-------------|
| `goal_manager` | CRUD goals persisted to workspace/goals.json |
| `task_manager` | Track tasks persisted to workspace/tasks.json |
| `telegram_notify` | Proactive Telegram message to owner |

### Infrastructure

| Tool | Description |
|------|-------------|
| `system_health` | psutil on PC + /health pings on all Xeon services |
| `docker_restart` | Restart allowlisted PC Docker services |
| `shell_run` | Read-only shell commands (metachar guard + allowlist) |

---

## Key Engineering Decisions

### Sync over async for the tool layer

v2's tool layer was fully async — `async with httpx.AsyncClient()`, `await` everywhere, proper asyncio integration. This made sense in v2 because the entire runtime was asyncio. v3's `process_turn()` is a sync function called via `run_in_executor()` from the Telegram handler. Making tools async while brain is sync would have required nested event loops or thread pool workarounds. The simpler path: everything in the tool layer is sync `httpx.get/post`. The Telegram handler's event loop stays clean. No asyncio in any tool file.

### RAG injection at prompt-build time, not tool call time

v2's knowledge base was accessed by explicit tool call (`search_knowledge_base`, `kb_multi_query`). The model had to decide to search and formulate the right query. v3 injects relevant context automatically in `build_system_prompt()` before the model sees the message — it's always working with matched context without needing to ask for it. The model still has `knowledge_search` available for explicit lookup, but the default case is zero-friction.

### Episode collection separate from knowledge collection

Early versions used a single ChromaDB collection for everything. The problem: episodic memory (short conversational fragments) polluted knowledge search results and vice versa. A query like "what did we discuss about the pricing model?" would surface both the actual pricing document and half a dozen conversation snippets in arbitrary order. Splitting into two collections with separate search paths — knowledge for facts, episodes for conversational history — gave much cleaner results in both directions.

### System prompt includes live tool list

The model would occasionally claim capabilities it didn't have (calendar integration was the concrete case). The tool schemas passed in the `tools` API parameter define what the model *can call*, but they don't prevent it from describing tools in prose. Fix: `_build_tool_list()` in `prompt.py` reads the live `_TOOLS` dict at prompt-build time and injects the exact list into the system prompt. The list can't drift from the actual registry.

### `http_request` blocks RFC1918 in Python, not at network layer

The generic HTTP tool resolves the hostname to an IP using `socket.getaddrinfo()` before sending the request, then checks it against `ipaddress.ip_address().is_private`. This happens in process, before `httpx` opens a connection — no network-layer configuration required. Covers localhost (127.x), link-local (169.254.x), and all RFC1918 ranges. The check runs even on redirects because the tool doesn't follow redirects automatically.

### Per-chat asyncio queue in the Telegram handler

The Telegram handler creates one `asyncio.Queue` per chat ID and one persistent consumer coroutine per queue. Messages queue up and are processed serially per chat. This prevents interleaved responses when the user sends multiple messages before the first reply completes — a real edge case when `process_turn()` takes 15+ seconds on a complex multi-tool chain.

### History strips tool messages before storage

Tool call/result message pairs can be several kilobytes each (especially Playwright responses, Wikipedia articles). Storing them would mean every future turn prefills the context window with stale tool exchange data. `store/history.py` filters to `role: user` and `role: assistant` only before writing to disk. The model loses tool call detail between sessions but gains a much more efficient context window.

### Memory client is fully non-fatal

Every method in `memory/client.py` wraps its HTTP call in a broad `except Exception: return []`. A Xeon outage, a ChromaDB crash, a slow network — none of these should take the agent down. The consequence is a less contextual response, not a failed request. The same pattern applies to episode recording: it's fire-and-forget via `run_in_executor()`. If it fails, the conversation continues and the exchange just isn't stored.

---

## Issues Navigated

### network_mode: none breaks port binding

The code runner sandbox plan called for `network_mode: none` in its `docker-compose.yml` to completely isolate network access. This is correct in principle but Docker doesn't allow binding host ports when `network_mode: none` is set — the container can't be reached from outside. The fix was to drop `network_mode: none` and rely entirely on the AST import scan to block network-capable modules. `socket`, `os`, `subprocess`, `urllib.request`, `http.client`, and `ftplib` are all in the block list. The network is accessible at the OS level but unreachable from inside the sandbox.

### Model hallucinating tools it doesn't have

After adding 45 new tools in Phase 4, the model gave a status summary that included "Google Calendar" as an available integration. It wasn't. The model was drawing on training data about common assistant capabilities rather than its actual tool schemas. The tool `tools` API parameter controls what can be *called*, not what can be *described in prose*. Fixed by injecting a live tool list into the system prompt from the registry, with an explicit instruction not to claim unlisted capabilities.

### SSH exit 255 masking successful operations

Several `nohup ... &` SSH commands returned exit code 255. This is normal: when a backgrounded process detaches, SSH closes the connection with a non-zero exit. The process had already started successfully. The confusion came from checking `$?` after SSH — the exit code was SSH's, not the process's. Verification is done separately: tail the log file, check the PID with `pgrep`, or hit the service's `/health` endpoint.

### Async → sync conversion for all v2 tools

All tools ported from v2 were originally `async def` with `async with httpx.AsyncClient()`. Calling these from a sync `process_turn()` isn't possible without `asyncio.run()`, which throws if a loop is already running (it is — the Telegram handler runs in one). Every tool was converted to sync: `httpx.get()`, `httpx.post()`, `httpx.Client()` context managers. No other changes were needed — the logic is identical.

### Episode recording inside the async handler

`record_episode()` is a sync function that makes an HTTP call. Calling it directly from the async Telegram handler would block the event loop. Running it with `await asyncio.to_thread()` would work but adds complexity. The simplest fix was `loop.run_in_executor(None, record_episode, ...)` — same pattern as `process_turn()`. Non-blocking, non-fatal, and consistent with the existing approach.

---

## Project Structure

```
jarvis-v3/
  brain.py              # process_turn() — 120 lines, sync, stateless
  prompt.py             # build_system_prompt() — SOUL + tool guidance + RAG + episodes
  config.py             # All env vars. Loaded once at startup.
  main.py               # Entry point — run_bot()
  SOUL.md               # Agent identity, mission, communication style (live-editable)
  requirements.txt      # All pip dependencies

  interfaces/
    telegram.py         # Owner-only bot, per-chat queue, run_in_executor wrapping

  memory/
    client.py           # Non-fatal HTTP client for Xeon memory service
    episodes.py         # record_episode() — called after every exchange

  store/
    history.py          # Per-chat history, tool-message stripping, 40-message cap

  tools/
    web.py              # web_search (DuckDuckGo) + web_fetch (httpx)
    memory_tools.py     # knowledge_add, knowledge_search, memory_note
    research.py         # 13 research tools — wikipedia, arxiv, hn, reddit, github, ...
    services.py         # 7 service tools — searxng, playwright, n8n, stripe, comfyui, ...
    documents.py        # 8 document tools — pptx, docx, xlsx, qr, diagram, financial_calc, ...
    shell.py            # shell_run — metachar guard + allowlist
    git_tools.py        # git_op — Gitea REST API
    files.py            # file_read, file_write, file_list — workspace/ scoped
    finance.py          # stock_price, crypto_price, exchange_rate
    data.py             # data_analyze — pandas on workspace CSV/JSON
    goals.py            # goal_manager — CRUD on workspace/goals.json
    tasks.py            # task_manager — CRUD on workspace/tasks.json
    notify.py           # telegram_notify — proactive owner message
    code_runner.py      # code_execute — POST to Xeon sandbox
    email_tools.py      # email_send, email_read — POST to Xeon email service
    infra.py            # system_health, docker_restart
    tools_registry.py   # Schemas + dispatch for all 50 tools

  workspace/            # Agent file output, history, goals, tasks (gitignored)

xeon-services/          # Docker services deployed to /opt/jarvis/services/ on Xeon
  memory/
    app/main.py         # ChromaDB + FastAPI — knowledge and episode collections
    app/Dockerfile
    docker-compose.yml  # Port 8083, /data volume
  code-runner/
    app/main.py         # Python sandbox — AST import scan, subprocess, output cap
    app/Dockerfile
    docker-compose.yml  # Port 8084
  email/
    app/main.py         # smtplib SMTP + imaplib IMAP4_SSL via FastAPI
    app/Dockerfile
    docker-compose.yml  # Port 8085, env vars for credentials
```

---

## Deployment

No Docker on the PC side. The agent runs in a Python venv.

```bash
# Sync source to PC — never sync .env
rsync -az --exclude='.env' ./jarvis-v3/ user@server:~/jarvis-v3/

# Install dependencies (first time or after requirements change)
ssh user@server "cd ~/jarvis-v3 && source .venv/bin/activate && pip install -r requirements.txt"

# Start
ssh user@server "cd ~/jarvis-v3 && source .venv/bin/activate && nohup python3 main.py >> bot.log 2>&1 &"
```

Xeon services deploy via rsync + docker compose:

```bash
# Copy service directory to Xeon (routed through PC)
rsync -az ./xeon-services/memory/ user@pc:/tmp/memory/
ssh user@pc "rsync -az /tmp/memory/ user@xeon:/opt/jarvis/services/memory/"

# Build and start on Xeon
ssh user@xeon "cd /opt/jarvis/services/memory && sudo docker compose up -d --build"
```

UFW on the Xeon allows each service port only from the PC's Tailscale IP.

---

## What v3 Taught

**The scaffolding was for the models, not for the problem.** v2's three-loop architecture, routing matrix, lean/full system prompt split, and Xeon context workarounds were all engineering solutions to model limitations. When the model gets capable enough, those solutions don't simplify — they become obstacles. Knowing when to delete infrastructure is harder than knowing when to build it.

**Sync is the right default.** The v2 async tool layer was correct for v2's runtime. Carrying it into v3 would have been cargo-culting. Defaulting to sync in a sync context and only reaching for async when there's a concrete reason is better engineering than "async is modern, do async."

**Two collections beat one.** Mixing episodic memory and factual knowledge in a single vector store is a false economy. The overhead of a second ChromaDB collection is negligible. The quality difference in retrieval — no conversational fragments polluting document search — is significant.

**Prompt-time injection beats tool-call lookup for ambient context.** Making the model ask for context it always needs is friction. Injecting it automatically at prompt-build time means the model starts every turn already oriented. The explicit `knowledge_search` tool still exists for deliberate lookups — but ambient context shouldn't require deliberate action.

**Non-fatal clients are the right default for optional services.** Memory augments responses — it doesn't make them possible. Letting a memory service outage crash the agent is the wrong tradeoff. Every external call the agent doesn't strictly need should be non-fatal by default.

---

## Status

Running 24/7. Telegram interface, semantic memory, 50 tools available. Interactive-only for now — no autonomous planning loop. The v2 planning loop may be reintroduced in a future phase once the tool layer is proven stable.
