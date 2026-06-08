"""
ingest_pipeline.py
Callable ingestion function used by the /upload endpoint.
Adds documents to an EXISTING vector store (vector_store_ids.txt must exist).
"""

import os
import re
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_google_vertexai.vectorstores import VectorSearchVectorStore
from google.cloud import aiplatform

load_dotenv()

_BACKEND_DIR = Path(__file__).parent
_IDS_FILE    = _BACKEND_DIR / "vector_store_ids.txt"


def _load_and_chunk(pdf_path: str) -> list:
    loader = PyPDFLoader(pdf_path)
    docs   = loader.load()

    for doc in docs:
        text = doc.page_content
        text = re.sub(r"(?<!\n)\n(?!\n)", " ",    text)
        text = re.sub(r"\n{2,}",          "\n\n", text)
        text = re.sub(r"[ \t]+",          " ",    text)
        text = re.sub(r"-\s+",            "",     text)
        doc.page_content = text.strip()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\n\n", ".", "?", "!", " "],
    )
    return splitter.split_documents(docs)


def ingest_pdf(pdf_path: str) -> int:
    """
    Load, chunk and embed a PDF into the existing Vertex AI Vector Search index.
    Returns the number of chunks ingested.
    Raises RuntimeError if no vector store is configured.
    """
    if not _IDS_FILE.exists():
        raise RuntimeError(
            "No vector store found (vector_store_ids.txt missing). "
            "Run ingest.py first."
        )

    with open(_IDS_FILE, "r") as f:
        saved = dict(line.strip().split("=", 1) for line in f if "=" in line)

    PROJECT_ID = os.getenv("GCP_PROJECT_ID")
    REGION     = os.getenv("GCP_REGION")
    BUCKET     = os.getenv("GCS_BUCKET")

    aiplatform.init(
        project=PROJECT_ID,
        location=REGION,
        staging_bucket=f"gs://{BUCKET}",
    )

    embeddings = VertexAIEmbeddings(
        model_name="text-embedding-005",
        project=PROJECT_ID,
        location=REGION,
    )

    vector_store = VectorSearchVectorStore.from_components(
        project_id=PROJECT_ID,
        region=REGION,
        gcs_bucket_name=BUCKET,
        index_id=saved["INDEX_ID"],
        endpoint_id=saved["ENDPOINT_ID"],
        embedding=embeddings,
        stream_update=True,
    )

    chunks = _load_and_chunk(pdf_path)
    vector_store.add_documents(chunks)
    return len(chunks)
