"""
LangChain LLM client wrapper for IPO Copilot AI.
Provides factory functions for different LLM configurations using the Model Router and Adapter.
Also provides an observable invoke wrapper that logs AI executions to the database.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage

from app.ai.model_router import get_model_for_task
from app.ai.llm_adapter import get_llm_adapter

logger = logging.getLogger(__name__)


def get_llm(temperature: float = 0.1) -> BaseChatModel:
    config = get_model_for_task("general")
    return get_llm_adapter(config, temperature)

def get_fast_llm(temperature: float = 0.1) -> BaseChatModel:
    config = get_model_for_task("fast")
    return get_llm_adapter(config, temperature)

def get_creative_llm(temperature: float = 0.7) -> BaseChatModel:
    config = get_model_for_task("general")
    return get_llm_adapter(config, temperature)


async def invoke_with_observability(
    llm: BaseChatModel,
    messages: list,
    workspace_id: Optional[str] = None,
    job_id: Optional[str] = None,
    db=None,
) -> Any:
    """
    Invoke an LLM and persist an AIExecution record to the database.
    Falls back gracefully if DB logging fails — never blocks the primary pipeline.
    """
    start_ts = time.monotonic()
    result = None
    tokens_prompt = None
    tokens_completion = None
    
    try:
        result = await llm.ainvoke(messages)
        
        # Extract token usage if available (Groq/OpenAI return this)
        if hasattr(result, "usage_metadata") and result.usage_metadata:
            tokens_prompt = result.usage_metadata.get("input_tokens")
            tokens_completion = result.usage_metadata.get("output_tokens")
        elif hasattr(result, "response_metadata") and result.response_metadata:
            meta = result.response_metadata.get("token_usage", {})
            tokens_prompt = meta.get("prompt_tokens")
            tokens_completion = meta.get("completion_tokens")
    except Exception:
        raise
    finally:
        elapsed_ms = (time.monotonic() - start_ts) * 1000
        
        # Log to database asynchronously — failure here is non-fatal
        if db is not None and workspace_id:
            try:
                from app.models.enterprise import AIExecution
                model_name = getattr(llm, "model_name", None) or getattr(llm, "model", "unknown")
                record = AIExecution(
                    workspace_id=workspace_id,
                    job_id=job_id,
                    model_name=str(model_name),
                    tokens_prompt=tokens_prompt,
                    tokens_completion=tokens_completion,
                )
                db.add(record)
                await db.flush()
                logger.debug(
                    "[AI Exec] model=%s workspace=%s tokens_in=%s tokens_out=%s latency=%.0fms",
                    model_name, workspace_id, tokens_prompt, tokens_completion, elapsed_ms
                )
            except Exception as log_err:
                logger.warning("[AI Exec] Could not persist AIExecution record: %s", log_err)
    
    return result
