"""
LangChain LLM client wrapper for IPO Copilot AI.
Provides factory functions for different LLM configurations using the Model Router and Adapter.
"""
from langchain_core.language_models.chat_models import BaseChatModel
from app.ai.model_router import get_model_for_task
from app.ai.llm_adapter import get_llm_adapter

def get_llm(temperature: float = 0.1) -> BaseChatModel:
    config = get_model_for_task("general")
    return get_llm_adapter(config, temperature)

def get_fast_llm(temperature: float = 0.1) -> BaseChatModel:
    config = get_model_for_task("fast")
    return get_llm_adapter(config, temperature)

def get_creative_llm(temperature: float = 0.7) -> BaseChatModel:
    config = get_model_for_task("general")
    return get_llm_adapter(config, temperature)
