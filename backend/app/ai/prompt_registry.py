"""
Prompt Registry
Centralized storage for all prompts.
"""
from app.ai.prompts import (
    COMPLIANCE_CHECK_SYSTEM,
    COMPLIANCE_CHECK_WITH_CONTEXT_TEMPLATE,
    DRAFT_REVIEW_SYSTEM,
    DRAFT_REVIEW_TEMPLATE,
    DOCUMENT_VALIDATOR_SYSTEM,
    DOCUMENT_VALIDATION_WITH_CONTEXT_TEMPLATE,
    SEBI_EXPERT_SYSTEM,
    SEBI_QUERY_WITH_CONTEXT_TEMPLATE,
    COPILOT_SYSTEM_PROMPT,
)

# This acts as an abstraction to easily fetch prompts by name.
PROMPTS = {
    "compliance_system": COMPLIANCE_CHECK_SYSTEM,
    "compliance_template": COMPLIANCE_CHECK_WITH_CONTEXT_TEMPLATE,
    "draft_system": DRAFT_REVIEW_SYSTEM,
    "draft_template": DRAFT_REVIEW_TEMPLATE,
    "validator_system": DOCUMENT_VALIDATOR_SYSTEM,
    "validator_template": DOCUMENT_VALIDATION_WITH_CONTEXT_TEMPLATE,
    "sebi_expert_system": SEBI_EXPERT_SYSTEM,
    "sebi_expert_template": SEBI_QUERY_WITH_CONTEXT_TEMPLATE,
    "copilot_system": COPILOT_SYSTEM_PROMPT,
}

def get_prompt(prompt_name: str) -> str:
    if prompt_name not in PROMPTS:
        raise KeyError(f"Prompt {prompt_name} not found in registry.")
    return PROMPTS[prompt_name]
