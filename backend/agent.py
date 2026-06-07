# START -> orchestrator -> [conditional routing] -> generate -> END
# -----------------------------------------------------------------

import os
from typing import Literal
from dotenv import load_dotenv
from typing_extensions import TypedDict

# LangGraph
from langgraph.graph import StateGraph, START, END

# LangChain
from langchain_groq import ChatGroq
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_google_vertexai.vectorstores import VectorSearchVectorStore
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.documents import Document

# GCP
from google.cloud import aiplatform

import warnings
from langchain_core._api.deprecation import LangChainDeprecationWarning

warnings.filterwarnings(
    "ignore",
    category=LangChainDeprecationWarning
)

warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning
)

load_dotenv()

# -------------------------------------------------------------
# Config
# -------------------------------------------------------------
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
REGION = os.getenv("GCP_REGION")
BUCKET = os.getenv("GCS_BUCKET")

# -------------------------------------------------------------
# Load saved Index + Endpoint IDs from ingest.py
# -------------------------------------------------------------
with open("vector_store_ids.txt", "r") as f:
    lines = dict(
        line.strip().split("=", 1)
        for line in f
        if "=" in line
    )

INDEX_ID = lines["INDEX_ID"]
ENDPOINT_ID = lines["ENDPOINT_ID"]

# -------------------------------------------------------------
# GLOBAL SINGLETONS (Lazy Initialization)
# Prevent Cloud Run startup timeout
# -------------------------------------------------------------
llm = None
retriever = None
web_search = None

# -------------------------------------------------------------
# Lazy initialize ALL expensive components
# ONLY runs on first request
# -------------------------------------------------------------
def initialize_components():
    global llm, retriever, web_search

    # Prevent re-initialization
    if llm is not None:
        return

    # ---------------------------------------------------------
    # Initialize GCP
    # ---------------------------------------------------------
    print("STEP 1")

    aiplatform.init(
        project=PROJECT_ID,
        location=REGION,
        staging_bucket=f"gs://{BUCKET}",
    )

    # ---------------------------------------------------------
    # LLM - Groq (Fast + Free tier)
    # ---------------------------------------------------------
    print("STEP 2")

    llm = ChatGroq(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY"),
    )

    # ---------------------------------------------------------
    # Embeddings - Vertex AI text-embedding-005
    # ---------------------------------------------------------
    print("STEP 3")

    embeddings = VertexAIEmbeddings(
        model_name="text-embedding-005",
        project=PROJECT_ID,
        location=REGION,
    )

    # ---------------------------------------------------------
    # Vector Store - Vertex AI Vector Search (GCP)
    # ---------------------------------------------------------
    print("STEP 4")

    vector_store = VectorSearchVectorStore.from_components(
        project_id=PROJECT_ID,
        region=REGION,
        gcs_bucket_name=BUCKET,
        index_id=INDEX_ID,
        endpoint_id=ENDPOINT_ID,
        embedding=embeddings,
        stream_update=False,
    )

    # Retriever
    retriever = vector_store.as_retriever(
        search_kwargs={"k": 4}
    )

    # ---------------------------------------------------------
    # Web Search Tool - Tavily
    # ---------------------------------------------------------
    print("STEP 5")

    web_search = TavilySearchResults(
        max_results=3,
        tavily_api_key=os.getenv("TAVILY_API_KEY"),
    )

    print("All components initialized successfully!")


class GraphState(TypedDict):
    question: str
    route: str
    vector_docs: list[Document]
    web_results: list[dict]
    final_answer: str


