"""
Embedding Adapter
Provides unified factory for LangChain Embeddings.
Supports Google Generative AI and HuggingFace sentence-transformers as fallback.
"""
from langchain_core.embeddings import Embeddings
from app.ai.model_registry import ModelConfig
from app.config import settings
import logging

logger = logging.getLogger(__name__)


def get_embedding_adapter(config: ModelConfig) -> Embeddings:
    if config.provider == "google":
        if not settings.GOOGLE_API_KEY:
            logger.warning("GOOGLE_API_KEY not set — falling back to local HuggingFace embeddings.")
            return _get_huggingface_embeddings()
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            return GoogleGenerativeAIEmbeddings(
                model=config.model_name,
                google_api_key=settings.GOOGLE_API_KEY,
            )
        except Exception as exc:
            logger.error("Google embeddings failed (%s) — falling back to local HuggingFace embeddings.", exc)
            return _get_huggingface_embeddings()

    if config.provider == "huggingface":
        return _get_huggingface_embeddings(config.model_name)

    raise ValueError(f"Unsupported provider {config.provider}")


def _get_huggingface_embeddings(model_name: str = "all-MiniLM-L6-v2") -> Embeddings:
    """Use a local sentence-transformer model — no API key needed."""
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        logger.info("Loading HuggingFace embedding model: %s", model_name)
        return HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    except ImportError:
        logger.error("langchain_huggingface not installed. Install with: pip install langchain-huggingface sentence-transformers")
        raise
