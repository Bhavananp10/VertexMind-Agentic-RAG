# ingest.py

# Run this ONCE to:
# 1. Parse your PDF
# 2. Chunk the text
# 3. Create Vertex AI Vector Search Index + Endpoint
# 4. Ingest embeddings + chunks into Vector Search via GCS

import os
import re
import warnings

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_google_vertexai import VertexAIEmbeddings
from langchain_google_vertexai.vectorstores import VectorSearchVectorStore

from google.cloud import aiplatform

# Suppress LangChain deprecation warnings
try:
    from langchain_core._api.deprecation import LangChainDeprecationWarning

    warnings.filterwarnings(
        "ignore",
        category=LangChainDeprecationWarning
    )
except Exception:
    pass

warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning
)

load_dotenv()

# ==========================================================
# CONFIG
# ==========================================================

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
REGION = os.getenv("GCP_REGION")
BUCKET = os.getenv("GCS_BUCKET")

INDEX_NAME = os.getenv("INDEX_DISPLAY_NAME")
ENDPOINT_NAME = os.getenv("ENDPOINT_DISPLAY_NAME")

# Put your PDF path(s) here
PDF_PATHS = [
    r"E:\Downloads\Responsibilities.pdf"
]

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
# STEP 2 : LOAD PDFS
# ==========================================================

print("\nLoading PDF(s)...")

all_docs = []

for path in PDF_PATHS:

    loader = PyPDFLoader(path)
    docs = loader.load()

    # Clean PDF text BEFORE chunking
    for doc in docs:

        text = doc.page_content

        # Merge broken lines inside paragraphs
        text = re.sub(
            r"(?<!\n)\n(?!\n)",
            " ",
            text
        )

        # Keep paragraph breaks
        text = re.sub(
            r"\n{2,}",
            "\n\n",
            text
        )

        # Remove extra spaces
        text = re.sub(
            r"[ \t]+",
            " ",
            text
        )

        # Fix broken hyphenated words
        text = re.sub(
            r"-\s+",
            "",
            text
        )

        doc.page_content = text.strip()

    all_docs.extend(docs)

    print(
        f"Loaded: {path} + {len(docs)} pages"
    )

print(
    f"\nTotal pages loaded: {len(all_docs)}"
)

# ==========================================================
# STEP 3 : CHUNK DOCUMENTS
# ==========================================================

print("\nChunking documents...")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,

    # IMPORTANT:
    # Removed aggressive separators
    separators=[
        "\n\n",
        ".",
        "?",
        "!",
        " "
    ]
)

chunks = splitter.split_documents(
    all_docs
)

print(
    f"Total chunks created: {len(chunks)}"
)

# Preview chunk
if chunks:
    print(
        f"\nPreview of chunk 1:\n"
        f"{chunks[0].page_content[:200]}"
    )

# ==========================================================
# STEP 4 : EMBEDDINGS
# ==========================================================

print(
    "\nSetting up Vertex AI Embeddings "
    "(text-embedding-005)..."
)

embeddings = VertexAIEmbeddings(
    model_name="text-embedding-005",
    project=PROJECT_ID,
    location=REGION,
)

print("Embedding model ready.")

# ==========================================================
# STEP 5 : CREATE VECTOR SEARCH INDEX
# ==========================================================

print(
    "\nCreating Vertex AI Vector Search Index..."
)

print(
    "This can take 10-30 minutes. "
    "Please wait..."
)

my_index = (
    aiplatform.MatchingEngineIndex
    .create_tree_ah_index(
        display_name=INDEX_NAME,

        # Must match embedding dimensions
        dimensions=768,

        approximate_neighbors_count=10,

        leaf_node_embedding_count=500,

        leaf_nodes_to_search_percent=7,

        index_update_method="STREAM_UPDATE",

        distance_measure_type=
        "DOT_PRODUCT_DISTANCE",
    )
)

print("\nIndex created!")

print(
    f"Index Resource Name: "
    f"{my_index.resource_name}"
)

# ==========================================================
# STEP 6 : CREATE ENDPOINT
# ==========================================================

print(
    "\nCreating Vertex AI Index Endpoint..."
)

my_index_endpoint = (
    aiplatform.MatchingEngineIndexEndpoint
    .create(
        display_name=ENDPOINT_NAME,
        public_endpoint_enabled=True
    )
)

print("\nEndpoint created!")

print(
    f"Endpoint Resource Name: "
    f"{my_index_endpoint.resource_name}"
)

# ==========================================================
# STEP 7 : DEPLOY INDEX
# ==========================================================

print(
    "\nDeploying Index to Endpoint..."
)

print(
    "This can take another "
    "10-20 minutes..."
)

my_index_endpoint.deploy_index(
    index=my_index,
    deployed_index_id=
    "multi_agent_11_deployed_index",
)

print(
    "\nIndex successfully deployed "
    "to Endpoint!"
)

# ==========================================================
# STEP 8 : INGEST CHUNKS
# ==========================================================

print(
    "\nIngesting chunks into "
    "Vertex AI Vector Search..."
)

print(
    "Generating embeddings + "
    "uploading to GCS + indexing..."
)

vector_store = (
    VectorSearchVectorStore
    .from_components(
        project_id=PROJECT_ID,

        region=REGION,

        gcs_bucket_name=BUCKET,

        index_id=my_index.name,

        endpoint_id=
        my_index_endpoint.name,

        embedding=embeddings,

        stream_update=True,
    )
)

# This call:
# chunk text
# -> embed
# -> store in GCS
# -> index in Vector Search

vector_store.add_documents(
    chunks
)

print(
    f"\nAll {len(chunks)} chunks "
    f"ingested successfully!"
)

# ==========================================================
# STEP 9 : SAVE IDS
# ==========================================================

with open(
    "vector_store_ids.txt",
    "w",
    encoding="utf-8"
) as f:

    f.write(
        f"INDEX_ID={my_index.name}\n"
    )

    f.write(
        f"ENDPOINT_ID="
        f"{my_index_endpoint.name}\n"
    )

# ==========================================================
# COMPLETE
# ==========================================================

print("\n" + "=" * 60)

print("INGESTION COMPLETE!")

print("=" * 60)

print(
    "Index ID saved to "
    "vector_store_ids.txt"
)

print(
    "Endpoint ID saved to "
    "vector_store_ids.txt"
)

print(
    "\nNow run: uv run agent.py"
)

print("=" * 60)