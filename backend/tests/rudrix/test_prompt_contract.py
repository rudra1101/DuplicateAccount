\
import re
from app.ai.prompts import IDENTITY_OPERATIONS_INSTRUCTIONS

def normalized_prompt() -> str:
    return " ".join(IDENTITY_OPERATIONS_INSTRUCTIONS.lower().split())

def test_prompt_identifies_assistant_as_rudrix():
    assert "rudrix" in normalized_prompt()

def test_prompt_routes_system_duplicate_count_to_dashboard_summary():
    prompt = normalized_prompt()
    assert "get_dashboard_summary" in prompt
    assert "duplicate accounts" in prompt
    assert "summary.duplicateaccounts" in prompt

def test_prompt_keeps_candidate_confidence_separate_from_group_confidence():
    prompt = normalized_prompt()
    assert "get_confidence_breakdown" in prompt
    assert "duplicate candidate account" in prompt
    assert "search_duplicate_groups" in prompt
    assert "highest-confidence" in prompt or "highest confidence" in prompt

def test_prompt_preserves_gt_vs_gte_semantics():
    prompt = normalized_prompt()
    assert 'operator = "gt"' in prompt or 'operator="gt"' in prompt
    assert 'operator = "gte"' in prompt or 'operator="gte"' in prompt

def test_prompt_preserves_follow_up_threshold_context():
    prompt = normalized_prompt()
    assert "follow-up" in prompt or "follow up" in prompt
    assert "application-wise" in prompt or "application wise" in prompt

def test_prompt_has_rag_and_hybrid_rules():
    prompt = normalized_prompt()
    assert "search_knowledge_base" in prompt
    assert "list_knowledge_documents" in prompt
    assert "current system data" in prompt
    assert "policy guidance" in prompt

def test_prompt_forbids_internal_tool_and_json_leakage():
    prompt = normalized_prompt()
    assert "raw json" in prompt
    assert "tool names" in prompt or "internal tool names" in prompt
    assert "return only the final user-facing answer" in prompt

def test_prompt_does_not_hardcode_a_live_duplicate_count():
    match = re.search(
        r"there are\s+\d+\s+duplicate accounts across all current integrations",
        IDENTITY_OPERATIONS_INSTRUCTIONS,
        flags=re.IGNORECASE,
    )
    assert match is None, (
        "Remove hard-coded live duplicate counts from the system prompt. "
        "Use a placeholder such as <count> instead."
    )
