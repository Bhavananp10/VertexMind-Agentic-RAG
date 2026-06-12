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

from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile, Request
from fastapi.responses import StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from google.cloud import speech as gcp_speech
from google.cloud import texttospeech

# ── STT / TTS singletons (lazy) ───────────────────────────────
_stt_client = None
_tts_client = None

def _get_stt():
    global _stt_client
    if _stt_client is None:
        _stt_client = gcp_speech.SpeechClient()
    return _stt_client

def _get_tts():
    global _tts_client
    if _tts_client is None:
        _tts_client = texttospeech.TextToSpeechClient()
    return _tts_client

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


# ── /dialogflow-webhook  (Dialogflow CX fulfillment) ─────────

@app.post("/dialogflow-webhook")
async def dialogflow_webhook(request: Request):
    """
    Dialogflow CX calls this endpoint when it needs a dynamic answer.
    We extract the user's question, run it through the LangGraph RAG
    pipeline, and return the answer in the format Dialogflow expects.
    """
    body = await request.json()

    # Dialogflow CX sends the user's text in the "text" field
    user_text = body.get("text", "").strip()

    # Fallback: some CX versions nest it differently
    if not user_text:
        user_text = (
            body.get("transcript", "")
            or body.get("fulfillmentInfo", {}).get("tag", "")
        ).strip()

    if not user_text:
        return {
            "fulfillmentResponse": {
                "messages": [{"text": {"text": ["Sorry, I didn't receive your question. Please try again."]}}]
            }
        }

    print(f"[dialogflow-webhook] Question: {user_text}")

    # Run through the existing LangGraph RAG pipeline
    state: GraphState = {
        "question":     user_text,
        "route":        "",
        "vector_docs":  [],
        "web_results":  [],
        "final_answer": "",
        "history":      [],
    }

    result    = await asyncio.to_thread(rag_app.invoke, state)
    answer    = result["final_answer"]
    citations = extract_citations(result.get("vector_docs", []))
    route     = result.get("route", "")

    print(f"[dialogflow-webhook] Route: {route} | Answer: {answer[:80]}...")

    # Build citation text if docs were found
    citation_text = ""
    if citations:
        sources = ", ".join(
            f"{c['source']} (p.{c['page']})" for c in citations[:2]
        )
        citation_text = f"\n\nSources: {sources}"

    # Return in Dialogflow CX webhook response format
    return {
        "fulfillmentResponse": {
            "messages": [
                {
                    "text": {
                        "text": [answer + citation_text]
                    }
                }
            ]
        },
        "sessionInfo": {
            "parameters": {
                "last_route":    route,
                "has_citations": len(citations) > 0,
            }
        }
    }


# ── /stt  (Speech-to-Text via Google Cloud) ──────────────────

@app.post("/stt")
async def speech_to_text(audio: UploadFile = File(...)):
    audio_bytes = await audio.read()
    print(f"[stt] Received audio: {len(audio_bytes)} bytes, type: {audio.content_type}")

    try:
        client = _get_stt()
        recognition_audio = gcp_speech.RecognitionAudio(content=audio_bytes)
        config = gcp_speech.RecognitionConfig(
            encoding=gcp_speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=48000,
            language_code="en-US",
            enable_automatic_punctuation=True,
        )
        response = await asyncio.to_thread(
            client.recognize, config=config, audio=recognition_audio
        )
        transcript = (
            response.results[0].alternatives[0].transcript
            if response.results else ""
        )
        print(f"[stt] Transcript: '{transcript}'")
        return {"transcript": transcript}

    except Exception as exc:
        print(f"[stt] ERROR: {exc}")
        raise HTTPException(status_code=500, detail=f"STT failed: {str(exc)}")


# ── /tts  (Text-to-Speech via Google Cloud) ──────────────────

class TTSRequest(BaseModel):
    text: str

@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    """
    Receives answer text from the frontend.
    Converts to speech using Google Cloud Neural2 voice.
    Returns MP3 audio bytes directly — browser plays it.
    """
    client = _get_tts()

    synthesis_input = texttospeech.SynthesisInput(
        text=request.text[:800]          # cap length to avoid long audio
    )
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Neural2-J",          # professional male neural voice
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.0,
    )

    try:
        tts_response = await asyncio.to_thread(
            client.synthesize_speech,
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )
        return Response(content=tts_response.audio_content, media_type="audio/mpeg")

    except Exception as exc:
        print(f"[tts] ERROR: {exc}")
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(exc)}")


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
