# brain.py — Core reasoning loop.
#
# process_turn(user_input, history=None) → str
#
# Calls the Ollama /api/chat endpoint directly via httpx.
#
# Flow:
#   1. Build system prompt with semantic memory context (RAG + episodes).
#   2. Inject conversation history for multi-turn context.
#   3. Send user message to LLM with tool schemas.
#   4. If response contains tool_calls: execute each, append results, repeat.
#   5. If no tool_calls: return message content.
#
# Loop capped at MAX_TOOL_ROUNDS to prevent runaway chains.
#
# Retry guard:
#   Tracks per-tool failure counts. If the same tool returns success=false
#   twice, the loop stops immediately and returns a graceful error message.

import json
import httpx

from config import OLLAMA_API_KEY, OLLAMA_BASE_URL, MODEL, MAX_TOKENS, MAX_TOOL_ROUNDS
from prompt import build_system_prompt
from tools.tools_registry import get_tool_schemas, dispatch_tool

_CHAT_URL = f"{OLLAMA_BASE_URL.rstrip('/')}/chat"
_HEADERS = {
    "Authorization": f"Bearer {OLLAMA_API_KEY}",
    "Content-Type": "application/json",
}

_FAILURE_MESSAGES = {
    "rate_limited": "The search service is currently rate-limited. Please try again in a moment.",
    "no_results": "No results were found for that search. Try rephrasing the query.",
    "js_rendered_page": "That page requires JavaScript to render and cannot be read directly. Try a raw URL (e.g. raw.githubusercontent.com) or a plain HTML alternative.",
    "fetch_error": "The page could not be fetched. It may be unavailable or require authentication.",
    "no_content": "The page was fetched but contained no readable content.",
}


def _chat(messages: list[dict]) -> dict:
    payload = {
        "model": MODEL,
        "messages": messages,
        "tools": get_tool_schemas(),
        "stream": False,
        "options": {"num_predict": MAX_TOKENS},
    }
    resp = httpx.post(_CHAT_URL, headers=_HEADERS, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()


def _is_tool_failure(result_str: str) -> str | None:
    """Parse a tool result string. Returns the error value if success=false, else None."""
    try:
        parsed = json.loads(result_str)
        if isinstance(parsed, dict) and not parsed.get("success", True):
            return parsed.get("error", "unknown")
    except (json.JSONDecodeError, Exception):
        pass
    return None


def process_turn(user_input: str, history: list[dict] | None = None) -> str:
    messages = [{"role": "system", "content": build_system_prompt(user_input)}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_input})

    fail_counts: dict[str, int] = {}

    for _ in range(MAX_TOOL_ROUNDS):
        try:
            data = _chat(messages)
        except Exception as e:
            return f"LLM error: {e}"

        message = data.get("message", {})
        tool_calls = message.get("tool_calls")

        if not tool_calls:
            return message.get("content", "(no response)")

        # Append assistant turn with tool calls
        messages.append(message)

        # Execute each tool call and append results
        for call in tool_calls:
            fn = call.get("function", {})
            name = fn.get("name", "")
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}

            result = dispatch_tool(name, args)

            # Check for structured failure
            error = _is_tool_failure(result)
            if error is not None:
                fail_counts[name] = fail_counts.get(name, 0) + 1
                if fail_counts[name] >= 2:
                    msg = _FAILURE_MESSAGES.get(error, f"Tool '{name}' failed: {error}.")
                    return f"I wasn't able to complete that request. {msg}"

            messages.append({
                "role": "tool",
                "content": result,
            })

    return "(max tool rounds reached)"
