# tools/mcp.py — Montegallo knowledge base via MCP (SSE + JSON-RPC 2.0).
#
# Sync port of v2 mcp.py. All functions return strings and never raise.
#
# Protocol (one fresh session per call to avoid idle timeout):
#   1. GET /sse (Bearer token) → SSE stream
#   2. Parse "endpoint" event → session path (e.g. /messages/?session_id=xyz)
#   3. POST initialize JSON-RPC to session path
#   4. Receive initialize response on SSE stream
#   5. POST notifications/initialized
#   6. POST tools/call { name: "<tool>", arguments: { ... } }
#   7. Receive result on SSE stream → return text
#
# Available tools:
#   search_kb          — basic semantic search
#   multi_query        — run several queries at once (queries: newline-separated string)
#   search_with_context — returns matched chunks + surrounding context
#   suggest_queries    — suggest related query expansions
#   list_sources       — list all KB source documents
#
# 30s timeout via httpx.Timeout. Graceful degradation — never raises.

import json
import uuid
from typing import Generator

import httpx

from config import MCP_MONTEGALLO_URL, MCP_MONTEGALLO_TOKEN

_TIMEOUT   = httpx.Timeout(30.0)
_TOP_K     = 5
_PROTO_VER = "2024-11-05"


def search_knowledge_base(query: str) -> str:
    """Search a curated document collection. Treat results like web results — one source among many."""
    return _mcp_call("search_kb", {"query": query, "top_k": _TOP_K})


def kb_multi_query(queries: list[str], top_k: int = 5) -> str:
    """
    Run multiple queries at once against the KB — broader coverage than a single search.
    queries: list of query strings. Treat results like web results, not authoritative truth.
    """
    queries_str = "\n".join(q.strip() for q in queries if q.strip())
    return _mcp_call("multi_query", {"queries": queries_str, "top_k": top_k})


def kb_search_with_context(query: str, top_k: int = 3, context_chunks: int = 3) -> str:
    """
    Search and return matched chunks with surrounding context.
    Treat results like web results. Better for tasks needing more passage context.
    """
    return _mcp_call("search_with_context", {
        "query": query, "top_k": top_k, "context_chunks": context_chunks,
    })


def kb_suggest_queries(partial_query: str, count: int = 5) -> str:
    """Suggest related query expansions for a topic. Use to discover angles not yet searched."""
    return _mcp_call("suggest_queries", {"partial_query": partial_query, "count": count})


def kb_list_sources() -> str:
    """List all source documents indexed in the knowledge base."""
    return _mcp_call("list_sources", {})


# ── Internal ──────────────────────────────────────────────────────────────────

def _mcp_call(tool_name: str, arguments: dict) -> str:
    if not MCP_MONTEGALLO_TOKEN:
        return "[Knowledge base unavailable: MCP_MONTEGALLO_TOKEN not configured]"
    try:
        return _run_tool(tool_name, arguments)
    except Exception as e:
        return f"[KB {tool_name} failed: {e}]"


def _run_tool(tool_name: str, arguments: dict) -> str:
    base = MCP_MONTEGALLO_URL.rstrip("/").removesuffix("/sse")
    sse_url = f"{base}/sse"
    auth = f"Bearer {MCP_MONTEGALLO_TOKEN}"
    init_id = str(uuid.uuid4())
    call_id = str(uuid.uuid4())

    with httpx.Client(timeout=_TIMEOUT) as client:
        with client.stream(
            "GET", sse_url,
            headers={"Authorization": auth, "Accept": "text/event-stream"},
        ) as resp:
            resp.raise_for_status()
            reader = resp.iter_bytes()

            session_path = _read_until_endpoint(reader)
            post_url = f"{base}{session_path}"

            def post(body: dict) -> None:
                r = client.post(
                    post_url, json=body,
                    headers={"Content-Type": "application/json", "Authorization": auth},
                )
                r.raise_for_status()

            post({
                "jsonrpc": "2.0", "id": init_id, "method": "initialize",
                "params": {
                    "protocolVersion": _PROTO_VER,
                    "capabilities": {},
                    "clientInfo": {"name": "jarvis", "version": "3.0"},
                },
            })
            _read_until_id(reader, init_id)
            post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
            post({
                "jsonrpc": "2.0", "id": call_id, "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            })
            return _read_until_id(reader, call_id)


def _parse_sse(reader) -> Generator[tuple[str, str], None, None]:
    """Yield (event_type, data) tuples from a sync SSE byte stream."""
    buf = b""
    event_type = "message"
    data_lines: list[str] = []

    for chunk in reader:
        buf += chunk
        while b"\n" in buf:
            line_bytes, buf = buf.split(b"\n", 1)
            line = line_bytes.decode("utf-8", errors="replace").rstrip("\r")

            if line == "":
                if data_lines:
                    yield event_type, "\n".join(data_lines)
                event_type = "message"
                data_lines = []
            elif line.startswith("event:"):
                event_type = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data_lines.append(line[len("data:"):].strip())


def _read_until_endpoint(reader) -> str:
    """Read SSE stream until the 'endpoint' event. Returns session path."""
    for evt, data in _parse_sse(reader):
        if evt == "endpoint":
            return data.strip()
    raise RuntimeError("SSE stream ended without 'endpoint' event")


def _read_until_id(reader, msg_id: str) -> str:
    """Read SSE stream until a JSON-RPC response matching msg_id. Returns text content."""
    for evt, data in _parse_sse(reader):
        if evt not in ("message", "data"):
            continue
        try:
            msg = json.loads(data)
        except json.JSONDecodeError:
            continue

        if msg.get("id") != msg_id:
            continue

        if "error" in msg:
            raise RuntimeError(f"MCP error: {msg['error']}")

        result = msg.get("result", {})
        content = result.get("content") if isinstance(result, dict) else None
        if isinstance(content, list) and content:
            text = content[0].get("text")
            if text:
                return str(text)
        return json.dumps(result)

    raise RuntimeError("SSE stream ended before receiving expected response")
