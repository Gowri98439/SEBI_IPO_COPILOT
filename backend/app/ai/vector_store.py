"""
ChromaDB vector store singleton for IPO Copilot AI.
Manages persistent Chroma collections for SEBI corpus and document chunks.
"""
from __future__ import annotations

import logging
from typing import List

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_core.documents import Document

from langchain_chroma import Chroma

import os
import pickle
from rank_bm25 import BM25Okapi

from app.ai.embeddings import get_embeddings
from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton Chroma persistent client
# ---------------------------------------------------------------------------

_chroma_client: chromadb.ClientAPI | None = None  # type: ignore


def get_chroma_client() -> chromadb.ClientAPI:  # type: ignore
    """
    Return (or create) the singleton ChromaDB persistent client.
    Stores data at settings.CHROMA_PERSIST_DIR.
    Thread-safe at the FastAPI worker level (single process per uvicorn worker).
    """
    global _chroma_client
    if _chroma_client is None:
        logger.info("Initialising ChromaDB persistent client at: %s", settings.CHROMA_PERSIST_DIR)
        _chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )
        logger.info("ChromaDB client initialised successfully.")
    return _chroma_client


# ---------------------------------------------------------------------------
# Collection-level helpers
# ---------------------------------------------------------------------------

SEBI_COLLECTION = "sebi_regulations"
DOCUMENT_COLLECTION_PREFIX = "workspace_"


def get_sebi_vectorstore() -> Chroma:
    """
    Return a LangChain Chroma vectorstore for the 'sebi_regulations' collection.
    Used by the RAG pipeline to query the indexed SEBI corpus.
    """
    client = get_chroma_client()
    embeddings = get_embeddings()
    return Chroma(
        client=client,
        collection_name=SEBI_COLLECTION,
        embedding_function=embeddings,
    )


def get_workspace_vectorstore(workspace_id: str) -> Chroma:
    """
    Return a LangChain Chroma vectorstore for a specific workspace's documents.
    Each workspace gets its own collection for document isolation.
    """
    client = get_chroma_client()
    embeddings = get_embeddings()
    collection_name = f"{DOCUMENT_COLLECTION_PREFIX}{workspace_id}"
    return Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embeddings,
    )


def add_documents_to_vectorstore(
    docs: List[Document],
    collection_name: str,
) -> int:
    """
    Add LangChain Document objects to a named ChromaDB collection.

    Args:
        docs: List of LangChain Document objects with page_content and metadata.
        collection_name: Target ChromaDB collection name.

    Returns:
        Number of documents successfully added.
    """
    if not docs:
        logger.warning("add_documents_to_vectorstore called with empty docs list.")
        return 0

    client = get_chroma_client()
    embeddings = get_embeddings()

    vectorstore = Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embeddings,
    )

    # Add in batches of 100 to avoid memory spikes
    batch_size = 100
    total_added = 0
    for i in range(0, len(docs), batch_size):
        batch = docs[i : i + batch_size]
        vectorstore.add_documents(batch)
        total_added += len(batch)
        logger.debug("Added batch %d/%d (%d docs) to collection '%s'",
                     i // batch_size + 1,
                     (len(docs) + batch_size - 1) // batch_size,
                     len(batch),
                     collection_name)

    logger.info("Total %d documents added to collection '%s'", total_added, collection_name)
    
    # After chroma add, we need to rebuild the BM25 index.
    # To do this correctly, we retrieve all docs from the existing BM25 cache, append new ones, and rebuild.
    _, existing_docs = get_bm25_index(collection_name)
    all_docs = (existing_docs or []) + docs
    build_bm25_index(all_docs, collection_name)
    
    return total_added


def get_collection_count(collection_name: str) -> int:
    """Return the number of items in a ChromaDB collection (0 if not found)."""
    client = get_chroma_client()
    try:
        collection = client.get_collection(name=collection_name)
        return collection.count()
    except Exception:
        return 0


def delete_workspace_collection(workspace_id: str) -> None:
    """Delete all document vectors for a given workspace."""
    client = get_chroma_client()
    collection_name = f"{DOCUMENT_COLLECTION_PREFIX}{workspace_id}"
    try:
        client.delete_collection(name=collection_name)
        logger.info("Deleted ChromaDB collection: %s", collection_name)
        
        # Delete BM25 cache files
        bm25_dir = os.path.join(settings.CHROMA_PERSIST_DIR, "bm25")
        index_path = os.path.join(bm25_dir, f"{collection_name}.pkl")
        docs_path = os.path.join(bm25_dir, f"{collection_name}_docs.pkl")
        if os.path.exists(index_path):
            os.remove(index_path)
        if os.path.exists(docs_path):
            os.remove(docs_path)
    except Exception as exc:
        logger.warning("Could not delete collection '%s': %s", collection_name, exc)