# =============================================================
# NODE 1 — ORCHESTRATOR
# Brain of the agent — decides WHERE to look for the answer
# =============================================================
def orchestrator(state: GraphState) -> GraphState:
    """
    Routing Logic:
    - vectordb   -> question is about the PDF content
    - websearch  -> question needs real-time / internet data
    - both       -> question needs both sources
    """

    question = state["question"]

    system_prompt = """
You are an intelligent routing agent for a RAG system.

Based on the user's question, decide where to search for the answer.

The uploaded document is a fictional corporate thriller story titled
"THE LAST SIGNAL" about:

- NovaCrest Technologies - a tech company building SentinelAI
- Arjun Mehta - CEO/founder of NovaCrest
- Daniel Voss - Head of Core Architecture
- Priya Sood - CFO of NovaCrest
- Themes: corporate betrayal, ambition, IPO,
  AI technology, whistleblowing, silence

Routing Rules:

- Reply "vectordb"
  -> if the question is about the story,
     characters, events, plot, NovaCrest,
     Arjun, Daniel, Priya, SentinelAI etc.

- Reply "websearch"
  -> if the question requires current,
     real-time or internet information.

- Reply "both"
  -> if the question requires BOTH
     document context and web information.

- Reply "direct"
  -> if the question is a greeting,
     small talk, gibberish, nonsense,
     or general conversation.

IMPORTANT:

Reply with ONLY one of these exact words:

vectordb
websearch
both
direct

Do NOT add any explanation.
"""

    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=f"Question: {question}"
            ),
        ]
    )

    route = response.content.strip().lower()

    # Safety fallback
    if route not in [
        "vectordb",
        "websearch",
        "both",
        "direct",
    ]:
        print(
            f"⚠ Unexpected route '{route}' "
            f"- defaulting to 'both'"
        )
        route = "both"

    print(
        f"\n🧠 Orchestrator Decision -> "
        f"[{route.upper()}]"
    )

    return {
        **state,
        "route": route,
    }


# =============================================================
# NODE 2 — DIRECT LLM
# Handles greetings, gibberish, small talk directly
# =============================================================
def direct_llm(state: GraphState) -> GraphState:
    print(
        "💬 Direct LLM response "
        "(no retrieval needed)..."
    )

    response = llm.invoke(
        [
            SystemMessage(
                content=(
                    "You are a friendly and "
                    "helpful AI assistant. "
                    "Respond naturally and "
                    "conversationally."
                )
            ),
            HumanMessage(
                content=state["question"]
            ),
        ]
    )

    print("✅ Direct answer generated!")

    return {
        **state,
        "final_answer": response.content,
    }


# =============================================================
# NODE 3 — VECTOR DB RETRIEVER
# Searches Vertex AI Vector Search for relevant PDF chunks
# =============================================================
def retrieve_from_vectordb(
    state: GraphState,
) -> GraphState:

    print(
        "🔍 Searching Vector DB "
        "(Vertex AI Vector Search)..."
    )

    docs = retriever.invoke(
        state["question"]
    )

    print(
        f"✅ Retrieved {len(docs)} "
        f"relevant chunks from your PDFs."
    )

    for i, doc in enumerate(docs):
        src = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "?")

        print(
            f"    [{i+1}] Source: {src} | Page: {page}"
        )

    return {
        **state,
        "vector_docs": docs,
    }


# =============================================================
# NODE 4 — WEB SEARCH
# Searches the internet via Tavily for real-time information
# =============================================================
def search_web(state: GraphState) -> GraphState:

    print("🌐 Searching the Web (Tavily)...")

    results = web_search.invoke(
        {"query": state["question"]}
    )

    print(
        f"✅ Found {len(results)} web results."
    )

    for i, r in enumerate(results):
        print(
            f"    [{i+1}] "
            f"{r.get('url', 'No URL')}"
        )

    return {
        **state,
        "web_results": results,
    }


# =============================================================
# NODE 5 — GENERATOR
# Combines ALL retrieved context and generates the final answer
# =============================================================
def generate(state: GraphState) -> GraphState:

    print("🤖 Generating answer with Groq LLM...")

    context_parts = []

    # ---------------------------------------------------------
    # Add Vector DB context
    # ---------------------------------------------------------
    if state.get("vector_docs"):

        doc_context = "\n\n".join(
            [
                (
                    f"[PDF Chunk {i+1} | "
                    f"Page {doc.metadata.get('page', '?')}]:\n"
                    f"{doc.page_content}"
                )
                for i, doc in enumerate(
                    state["vector_docs"]
                )
            ]
        )

        context_parts.append(
            f"=== From Your Documents ===\n"
            f"{doc_context}"
        )

    # ---------------------------------------------------------
    # Add Web Search context
    # ---------------------------------------------------------
    if state.get("web_results"):

        web_context = "\n\n".join(
            [
                (
                    f"[Web Result {i+1}]\n"
                    f"URL: {r.get('url', 'N/A')}\n"
                    f"Content: {r.get('content', '')}"
                )
                for i, r in enumerate(
                    state["web_results"]
                )
            ]
        )

        context_parts.append(
            f"=== From Web Search ===\n"
            f"{web_context}"
        )

    # ---------------------------------------------------------
    # No context fallback
    # ---------------------------------------------------------
    if not context_parts:
        full_context = (
            "No context was retrieved "
            "from any source."
        )
    else:
        full_context = "\n\n".join(
            context_parts
        )

    # ---------------------------------------------------------
    # Final Prompt
    # ---------------------------------------------------------
    prompt = f"""
You are a helpful and accurate AI assistant.

Use the context provided below to answer the question clearly and concisely.

If the context doesn't contain enough information,
say so honestly — do not make things up.

CONTEXT:
{full_context}

QUESTION:
{state["question"]}

ANSWER:
"""

    response = llm.invoke(
        [HumanMessage(content=prompt)]
    )

    print("✅ Answer generated!")

    return {
        **state,
        "final_answer": response.content,
    }


