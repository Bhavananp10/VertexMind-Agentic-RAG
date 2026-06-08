# ingest.py
#
# Smart ingestion:
# - First run  → creates Index + Endpoint + deploys → saves IDs
# - Later runs → reuses existing Index + Endpoint, just adds new chunks
#
# Usage:  .\.venv\Scripts\python.exe ingest.py

import os
import re
import time
import warnings

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_google_vertexai import VertexAIEmbeddings
from langchain_google_vertexai.vectorstores import VectorSearchVectorStore

from google.cloud import aiplatform

try:
    from langchain_core._api.deprecation import LangChainDeprecationWarning
    warnings.filterwarnings("ignore", category=LangChainDeprecationWarning)
except Exception:
    pass

warnings.filterwarnings("ignore", category=DeprecationWarning)

load_dotenv()

# ==========================================================
# CONFIG
# ==========================================================

PROJECT_ID    = os.getenv("GCP_PROJECT_ID")
REGION        = os.getenv("GCP_REGION")
BUCKET        = os.getenv("GCS_BUCKET")
INDEX_NAME    = os.getenv("INDEX_DISPLAY_NAME")
ENDPOINT_NAME = os.getenv("ENDPOINT_DISPLAY_NAME")

# ── Put your PDF path(s) here ──────────────────────────────
PDF_PATHS = [
    r"E:\Downloads\Adventures-of-Huckleberry book-20-30.pdf"
]

IDS_FILE = "vector_store_ids.txt"

# ==========================================================
# STEP 1 : INIT GCP
# ==========================================================

print("\nInitializing GCP...")

aiplatform.init(
    project=PROJECT_ID,
    location=REGION,
    staging_bucket=f"gs://{BUCKET}",
)

# ==========================================================
# STEP 2 : LOAD PDFs
# ==========================================================

print("\nLoading PDF(s)...")

all_docs = []

for path in PDF_PATHS:
    loader = PyPDFLoader(path)
    docs   = loader.load()

    for doc in docs:
        text = doc.page_content
        text = re.sub(r"(?<!\n)\n(?!\n)", " ",    text)
        text = re.sub(r"\n{2,}",          "\n\n", text)
        text = re.sub(r"[ \t]+",          " ",    text)
        text = re.sub(r"-\s+",            "",     text)
        doc.page_content = text.strip()

    all_docs.extend(docs)
    print(f"Loaded: {path}  ({len(docs)} pages)")

print(f"\nTotal pages loaded: {len(all_docs)}")

# ==========================================================
# STEP 3 : CHUNK
# ==========================================================

print("\nChunking documents...")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,
    separators=["\n\n", ".", "?", "!", " "],
)

chunks = splitter.split_documents(all_docs)
print(f"Total chunks created: {len(chunks)}")

if chunks:
    print(f"\nPreview of chunk 1:\n{chunks[0].page_content[:200]}")

# ==========================================================
# STEP 4 : EMBEDDINGS
# ==========================================================

print("\nSetting up Vertex AI Embeddings (text-embedding-005)...")

embeddings = VertexAIEmbeddings(
    model_name="text-embedding-005",
    project=PROJECT_ID,
    location=REGION,
)

print("Embedding model ready.")

# ==========================================================
# DECISION: reuse existing store OR create from scratch?
# ==========================================================

if os.path.exists(IDS_FILE):

    # ── EXISTING INDEX → skip setup, just add docs ─────────
    print(f"\nFound {IDS_FILE} → reusing existing Index + Endpoint.")

    with open(IDS_FILE, "r") as f:
        saved = dict(line.strip().split("=", 1) for line in f if "=" in line)

    INDEX_ID    = saved["INDEX_ID"]
    ENDPOINT_ID = saved["ENDPOINT_ID"]

    print(f"   Index    : {INDEX_ID}")
    print(f"   Endpoint : {ENDPOINT_ID}")

    print("\nIngesting chunks into existing Vector Search store...")

    vector_store = VectorSearchVectorStore.from_components(
        project_id=PROJECT_ID,
        region=REGION,
        gcs_bucket_name=BUCKET,
        index_id=INDEX_ID,
        endpoint_id=ENDPOINT_ID,
        embedding=embeddings,
        stream_update=True,
    )

    vector_store.add_documents(chunks)
    print(f"\nAll {len(chunks)} chunks added to existing store!")

else:

    # ── FIRST RUN → full setup ─────────────────────────────
    print(f"\n{IDS_FILE} not found → running first-time setup.")

    # Timestamp guarantees a unique deployed_index_id every run
    DEPLOYED_INDEX_ID = f"deployed_index_{int(time.time())}"

    # =====================================================
    # STEP 5 : CREATE INDEX
    # =====================================================

    print("\nCreating Vertex AI Vector Search Index...")
    print("This can take 10-30 minutes. Please wait...")

    my_index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
        display_name=INDEX_NAME,
        dimensions=768,
        approximate_neighbors_count=10,
        leaf_node_embedding_count=500,
        leaf_nodes_to_search_percent=7,
        index_update_method="STREAM_UPDATE",
        distance_measure_type="DOT_PRODUCT_DISTANCE",
    )

    print(f"\nIndex created!")
    print(f"Index Resource Name: {my_index.resource_name}")

    # =====================================================
    # STEP 6 : CREATE ENDPOINT
    # =====================================================

    print("\nCreating Vertex AI Index Endpoint...")

    my_index_endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
        display_name=ENDPOINT_NAME,
        public_endpoint_enabled=True,
    )

    print(f"\nEndpoint created!")
    print(f"Endpoint Resource Name: {my_index_endpoint.resource_name}")

    # =====================================================
    # STEP 7 : DEPLOY INDEX  (unique ID avoids conflicts)
    # =====================================================

    print(f"\nDeploying Index to Endpoint...")
    print(f"Deployed index ID: {DEPLOYED_INDEX_ID}")
    print("This can take another 10-20 minutes...")

    my_index_endpoint.deploy_index(
        index=my_index,
        deployed_index_id=DEPLOYED_INDEX_ID,
    )

    print("\nIndex successfully deployed to Endpoint!")

    # =====================================================
    # STEP 8 : INGEST CHUNKS
    # =====================================================

    print("\nIngesting chunks into Vertex AI Vector Search...")
    print("Generating embeddings + uploading to GCS + indexing...")

    vector_store = VectorSearchVectorStore.from_components(
        project_id=PROJECT_ID,
        region=REGION,
        gcs_bucket_name=BUCKET,
        index_id=my_index.name,
        endpoint_id=my_index_endpoint.name,
        embedding=embeddings,
        stream_update=True,
    )

    vector_store.add_documents(chunks)
    print(f"\nAll {len(chunks)} chunks ingested successfully!")

    # =====================================================
    # STEP 9 : SAVE IDS
    # =====================================================

    with open(IDS_FILE, "w", encoding="utf-8") as f:
        f.write(f"INDEX_ID={my_index.name}\n")
        f.write(f"ENDPOINT_ID={my_index_endpoint.name}\n")

    print(f"\nIDs saved to {IDS_FILE}")

# ==========================================================
# COMPLETE
# ==========================================================

print("\n" + "=" * 60)
print("INGESTION COMPLETE!")
print("=" * 60)
print("\nNow run: python main.py")
print("=" * 60)
