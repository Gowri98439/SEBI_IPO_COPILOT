"""
Model Router
Routes tasks to the appropriate model based on configuration and fallbacks.
"""
from app.ai.model_registry import SUPPORTED_LLMS, SUPPORTED_EMBEDDINGS
from app.config import settings

def get_model_for_task(task_type: str = "general"):
    """
    Returns the ModelConfig to use based on the task type.
    """
    if task_type == "fast":
        return SUPPORTED_LLMS.get("groq_llama_3_3_70b", SUPPORTED_LLMS.get("gemini_1_5_flash"))
    elif task_type == "reasoning":
        return SUPPORTED_LLMS.get("gemini_1_5_pro", SUPPORTED_LLMS.get("groq_llama_3_3_70b"))
    
    # Default fallback to configured LLM
    for key, config in SUPPORTED_LLMS.items():
        if config.model_name == settings.LLM_MODEL and config.provider == settings.LLM_PROVIDER:
            return config
            
    return SUPPORTED_LLMS.get("groq_llama_3_3_70b", list(SUPPORTED_LLMS.values())[0])

def get_embedding_model():
    # Always prefer local MiniLM — it's free, offline, and consistent.
    # Google text-embedding-004 requires a specific API endpoint not available in all regions.
    # Override only if explicitly set to a non-local embedding model in config and Google key works.
    explicit = settings.EMBEDDING_MODEL or ""
    if "minilm" in explicit.lower() or "huggingface" in explicit.lower() or not explicit:
        return SUPPORTED_EMBEDDINGS.get("local_minilm", list(SUPPORTED_EMBEDDINGS.values())[0])
    # Allow explicit Google embedding if specifically requested
    for key, config in SUPPORTED_EMBEDDINGS.items():
        if explicit in config.model_name or config.model_name in explicit:
            return config
    # Safe default: local model
    return SUPPORTED_EMBEDDINGS.get("local_minilm", list(SUPPORTED_EMBEDDINGS.values())[0])