# ---------------------------------------------------------------------------
# Hybrid Retrieval (BM25 + RRF)
# ---------------------------------------------------------------------------

def build_bm25_index(docs: List[Document], collection_name: str) -> None:
    """Build a BM25 index over the provided documents and pickle it to disk."""
    if not docs:
        return
        
    tokenized_corpus = [doc.page_content.lower().split() for doc in docs]
    bm25 = BM25Okapi(tokenized_corpus)
    
    bm25_dir = os.path.join(settings.CHROMA_PERSIST_DIR, "bm25")
    os.makedirs(bm25_dir, exist_ok=True)
    
    index_path = os.path.join(bm25_dir, f"{collection_name}.pkl")
    docs_path = os.path.join(bm25_dir, f"{collection_name}_docs.pkl")
    
    try:
        with open(index_path, "wb") as f:
            pickle.dump(bm25, f)
        with open(docs_path, "wb") as f:
            pickle.dump(docs, f)
        logger.info("Built and persisted BM25 index for collection '%s' with %d docs.", collection_name, len(docs))
    except Exception as exc:
        logger.error("Failed to persist BM25 index for '%s': %s", collection_name, exc)

def get_bm25_index(collection_name: str):
    """Retrieve the cached BM25 index and corresponding documents for a collection."""
    bm25_dir = os.path.join(settings.CHROMA_PERSIST_DIR, "bm25")
    index_path = os.path.join(bm25_dir, f"{collection_name}.pkl")
    docs_path = os.path.join(bm25_dir, f"{collection_name}_docs.pkl")
    
    if not os.path.exists(index_path) or not os.path.exists(docs_path):
        return None, None
        
    try:
        with open(index_path, "rb") as f:
            bm25 = pickle.load(f)
        with open(docs_path, "rb") as f:
            docs = pickle.load(f)
        return bm25, docs
    except Exception as exc:
        logger.warning("Failed to load BM25 index for '%s': %s", collection_name, exc)
        return None, None

def search_bm25(query: str, collection_name: str, top_k: int = 5) -> List[tuple[Document, float]]:
    """Search the BM25 index for a given query."""
    bm25, docs = get_bm25_index(collection_name)
    if not bm25 or not docs:
        logger.warning("BM25 index not found for collection '%s'. Falling back to empty results.", collection_name)
        return []
        
    tokenized_query = query.lower().split()
    doc_scores = bm25.get_scores(tokenized_query)
    
    # Sort docs by score
    top_n_indices = sorted(range(len(doc_scores)), key=lambda i: doc_scores[i], reverse=True)[:top_k]
    
    # Only return docs with a positive score
    return [(docs[i], doc_scores[i]) for i in top_n_indices if doc_scores[i] > 0]

def rrf_merge(
    dense_results: List[tuple[Document, float]], 
    bm25_results: List[tuple[Document, float]], 
    k: int = 60, 
    top_n: int = 5
) -> List[tuple[Document, float]]:
    """
    Reciprocal Rank Fusion (RRF) to merge Dense and BM25 search results.
    Returns the fused list of (Document, fused_score).
    """
    rrf_scores = {}
    doc_store = {}
    
    def _get_doc_id(doc: Document) -> str:
        # Generate a unique ID based on file metadata or content hash
        # If source_file and chunk_index exist, they form a unique key
        source = doc.metadata.get("source_file", "unknown")
        idx = doc.metadata.get("chunk_index", -1)
        if idx != -1:
            return f"{source}_{idx}"
        import hashlib
        return hashlib.md5(doc.page_content.encode("utf-8")).hexdigest()
        
    for rank, (doc, _) in enumerate(dense_results):
        doc_id = _get_doc_id(doc)
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
        doc_store[doc_id] = doc
        
    for rank, (doc, _) in enumerate(bm25_results):
        doc_id = _get_doc_id(doc)
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
        doc_store[doc_id] = doc

    sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return [(doc_store[doc_id], score) for doc_id, score in sorted_docs[:top_n]]
