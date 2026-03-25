# main.py — Memory API service for jarvis-v3.
#
# Runs on Xeon in Docker. Wraps ChromaDB with FastAPI.
# Embeddings: chromadb built-in ONNX (all-MiniLM-L6-v2, ~22MB, downloads on first start).
# No Ollama dependency.
#
# Collections:
#   knowledge — RAG static documents (chunked, 500 chars / 50 overlap)
#   episodes  — episodic memory (conversation summaries + explicit notes)
#
# Endpoints:
#   POST /knowledge/add    {text, title}     -> {success, ids}
#   POST /knowledge/search {query, n=3}      -> {results: [{text, title, score}]}
#   POST /episodes/add     {text, timestamp} -> {success, id}
#   POST /episodes/search  {query, n=5}      -> {results: [{text, timestamp, score}]}
#   GET  /health                             -> {status, knowledge_count, episode_count}

import uuid
from datetime import datetime, timezone

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="jarvis-memory")

_embed_fn = DefaultEmbeddingFunction()

# ChromaDB — persisted at /data (Docker volume)
_db = chromadb.PersistentClient(path="/data")
_knowledge = _db.get_or_create_collection("knowledge", embedding_function=_embed_fn)
_episodes = _db.get_or_create_collection("episodes", embedding_function=_embed_fn)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def _chunk(text: str) -> list[str]:
    if len(text) <= CHUNK_SIZE:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + CHUNK_SIZE])
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


# --- Request models ---

class AddKnowledgeRequest(BaseModel):
    text: str
    title: str = ""

class SearchRequest(BaseModel):
    query: str
    n: int = 3

class AddEpisodeRequest(BaseModel):
    text: str
    timestamp: str = ""


# --- Knowledge endpoints ---

@app.post("/knowledge/add")
def knowledge_add(req: AddKnowledgeRequest):
    try:
        chunks = _chunk(req.text)
        ids = []
        for i, chunk in enumerate(chunks):
            cid = str(uuid.uuid4())
            _knowledge.add(
                ids=[cid],
                documents=[chunk],
                metadatas=[{"title": req.title, "chunk_index": i}],
            )
            ids.append(cid)
        return {"success": True, "ids": ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/knowledge/search")
def knowledge_search(req: SearchRequest):
    try:
        count = _knowledge.count()
        if count == 0:
            return {"results": []}
        res = _knowledge.query(
            query_texts=[req.query],
            n_results=min(req.n, count),
            include=["documents", "metadatas", "distances"],
        )
        results = []
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            results.append({
                "text": doc,
                "title": meta.get("title", ""),
                "score": round(1 - dist, 3),
            })
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Episode endpoints ---

@app.post("/episodes/add")
def episodes_add(req: AddEpisodeRequest):
    try:
        ep_id = str(uuid.uuid4())
        ts = req.timestamp or datetime.now(timezone.utc).isoformat()
        _episodes.add(
            ids=[ep_id],
            documents=[req.text],
            metadatas=[{"timestamp": ts}],
        )
        return {"success": True, "id": ep_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/episodes/search")
def episodes_search(req: SearchRequest):
    try:
        count = _episodes.count()
        if count == 0:
            return {"results": []}
        res = _episodes.query(
            query_texts=[req.query],
            n_results=min(req.n, count),
            include=["documents", "metadatas", "distances"],
        )
        results = []
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            results.append({
                "text": doc,
                "timestamp": meta.get("timestamp", ""),
                "score": round(1 - dist, 3),
            })
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {
        "status": "ok",
        "knowledge_count": _knowledge.count(),
        "episode_count": _episodes.count(),
    }
