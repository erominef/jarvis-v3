# tools/memory_tools.py — Memory tools exposed to the LLM.
#
# knowledge_add(content, title)  — add a document to the RAG knowledge base
# knowledge_search(query)        — semantic search over the knowledge base
# memory_note(content)           — save an explicit episodic note
#
# All delegate to the Xeon memory service via memory/client.py.
# Return structured dicts compatible with tools_registry dispatch.


def knowledge_add(content: str, title: str = "") -> dict:
    """Store a document or fact in the semantic knowledge base (ChromaDB)."""
    raise NotImplementedError


def knowledge_search(query: str) -> dict:
    """Explicit semantic search over the knowledge base. Returns top 3 results."""
    raise NotImplementedError


def memory_note(content: str) -> dict:
    """Save a short note to episodic memory with the current timestamp."""
    raise NotImplementedError
