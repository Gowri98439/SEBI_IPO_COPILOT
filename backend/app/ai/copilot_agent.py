"""
LangChain ReAct agent for the IPO Copilot conversational interface.
Streams token-by-token responses via async generator for SSE delivery.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator

from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_core.tools import Tool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from app.ai.llm_client import get_llm, get_creative_llm
from app.ai.prompts import (
    COPILOT_SYSTEM,
    REACT_AGENT_SYSTEM,
    SECTION_DRAFTER_SYSTEM,
    SECTION_DRAFTER_TEMPLATE,
)
from app.ai.rag_pipeline import query_sebi_regulations, rag_query_full

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


async def search_sebi_rules_async(query: str) -> str:
    """
    Search SEBI regulations for relevant rules.
    Input: a search query string.
    """
    try:
        docs = await query_sebi_regulations(query, top_k=5)
        if not docs:
            return "No relevant SEBI regulations found for the given query."
        parts = []
        for doc in docs:
            reg_id = doc.get("regulation_id", "N/A")
            section = doc.get("section", "")
            parts.append(f"[{reg_id} — {section}]\n{doc['content'][:600]}")
        return "\n\n---\n\n".join(parts)
    except Exception as exc:
        logger.error("search_sebi_rules tool failed: %s", exc, exc_info=True)
        return f"Error searching SEBI regulations: {exc}"


def search_sebi_rules(query: str) -> str:
    return "Error: sync execution not supported in async agent"


def get_compliance_summary(workspace_id: str) -> str:
    """
    Get current compliance status summary for the workspace.
    """
    try:
        from app.ai.compliance_engine import SEBI_SME_CHECKLIST

        checklist_summary = []
        for item in SEBI_SME_CHECKLIST[:5]:
            checklist_summary.append(f"- [{item['id']}] {item['name']} ({item['category']})")

        return (
            f"Workspace ID: {workspace_id}\n"
            f"SEBI SME IPO Checklist has {len(SEBI_SME_CHECKLIST)} compliance checks.\n"
            f"Key checks include:\n" + "\n".join(checklist_summary) +
            f"\n\nTo run a full compliance check, use the 'Run Compliance Checks' feature in the workspace dashboard."
        )
    except Exception as exc:
        logger.error("get_compliance_summary tool failed: %s", exc, exc_info=True)
        return f"Could not retrieve compliance summary: {exc}"


async def get_compliance_summary_async(workspace_id: str) -> str:
    return get_compliance_summary(workspace_id)


def _build_draft_section_content_async(workspace_id: str):
    async def draft_section_content_async(section_and_context: str) -> str:
        """
        Draft a section of the IPO offer document.
        Input format: 'section_name' OR 'section_name|company_context'
        """
        try:
            parts = section_and_context.split("|", 1)
            section_name = parts[0].strip()
            company_context = parts[1].strip() if len(parts) > 1 else "No specific company context provided."

            from app.ai.rag_pipeline import query_sebi_regulations, query_workspace_documents

            # Pull SEBI regulatory context
            rag_docs = await query_sebi_regulations(
                f"IPO offer document {section_name} section requirements SEBI ICDR",
                top_k=4,
            )
            rag_context = "\n\n".join(
                f"[{d.get('regulation_id', 'N/A')}]\n{d['content'][:500]}"
                for d in rag_docs
            ) if rag_docs else "General SEBI ICDR requirements apply."

            prompt_text = SECTION_DRAFTER_TEMPLATE.format(
                section_name=section_name,
                rag_context=rag_context,
                company_context=company_context,
            )
            llm = get_creative_llm()
            parser = StrOutputParser()
            messages = [
                SystemMessage(content=SECTION_DRAFTER_SYSTEM),
                HumanMessage(content=prompt_text),
            ]
            chain = llm | parser
            return await chain.ainvoke(messages)
        except Exception as exc:
            logger.error("draft_section_content tool failed: %s", exc, exc_info=True)
            return f"Error drafting section '{section_and_context}': {exc}"
    return draft_section_content_async

def draft_section_content(section_and_context: str) -> str:
    return "Error: sync execution not supported in async agent"


def _build_search_workspace_documents_async(workspace_id: str):
    async def search_workspace_documents_async(query: str) -> str:
        """
        Search the user's uploaded documents for evidence.
        Input format: a natural language search query string.
        """
        try:
            query = query.strip()
            from app.ai.rag_pipeline import query_workspace_documents
            docs = await query_workspace_documents(query, workspace_id=workspace_id, top_k=5)
            if not docs:
                return f"No relevant information found in workspace documents for '{query}'."
            out_parts = []
            for doc in docs:
                filename = doc.get("filename", "Unknown File")
                page = doc.get("page", "?")
                out_parts.append(f"[File: {filename}, Page: {page}]\n{doc['content'][:600]}")
            return "\n\n---\n\n".join(out_parts)
        except Exception as exc:
            logger.error("search_workspace_documents tool failed: %s", exc, exc_info=True)
            return f"Error searching workspace documents: {exc}"
    return search_workspace_documents_async

def search_workspace_documents(query: str) -> str:
    return "Error: sync execution not supported in async agent"


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

def get_copilot_tools(workspace_id: str) -> list[Tool]:
    return [
        Tool(
            name="search_workspace_documents",
            func=search_workspace_documents,
            coroutine=_build_search_workspace_documents_async(workspace_id),
            description=(
                "Search the user's uploaded documents (like draft IPO offer documents, financials) for evidence. "
                "ALWAYS use this tool first when analyzing the user's company or documents. "
                "Input format: 'search query'"
            ),
        ),
        Tool(
            name="search_sebi_rules",
            func=search_sebi_rules,
            coroutine=search_sebi_rules_async,
            description=(
                "Search the SEBI regulations database for relevant rules, guidelines, and requirements. "
                "Use this when the user asks about specific SEBI regulations, compliance requirements, "
                "or any regulatory questions. Input should be a natural language search query."
            ),
        ),
        Tool(
            name="get_compliance_summary",
            func=lambda q: get_compliance_summary(workspace_id),
            coroutine=lambda q: get_compliance_summary_async(workspace_id),
            description=(
                "Get the compliance check status summary for the current workspace. "
                "Use this when the user asks about their current compliance status or progress. "
                "Input can be anything (e.g. 'status')."
            ),
        ),
        Tool(
            name="draft_section_content",
            func=draft_section_content,
            coroutine=_build_draft_section_content_async(workspace_id),
            description=(
                "Draft a specific section of the IPO offer document. "
                "Use this when the user wants help writing or drafting a particular section. "
                "Input format: 'section_name' or 'section_name|company_context'."
            ),
        ),
    ]

# ---------------------------------------------------------------------------
# Simple conversational chain (fallback for when agent is not needed)
# ---------------------------------------------------------------------------


async def run_simple_copilot(
    user_message: str,
    session_history: list[dict],
) -> AsyncGenerator[str, None]:
    """
    Run a simple conversational LLM chain with session history.
    Streams response tokens. Does NOT use agent tools.
    """
    llm = get_llm(temperature=0.1)
    messages = [SystemMessage(content=COPILOT_SYSTEM)]

    # Add session history (last 10 turns to manage context)
    for turn in session_history[-10:]:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))  # type: ignore
        elif role == "assistant":
            messages.append(AIMessage(content=content))  # type: ignore

    messages.append(HumanMessage(content=user_message))  # type: ignore

    async for chunk in llm.astream(messages):
        if chunk.content:
            yield chunk.content


# ---------------------------------------------------------------------------
# ReAct agent runner with streaming
# ---------------------------------------------------------------------------


async def run_copilot_agent(
    user_message: str,
    session_history: list[dict],
    workspace_id: str,
) -> AsyncGenerator[str, None]:
    """
    Run the ReAct agent and stream response tokens via async generator.
    Falls back to simple chain if agent setup fails.

    Args:
        user_message: The current user message.
        session_history: List of {'role': 'user'|'assistant', 'content': str} dicts.
        workspace_id: The active workspace identifier.

    Yields:
        String chunks suitable for SSE streaming.
    """
    # Build context from recent history for the agent
    history_context = ""
    if session_history:
        recent = session_history[-6:]  # last 3 turns
        parts = []
        for turn in recent:
            role = turn.get("role", "user").capitalize()
            content = turn.get("content", "")[:300]
            parts.append(f"{role}: {content}")
        history_context = "\nRecent conversation:\n" + "\n".join(parts) + "\n\n"

    # Determine if we need the agent (tool-requiring queries) or simple chain
    needs_agent = _requires_agent_tools(user_message)

    if needs_agent:
        logger.info("Using ReAct agent for message: %s...", user_message[:80])
        try:
            async for chunk in _run_react_agent(user_message, history_context, workspace_id):
                yield chunk
        except Exception as exc:
            logger.error("ReAct agent failed, falling back to simple chain: %s", exc, exc_info=True)
            yield "I encountered an issue with tool execution. Let me answer directly:\n\n"
            async for chunk in run_simple_copilot(user_message, session_history):
                yield chunk
    else:
        logger.info("Using simple chain for message: %s...", user_message[:80])
        async for chunk in run_simple_copilot(user_message, session_history):
            yield chunk


def _requires_agent_tools(message: str) -> bool:
    """Heuristic: determine if this message needs the ReAct agent with tools."""
    tool_trigger_keywords = [
        "regulation", "sebi rule", "icdr", "lodr", "compliance check",
        "draft", "write the section", "write the chapter", "generate the",
        "what does regulation", "what is the requirement", "check compliance",
        "search for", "find the rule", "look up",
    ]
    message_lower = message.lower()
    return any(kw in message_lower for kw in tool_trigger_keywords)


async def _run_react_agent(
    user_message: str,
    history_context: str,
    workspace_id: str,
) -> AsyncGenerator[str, None]:
    """Internal: execute the LangChain ReAct agent and stream output."""
    llm = get_llm(temperature=0.1)

    # Build the ReAct prompt template
    prompt = PromptTemplate.from_template(REACT_AGENT_SYSTEM)

    agent = create_react_agent(
        llm=llm,
        tools=get_copilot_tools(workspace_id),
        prompt=prompt,
    )

    agent_executor = AgentExecutor(
        agent=agent,
        tools=get_copilot_tools(workspace_id),
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5,
        max_execution_time=120,
    )

    enriched_input = f"{history_context}Current workspace: {workspace_id}\n\nUser question: {user_message}"

    # Stream intermediate steps and final answer
    yielded_anything = False
    in_final_answer = False
    buffer = ""
    async for event in agent_executor.astream_events(
        {"input": enriched_input},
        version="v2",
    ):
        event_type = event.get("event", "")
        if event_type == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                content = chunk.content
                if in_final_answer:
                    yield content
                    yielded_anything = True
                else:
                    buffer += content
                    if "Final Answer:" in buffer:
                        in_final_answer = True
                        idx = buffer.find("Final Answer:") + len("Final Answer:")
                        to_yield = buffer[idx:].lstrip()
                        if to_yield:
                            yield to_yield
                            yielded_anything = True
        elif event_type == "on_tool_start":
            tool_name = event.get("name", "")
            # We can still yield a status message that the frontend could parse or show
            # But the user asked for clean bullet points, so maybe we skip this or format it nicely.
            # yield f"\n\n🔍 *Searching {tool_name}...*\n\n"
            pass
        elif event_type == "on_tool_end":
            pass  # Tool result will be incorporated into the final answer

    if not yielded_anything:
        # Fallback: call ainvoke and return full result
        result = await agent_executor.ainvoke({"input": enriched_input})
        output = result.get("output", "I could not generate a response. Please try again.")
        yield output
