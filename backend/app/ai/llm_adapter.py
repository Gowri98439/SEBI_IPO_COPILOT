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

    primary_model = None
    fallback_model = None

    if config.provider == "groq" and settings.GROQ_API_KEY:
        try:
            from langchain_groq import ChatGroq
            primary_model = ChatGroq(
                model=config.model_name,
                temperature=temperature,
                api_key=settings.GROQ_API_KEY,
                max_retries=2,
                timeout=30.0,
            )
        except Exception as e:
            logger.warning("Could not initialize ChatGroq: %s", e)

    if settings.GOOGLE_API_KEY:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            fallback_model = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                temperature=temperature,
                google_api_key=settings.GOOGLE_API_KEY,
                max_retries=2,
            )
        except Exception as e:
            logger.warning("Could not initialize ChatGoogleGenerativeAI: %s", e)

    if primary_model and fallback_model:
        return primary_model.with_fallbacks([fallback_model])
    elif primary_model:
        return primary_model
    elif fallback_model:
        return fallback_model
    else:
        raise ValueError(f"No valid API keys configured for provider {config.provider}")
