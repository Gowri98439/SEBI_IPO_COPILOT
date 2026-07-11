"""
Model Registry
Defines the supported LLMs and Embedding models.
"""
from dataclasses import dataclass

@dataclass
class ModelConfig:
    provider: str
    model_name: str
    is_fast: bool = False
    is_reasoning: bool = False

SUPPORTED_LLMS = {
    "groq_llama_3_3_70b": ModelConfig(provider="groq", model_name="llama-3.3-70b-versatile", is_fast=True),
    "groq_llama_3_8b": ModelConfig(provider="groq", model_name="llama-3.1-8b-instant", is_fast=True),
    "gemini_1_5_flash": ModelConfig(provider="google", model_name="gemini-1.5-flash", is_fast=True),
    "gemini_1_5_pro": ModelConfig(provider="google", model_name="gemini-1.5-pro", is_reasoning=True),
}

SUPPORTED_EMBEDDINGS = {
    # Google text-embedding-004 is the current recommended model (replaces deprecated embedding-001)
    "google_text_embedding_004": ModelConfig(provider="google", model_name="models/text-embedding-004"),
    # Fallback: local sentence transformer (no API key needed)
    "local_minilm": ModelConfig(provider="huggingface", model_name="all-MiniLM-L6-v2"),
}
