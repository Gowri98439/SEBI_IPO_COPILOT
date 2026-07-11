"""
LangChain embeddings wrapper for IPO Copilot AI.
Provides factory functions for embeddings using the Model Router and Adapter.
"""
from functools import lru_cache
import hashlib
import json
import sqlite3

from langchain_core.embeddings import Embeddings
from app.ai.model_router import get_embedding_model
from app.ai.embedding_adapter import get_embedding_adapter
from app.config import settings

class CachedEmbeddings(Embeddings):
    def __init__(self, base_embeddings: Embeddings):
        self.base_embeddings = base_embeddings

    def _get_sync_conn(self):
        db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
        return sqlite3.connect(db_path)

    def _get_cached_embedding(self, text: str):
        md5_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
        try:
            with self._get_sync_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT embedding FROM embedding_cache WHERE id = ?", (md5_hash,))
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
        except Exception:
            pass
        return None

    def _set_cached_embedding(self, text: str, embedding: list[float]):
        md5_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
        try:
            with self._get_sync_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO embedding_cache (id, embedding, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)", (md5_hash, json.dumps(embedding)))
        except Exception:
            pass

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        results = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []
        
        for i, text in enumerate(texts):
            cached = self._get_cached_embedding(text)
            if cached:
                results[i] = cached
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)
                
        if uncached_texts:
            new_embs = self.base_embeddings.embed_documents(uncached_texts)
            for i, emb in zip(uncached_indices, new_embs):
                results[i] = emb
                self._set_cached_embedding(uncached_texts[uncached_indices.index(i)], emb)
                
        return results

    def embed_query(self, text: str) -> list[float]:
        cached = self._get_cached_embedding(text)
        if cached:
            return cached
        emb = self.base_embeddings.embed_query(text)
        self._set_cached_embedding(text, emb)
        return emb

@lru_cache(maxsize=1)
def get_embeddings() -> Embeddings:
    config = get_embedding_model()
    base_embeddings = get_embedding_adapter(config)
    return CachedEmbeddings(base_embeddings)
