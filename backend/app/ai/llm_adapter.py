"""
LLM Adapter
Provides unified factory for LangChain Chat Models.
"""
from langchain_core.language_models.chat_models import BaseChatModel
from app.ai.model_registry import ModelConfig
from app.config import settings

def get_llm_adapter(config: ModelConfig, temperature: float = 0.0) -> BaseChatModel:
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"Initializing LLM Adapter for {config.provider} - {config.model_name}")
    
    if config.provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=config.model_name,
            temperature=temperature,
            api_key=settings.GROQ_API_KEY
        )
    elif config.provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=config.model_name,
            temperature=temperature,
            google_api_key=settings.GOOGLE_API_KEY
        )
    raise ValueError(f"Unsupported provider {config.provider}")
