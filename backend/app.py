# =============================================================
# app.py  —  VertexMind FastAPI server
# =============================================================
# Existing /chat endpoint: PRESERVED (backward-compatible)
# New endpoints added:
#   POST /chat/stream  — SSE token-by-token streaming
#   POST /upload       — drag-drop PDF ingestion
# =============================================================

import warnings
from langchain_core._api.deprecation import LangChainDeprecationWarning
warnings.filterwarnings("ignore", category=LangChainDeprecationWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

import os
import json
import asyncio
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent import (
    build_rag_graph,
    GraphState,
    orchestrator,
    retrieve_from_vectordb,
    search_web,
    extract_citations,
    stream_final_answer,
)

# ── App ───────────────────────────────────────────────────────
app = FastAPI(
    title="VertexMind – Agentic Enterprise Knowledge Assistant",
    description="LangGraph + Groq + Vertex AI Vector Search",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://agentic-rag-495906.web.app",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Build graph ONCE at startup (initialises all singletons)
rag_app = build_rag_graph()

# ── Request / Response models ─────────────────────────────────

class QueryRequest(BaseModel):
    question: str
    history: list[dict] = []      # optional — backward-compatible


class QueryResponse(BaseModel):
    question: str
    route: str
    answer: str
    citations: list[dict] = []    # new field — empty for websearch/direct


class ChatStreamRequest(BaseModel):
    question: str
    history: list[dict] = []


# ── Health ────────────────────────────────────────────────────

@app.get("/")
def health_check():
    return {"status": "ok", "service": "VertexMind Agentic RAG v2"}


# ── /chat  (original endpoint — fully preserved + enhanced) ───

@app.post("/chat", response_model=QueryResponse)
def chat(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    initial_state: GraphState = {
        "question":    request.question,
        "route":       "",
        "vector_docs": [],
        "web_results": [],
        "final_answer": "",
        "history":     request.history,
    }

    result    = rag_app.invoke(initial_state)
    citations = extract_citations(result.get("vector_docs", []))

    return QueryResponse(
        question=request.question,
        route=result["route"],
        answer=result["final_answer"],
        citations=citations,
    )


# ── /chat/stream  (SSE — token-by-token streaming) ────────────

@app.post("/chat/stream")
async def chat_stream(request: ChatStreamRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    async def event_stream():
        try:
            state: GraphState = {
                "question":    request.question,
                "route":       "",
                "vector_docs": [],
                "web_results": [],
                "final_answer": "",
                "history":     request.history,
            }

            # Step 1 — route (blocking → thread)
            state = await asyncio.to_thread(orchestrator, state)
            route = state["route"]
            yield f"data: {json.dumps({'type': 'route', 'route': route})}\n\n"

            # Step 2 — retrieve
            if route in ("vectordb", "both"):
                state = await asyncio.to_thread(retrieve_from_vectordb, state)
            if route in ("websearch", "both"):
                state = await asyncio.to_thread(search_web, state)

            # Step 3 — stream answer tokens
            async for token in stream_final_answer(
                request.question, state, request.history
            ):
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            # Step 4 — citations
            citations = extract_citations(state.get("vector_docs", []))
            if citations:
                yield f"data: {json.dumps({'type': 'citations', 'citations': citations})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as exc:
            print(f"[stream error] {exc}")
            yield f"data: {json.dumps({'type': 'error', 'message': 'An error occurred. Please try again.'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "Connection":       "keep-alive",
            "X-Accel-Buffering":"no",
        },
    )


# ── /upload  (PDF drag-drop ingestion) ───────────────────────

def _run_ingestion(file_path: str, filename: str) -> None:
    """Background task: add a new PDF to the existing vector store."""
    try:
        from ingest_pipeline import ingest_pdf
        count = ingest_pdf(file_path)
        print(f"[upload] Ingested {count} chunks from '{filename}'")
    except Exception as exc:
        print(f"[upload] Ingestion failed for '{filename}': {exc}")


@app.post("/upload")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    ids_file = Path(__file__).parent / "vector_store_ids.txt"
    if not ids_file.exists():
        raise HTTPException(
            status_code=400,
            detail=(
                "No vector index found. "
                "Run ingest.py first to create the index, "
                "then upload additional PDFs here."
            ),
        )

    upload_dir = Path(__file__).parent / "uploads"
    upload_dir.mkdir(exist_ok=True)

    safe_name = file.filename.replace(" ", "_")
    file_path = upload_dir / safe_name
    file_path.write_bytes(await file.read())

    background_tasks.add_task(_run_ingestion, str(file_path), file.filename)

    return {
        "status":   "processing",
        "filename": file.filename,
        "message":  (
            f"'{file.filename}' received and queued for ingestion. "
            "It will be searchable in ~30 seconds."
        ),
    }
