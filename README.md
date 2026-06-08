<div align="center">

# VertexMind
### Agentic Enterprise Knowledge Assistant

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)](https://reactjs.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2-FF6B35?style=flat)](https://langchain-ai.github.io/langgraph)
[![Google Cloud](https://img.shields.io/badge/GCP-Vertex%20AI-4285F4?style=flat&logo=googlecloud&logoColor=white)](https://cloud.google.com/vertex-ai)
[![Groq](https://img.shields.io/badge/Groq-Llama%204-F55036?style=flat)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)

</div>

---

## Screenshots

| Chat Interface | Source Citations | PDF Upload |
|:-:|:-:|:-:|
| ![Chat](assets/chat.png) | ![Citations](assets/citations.png) | ![Upload](assets/upload.png) |

> Screenshots coming soon — will update once deployed.
> To run locally: `python main.py` (backend) + `npm run dev` (frontend), then drop screenshots into `assets/`.

---

## About the Project

I built VertexMind to understand how agentic AI systems actually work under the hood — not just calling an LLM API, but building a proper multi-node reasoning graph where the agent decides *how* to answer before it actually answers.

The core idea: instead of always searching the same source, the agent first classifies your question, picks the right tool (your documents, the web, or both), retrieves context, and then generates a grounded response — all while streaming tokens back to you in real time and keeping track of the conversation.

The hardest parts were getting the LangGraph routing to be truly document-agnostic (earlier it was hardcoded to specific filenames — rookie mistake), making streaming work cleanly with async FastAPI when most of LangChain's retrieval code is synchronous, and keeping GCP costs reasonable while still using Vertex AI Vector Search.

---

## How it works

```
┌──────────────────────────────────────────────────────────────────┐
│                         React Frontend                           │
│   Header  │  ChatWindow  │  MessageBubble  │  CitationList        │
│                    SSE Streaming (token-by-token)                │
└──────────────────────────┬───────────────────────────────────────┘
                           │  POST /chat/stream
                           │  POST /chat
                           │  POST /upload
┌──────────────────────────▼───────────────────────────────────────┐
│                       FastAPI Backend                            │
│                   app.py  ·  ingest_pipeline.py                  │
└──────────────────────────┬───────────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────────┐
│                    LangGraph Agent  (agent.py)                   │
│                                                                  │
│   START                                                          │
│     │                                                            │
│     ▼                                                            │
│  ┌──────────────┐                                                │
│  │ Orchestrator │  ← LLM decides route based on question type    │
│  └──────┬───────┘                                                │
│         │                                                        │
│    ┌────┴────┬──────────┬──────────┐                             │
│    ▼         ▼          ▼          ▼                             │
│ vectordb  websearch   both      direct                           │
│    │         │       ┌──┘          │                             │
│    ▼         │       │             ▼                             │
│ Vertex AI   │    VectorDB       Direct                          │
│  Vector     │    + Web            LLM                            │
│  Search     │    Search           │                              │
│    │        │       │             │                              │
│    └────────┴───────┴──────┬──────┘                              │
│                            ▼                                     │
│                       ┌─────────┐                                │
│                       │Generate │  ← Groq Llama 4 Scout          │
│                       └────┬────┘    + conversation history      │
│                            │                                     │
│                           END                                    │
└──────────────────────────────────────────────────────────────────┘
                           │
          ┌────────────────┴─────────────────────┐
          ▼                                      ▼
   Vertex AI Vector Search              Tavily Web Search
   (GCP — semantic retrieval)           (real-time internet)
```

The routing logic is what makes this interesting. The orchestrator doesn't use keyword matching — it sends the question to Llama 4 and asks it to classify the intent. "What happened in chapter 3?" goes to vectordb. "What's the latest AI news?" goes to websearch. "How does this compare to current research?" hits both. Simple questions like greetings skip retrieval entirely. And if it's uncertain, it defaults to your documents.

---

## What's built in

- **Streaming responses** — tokens come back one by one over SSE, answer builds live in the UI
- **Source citations** — every document answer shows which file, which page, and the actual chunk used
- **Conversation memory** — last 6 exchanges are passed as context so follow-ups work naturally
- **PDF upload** — drag a PDF onto the chat window, it indexes in the background in ~30 seconds
- **Hybrid search** — can query your documents and the live web at the same time if needed
- **Semantic retrieval** — using Vertex AI Vector Search with `text-embedding-005` (768-dim vectors)

---

## Tech Stack

**Backend**

| | |
|---|---|
| Agent framework | LangGraph 1.2 — StateGraph with conditional edges |
| LLM | Groq — `meta-llama/llama-4-scout-17b-16e-instruct` |
| Embeddings | Vertex AI `text-embedding-005` |
| Vector DB | GCP Vertex AI Vector Search (Matching Engine) |
| Web search | Tavily Search API |
| API | FastAPI with SSE, background tasks, file upload |
| PDF parsing | LangChain PyPDFLoader + RecursiveCharacterTextSplitter |

**Frontend**

| | |
|---|---|
| Framework | React 18 + Vite |
| Streaming | Fetch ReadableStream for SSE, Axios for REST |
| Styling | Vanilla CSS — wrote the whole design system by hand |

---

## Project Structure

```
VertexMind/
│
├── backend/
│   ├── agent.py              # the LangGraph graph — all nodes and routing logic
│   ├── app.py                # FastAPI — /chat, /chat/stream, /upload
│   ├── ingest.py             # one-time index setup (run this first)
│   ├── ingest_pipeline.py    # ingestion function called by the upload endpoint
│   ├── main.py               # server entry point, auto-finds the right venv
│   ├── requirements.txt
│   └── vector_store_ids.txt  # generated after first ingest run
│
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── components/
│       │   ├── Header.jsx
│       │   ├── ChatWindow.jsx
│       │   ├── MessageBubble.jsx    # streaming cursor, route badge
│       │   ├── ChatInput.jsx
│       │   ├── CitationList.jsx     # source cards per answer
│       │   └── PdfUpload.jsx        # drag-drop overlay
│       ├── services/api.js          # streamMessage, uploadPdf
│       └── styles/app.css
│
├── main.py                   # root launcher
└── README.md
```

---

## Running it locally

You'll need Python 3.11+, Node.js 18+, a GCP project with Vertex AI enabled, and API keys for Groq and Tavily.

**1. Clone**
```bash
git clone https://github.com/YOUR_USERNAME/vertexmind.git
cd vertexmind
```

**2. Backend env vars** — create `backend/.env`:
```env
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
GCS_BUCKET=your-bucket-name
INDEX_DISPLAY_NAME=vertexmind-index
ENDPOINT_DISPLAY_NAME=vertexmind-endpoint
GROQ_API_KEY=gsk_...
TAVILY_API_KEY=tvly-...
```

**3. GCP auth**
```bash
gcloud auth application-default login
```

**4. Backend dependencies**
```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

**5. First-time indexing** — edit `backend/ingest.py`, set your PDF paths, then run:
```bash
python ingest.py
```
This takes ~30 minutes because it creates and deploys a Vertex AI index. Only needs to happen once — after that, new PDFs go in through the UI in ~30 seconds.

**6. Start backend**
```bash
python main.py
# http://localhost:8000
```

**7. Start frontend**
```bash
cd frontend
npm install
npm run dev
# http://localhost:5173
```

---

## API

**POST /chat** — standard request/response

```json
// request
{ "question": "What happens in chapter 3?", "history": [] }

// response
{
  "route": "vectordb",
  "answer": "In chapter 3...",
  "citations": [{ "source": "book.pdf", "page": 42, "snippet": "..." }]
}
```

**POST /chat/stream** — SSE, same request body, streams events:

```
data: {"type": "route",     "route": "vectordb"}
data: {"type": "token",     "content": "In "}
data: {"type": "token",     "content": "chapter "}
data: {"type": "citations", "citations": [...]}
data: {"type": "done"}
```

**POST /upload** — multipart PDF, runs ingestion in background:

```json
{ "status": "processing", "filename": "report.pdf" }
```

---

## What I learned building this

A few things that weren't obvious until I hit them:

- LangGraph's `StateGraph` feels simple until you need conditional edges that branch on LLM output — getting the routing to be truly dynamic took a few iterations
- FastAPI's `StreamingResponse` with SSE works great, but most of LangChain's retrieval is synchronous. Had to wrap everything in `asyncio.to_thread` to avoid blocking the event loop
- Vertex AI Vector Search has a ~30 minute cold start for index creation, but once deployed it's fast. The trick is saving the index and endpoint IDs so you're not recreating it on every run
- Conversation memory over a stateless REST API means the frontend has to own the history — the backend just receives the last N messages and injects them into the prompt

---

## Built with

LangGraph · Groq · Vertex AI · FastAPI · React

---

**Buddha Bhavana**
[GitHub](https://github.com/YOUR_GITHUB) · [LinkedIn](https://linkedin.com/in/YOUR_LINKEDIN) · tcwneat@aicte-india.org
