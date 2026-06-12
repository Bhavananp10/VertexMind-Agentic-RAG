<div align="center">

# VertexMind
### Regulatory Compliance Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)](https://reactjs.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2-FF6B35?style=flat)](https://langchain-ai.github.io/langgraph)
[![Google Cloud](https://img.shields.io/badge/GCP-Vertex%20AI-4285F4?style=flat&logo=googlecloud&logoColor=white)](https://cloud.google.com/vertex-ai)
[![Dialogflow CX](https://img.shields.io/badge/Dialogflow-CX-FF9800?style=flat&logo=dialogflow&logoColor=white)](https://cloud.google.com/dialogflow)
[![LangSmith](https://img.shields.io/badge/LangSmith-Observability-1C3C3C?style=flat)](https://smith.langchain.com)
[![Groq](https://img.shields.io/badge/Groq-Llama%204-F55036?style=flat)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)

**Voice and chat-enabled AI agent for enterprise regulatory compliance — built on Google Cloud**

</div>

---

## Problem Statement

Compliance officers, legal teams, and auditors in regulated industries — banking, insurance, pharmaceuticals — spend **60–70% of their time manually searching** through hundreds of policy documents, RBI/GDPR/SEBI guidelines, and internal manuals.

The consequences are real:
- Compliance checks take **days instead of minutes**
- Human error causes missed clauses — leading to **regulatory fines**
- **No audit trail** of what was searched or who accessed what
- Regulations change weekly — teams have **no way to stay current**

---

## Solution

VertexMind is a voice and chat-enabled compliance intelligence platform. Compliance professionals ask questions in plain English — via web chat, or voice through a phone channel — and get answers sourced from internal policy documents and live regulatory updates, with every single query logged as a legally-defensible audit trail.

```
Compliance Officer: "What is our data retention policy under GDPR Article 17?"

VertexMind:  [searches internal policy PDFs]
             [fetches latest regulatory updates from web]
             "Under GDPR Article 17, data must be erased within 30 days of
              a valid request. Your internal DPA-2024 policy (page 12) specifies
              the erasure workflow..."
             [sources cited: DPA-2024.pdf p.12, GDPR-guidelines.pdf p.4]
             [query logged to audit trail with timestamp and user context]
```

---

## Architecture

```
                    ┌──────────────────────────────────────────────────┐
                    │           Entry Channels                         │
                    │                                                  │
                    │  Web Chat (React)    Voice / Phone (CCAI)        │
                    │       │                      │                   │
                    └───────┼──────────────────────┼───────────────────┘
                            │                      │
                            ▼                      ▼
                    ┌──────────────────────────────────────────────────┐
                    │           Dialogflow CX Agent                    │
                    │                                                  │
                    │  Intent Detection  ·  Multi-turn Flow Mgmt       │
                    │  Entity Extraction  ·  Voice / Text Handling     │
                    │  Structured Investigation Flows                  │
                    └──────────────────┬───────────────────────────────┘
                                       │ Webhook  (POST /dialogflow-webhook)
                                       ▼
                    ┌──────────────────────────────────────────────────┐
                    │           FastAPI Backend  (app.py)              │
                    │                                                  │
                    │  /chat  ·  /chat/stream (SSE)  ·  /upload        │
                    │  /dialogflow-webhook  ·  /mcp  (MCP server)      │
                    └──────────────────┬───────────────────────────────┘
                                       │
                    ┌──────────────────▼───────────────────────────────┐
                    │           LangGraph Agent  (agent.py)            │
                    │                                                  │
                    │   START → Orchestrator → [route decision]        │
                    │                │                                 │
                    │    ┌───────────┼──────────┬────────────┐         │
                    │    ▼           ▼          ▼            ▼         │
                    │  vectordb  websearch    both         direct       │
                    │    │           │       ┌──┘            │         │
                    │    ▼           │       │               ▼         │
                    │ Vertex AI      │   VectorDB +       Direct LLM   │
                    │ Vector Search  │   Web Search                    │
                    │    └───────────┴───────┴──────────────┘          │
                    │                        │                         │
                    │                   ┌────▼────┐                    │
                    │                   │Generate │ ← Groq Llama 4     │
                    │                   └────┬────┘                    │
                    │                       END                        │
                    └──────────────────────────────────────────────────┘
                              │                         │
              ┌───────────────▼──┐            ┌─────────▼──────────┐
              │ Vertex AI Vector │            │  Tavily Web Search  │
              │ Search (GCP)     │            │  (live regulations) │
              └──────────────────┘            └────────────────────┘
                                       │
                    ┌──────────────────▼───────────────────────────────┐
                    │           LangSmith  (Observability)             │
                    │                                                  │
                    │  Full trace of every query  ·  Routing audit     │
                    │  Retrieved chunks logged  ·  Answer quality      │
                    │  Legally-defensible audit trail per query        │
                    └──────────────────────────────────────────────────┘
                                       │
                    ┌──────────────────▼───────────────────────────────┐
                    │           MCP Server                             │
                    │                                                  │
                    │  Exposes compliance knowledge base as a tool     │
                    │  Slack  ·  CRM  ·  Ticketing  ·  Any MCP client  │
                    └──────────────────────────────────────────────────┘
```

---

## Technology Stack — Every Component Explained

### AI / ML Layer

| Component | Technology | Role |
|---|---|---|
| **Vector Embeddings** | Vertex AI `text-embedding-005` (768-dim) | ML model — converts compliance text to semantic vectors |
| **LLM** | Groq `llama-4-scout-17b` | ML model — answer generation, intent routing |
| **Agent Orchestration** | LangGraph StateGraph | Multi-node reasoning graph with conditional routing |
| **Vector Search** | GCP Vertex AI Matching Engine (Tree-AH ANN) | Approximate nearest-neighbour search over compliance docs |
| **Web Retrieval** | Tavily Search API | Live regulatory updates beyond uploaded documents |

### Conversational AI Layer

| Component | Technology | Role |
|---|---|---|
| **Conversational Interface** | Dialogflow CX | Intent detection, multi-turn flows, voice (CCAI-ready), entity extraction |
| **Webhook Fulfillment** | FastAPI `/dialogflow-webhook` | Dialogflow calls this to get dynamic answers from the RAG pipeline |

### Infrastructure Layer

| Component | Technology | Role |
|---|---|---|
| **Observability** | LangSmith | Full trace of every agent run — routing decisions, retrieved chunks, generated answers, token counts, latency — serves as audit trail |
| **Interoperability** | MCP Server | Exposes the compliance knowledge base as a standard tool for any MCP-compatible system |
| **API** | FastAPI + SSE | Token-by-token streaming, PDF upload, Dialogflow webhook |
| **Frontend** | React 18 + Vite | Web chat with streaming, citations, PDF drag-drop |
| **Deployment** | GCP Cloud Run | Serverless backend, scales to zero |

---

## The Audit Trail — Why It Matters Here

Most RAG projects treat observability as a developer convenience. For compliance, it is a **legal requirement**. LangSmith traces every query with:

- Timestamp and exact question asked
- Which documents were retrieved (source file, page number, chunk content)
- The full prompt sent to the LLM
- The exact answer generated
- Routing decision and reasoning
- Token counts and latency

This means if a regulator asks *"what information did your team access when making this decision?"* — the answer is in the LangSmith project, timestamped and immutable for 14 days (extendable on paid plan).

---

## RAG Pipeline — Chunking and Indexing Details

| Parameter | Value | Why |
|---|---|---|
| Chunk size | 1000 characters | Fits one regulatory clause or policy paragraph |
| Chunk overlap | 150 characters | Prevents cutting a sentence across chunk boundary |
| Splitter | RecursiveCharacterTextSplitter | Splits on paragraphs first, then sentences, then words |
| Embedding model | `text-embedding-005` | Google's latest text embedding, 768 dimensions |
| Index type | Tree-AH (Approximate Nearest Neighbour) | Fast semantic search across thousands of doc chunks |
| Distance metric | Dot product | Standard for transformer embeddings |
| Retrieval k | Top 4 chunks | Balances context richness vs prompt length |
| Index updates | Stream update | New PDFs appear in search within seconds |

---

## Observability — LangSmith Traces

Every compliance query produces a named trace in LangSmith:

```
▼ LangGraph run  (2.8s total)
   ▼ orchestrator          (0.3s)  — decided route: vectordb
   ▼ retrieve_from_vectordb (0.9s) — 4 chunks from DPA-2024.pdf
   ▼ generate              (1.6s)  — 312 prompt tokens, 98 completion tokens
       Full prompt visible · Full answer visible · Source chunks visible
```

Screenshot of live LangSmith dashboard — _coming soon_

---

## Project Structure

```
VertexMind/
│
├── backend/
│   ├── agent.py              # LangGraph graph — all nodes, routing, @traceable hooks
│   ├── app.py                # FastAPI — /chat, /chat/stream, /upload, /dialogflow-webhook
│   ├── ingest.py             # one-time Vertex AI index setup
│   ├── ingest_pipeline.py    # ingestion called by /upload endpoint
│   ├── main.py               # server entry point, auto-activates venv
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

## Running Locally

You need Python 3.11+, Node.js 18+, a GCP project with Vertex AI enabled, and API keys for Groq, Tavily, and LangSmith.

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
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_...
LANGCHAIN_PROJECT=vertexmind-rag
```

**3. GCP auth**
```bash
gcloud auth application-default login
```

**4. Backend setup**
```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

**5. First-time indexing** — set your PDF paths in `ingest.py`, then:
```bash
python ingest.py
# Takes ~30 min first run (creates Vertex AI index). One-time only.
```

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

## API Reference

**POST /chat** — standard request/response
```json
{ "question": "What is our GDPR data retention policy?", "history": [] }

{
  "route": "vectordb",
  "answer": "Under your DPA-2024 policy...",
  "citations": [{ "source": "DPA-2024.pdf", "page": 12, "snippet": "..." }]
}
```

**POST /chat/stream** — SSE token-by-token streaming
```
data: {"type": "route",     "route": "vectordb"}
data: {"type": "token",     "content": "Under "}
data: {"type": "token",     "content": "your "}
data: {"type": "citations", "citations": [...]}
data: {"type": "done"}
```

**POST /upload** — PDF ingestion
```json
{ "status": "processing", "filename": "GDPR-guidelines.pdf" }
```

**POST /dialogflow-webhook** — Dialogflow CX fulfillment
```json
{ "text": "What is our data retention policy?" }
→ Dialogflow CX structured response with answer from RAG pipeline
```

---

## What I Learned Building This

- LangGraph's conditional routing feels simple until you need the LLM itself to make routing decisions — getting it to consistently pick the right source for ambiguous compliance questions took several prompt iterations, and LangSmith traces were essential for diagnosing wrong decisions
- FastAPI's `StreamingResponse` with SSE works cleanly for real-time token delivery, but LangChain's retrieval is synchronous — `asyncio.to_thread` is the correct fix, not running sync code in async context directly
- Vertex AI Vector Search has a ~30 minute cold start for index creation, but once deployed it handles semantic search across hundreds of compliance documents in under a second
- LangSmith's `@traceable` decorator is zero-footprint observability — it doesn't change function behaviour at all, it just wraps it with telemetry. For a compliance use case, this trace data is genuinely useful as an audit record, not just a developer debugging tool
- Building for a specific domain (compliance) rather than a generic chatbot forces every architectural decision to have a business justification — which makes the project much easier to explain in interviews

---

## Built With

LangGraph · Groq · Vertex AI Vector Search · Dialogflow CX · LangSmith · FastAPI · React · GCP Cloud Run

---

**Buddha Bhavana**
[GitHub](https://github.com/YOUR_GITHUB) · [LinkedIn](https://linkedin.com/in/YOUR_LINKEDIN) · tcwneat@aicte-india.org