# =============================================================
# ROUTING FUNCTION
# Called after orchestrator to decide which node comes next
# =============================================================
def route_after_orchestrator(
    state: GraphState,
) -> Literal[
    "retrieve_from_vectordb",
    "search_web",
    "direct_llm",
]:

    route = state["route"]

    if route == "vectordb":
        return "retrieve_from_vectordb"

    elif route == "websearch":
        return "search_web"

    elif route == "direct":
        return "direct_llm"

    else:
        return "retrieve_from_vectordb"


# =============================================================
# ROUTE AFTER VECTOR DB
# =============================================================
def route_after_vectordb(
    state: GraphState,
) -> Literal[
    "search_web",
    "generate",
]:
    """
    After vectordb retrieval:

    - both      -> search_web
    - vectordb  -> generate
    """

    if state["route"] == "both":
        return "search_web"

    return "generate"


# =============================================================
# BUILD THE LANGGRAPH
# =============================================================
def build_rag_graph():

    # Lazy initialize expensive components
    initialize_components()

    # Shared state schema
    graph = StateGraph(GraphState)

    # ---------------------------------------------------------
    # Register Nodes
    # ---------------------------------------------------------
    graph.add_node(
        "orchestrator",
        orchestrator,
    )

    graph.add_node(
        "direct_llm",
        direct_llm,
    )

    graph.add_node(
        "retrieve_from_vectordb",
        retrieve_from_vectordb,
    )

    graph.add_node(
        "search_web",
        search_web,
    )

    graph.add_node(
        "generate",
        generate,
    )

    # ---------------------------------------------------------
    # Entry Point
    # ---------------------------------------------------------
    graph.add_edge(
        START,
        "orchestrator",
    )

    # ---------------------------------------------------------
    # Conditional Routing
    # ---------------------------------------------------------
    graph.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {
            "retrieve_from_vectordb":
                "retrieve_from_vectordb",

            "search_web":
                "search_web",

            "direct_llm":
                "direct_llm",
        },
    )

    # ---------------------------------------------------------
    # After Vector Search
    # ---------------------------------------------------------
    graph.add_conditional_edges(
        "retrieve_from_vectordb",
        route_after_vectordb,
        {
            "search_web":
                "search_web",

            "generate":
                "generate",
        },
    )

    # ---------------------------------------------------------
    # Web Search -> Generate
    # ---------------------------------------------------------
    graph.add_edge(
        "search_web",
        "generate",
    )

    # ---------------------------------------------------------
    # End Routes
    # ---------------------------------------------------------
    graph.add_edge(
        "generate",
        END,
    )

    graph.add_edge(
        "direct_llm",
        END,
    )

    # Compile
    return graph.compile()


# =============================================================
# MAIN — Run the Agent in a chat loop
# =============================================================

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("🤖 Agentic RAG Agent")
    print(
        "🚀 LangGraph + Groq + "
        "Vertex AI Vector Search"
    )
    print("=" * 60)
    print("💬 Type your question below.")
    print("🚪 Type 'exit' to quit.")
    print("=" * 60 + "\n")

    app = build_rag_graph()

    while True:

        question = input("You: ").strip()

        if not question:
            continue

        if question.lower() in [
            "exit",
            "quit",
            "bye",
        ]:
            print(
                "\n👋 Goodbye! "
                "Happy learning GCP!"
            )
            break

        print("\n" + "-" * 60)

        initial_state: GraphState = {
            "question": question,
            "route": "",
            "vector_docs": [],
            "web_results": [],
            "final_answer": "",
        }

        result = app.invoke(
            initial_state
        )

        print(
            f"\n🤖 Answer:\n"
            f"{result['final_answer']}"
        )

        print(
            "-" * 60 + "\n"
        )