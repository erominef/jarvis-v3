# tools/memory_tools.py — Memory tools exposed to the LLM.
#
# knowledge_add(content, title)  — add a document to the RAG knowledge base
# knowledge_search(query)        — semantic search over the knowledge base
# memory_note(content)           — save an explicit episodic note
#
# All call the Xeon memory API via memory/client.py.
# Return structured dicts compatible with tools_registry dispatch.

from datetime import datetime, timezone
from memory import client


def knowledge_add(content: str, title: str = "") -> dict:
    result = client.add_knowledge(content, title=title)
    if result.get("success"):
        return {"success": True, "message": f"Stored '{title or 'document'}' in knowledge base."}
    return {"success": False, "error": "store_error"}


def knowledge_search(query: str) -> dict:
    results = client.search_knowledge(query, n=3)
    if not results:
        return {"success": False, "error": "no_results"}
    return {"success": True, "results": results}


def memory_note(content: str) -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    result = client.add_episode(content, timestamp=ts)
    if result.get("success"):
        return {"success": True, "message": "Note saved to memory."}
    return {"success": False, "error": "store_error"}
