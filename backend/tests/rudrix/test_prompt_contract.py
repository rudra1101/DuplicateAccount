import re

from app.ai.prompts import IDENTITY_OPERATIONS_INSTRUCTIONS


def normalized_prompt() -> str:
    return " ".join(IDENTITY_OPERATIONS_INSTRUCTIONS.lower().split())


def test_prompt_identifies_assistant_as_rudrix():
    assert "rudrix" in normalized_prompt()


def test_prompt_is_goal_driven_not_phrase_routed():
    prompt = normalized_prompt()
    assert "user's goal" in prompt
    assert "hard-coded phrases" in prompt
    assert "capability schemas" in prompt


def test_prompt_requires_grounding_for_substantive_identityai_answers():
    prompt = normalized_prompt()
    assert "every substantive identityai answer must be grounded" in prompt
    assert "live identityai capabilities" in prompt
    assert "built-in identityai product knowledge" in prompt
    assert "uploaded knowledge/rag" in prompt


def test_prompt_requires_live_capabilities_for_live_product_state():
    prompt = normalized_prompt()
    assert "current records" in prompt
    assert "never answer current-state questions from model memory alone" in prompt
    assert "successful capability results as authoritative" in prompt


def test_prompt_has_product_rag_and_hybrid_rules_without_naming_specific_tools():
    prompt = normalized_prompt()
    assert "built-in identityai product knowledge" in prompt
    assert "organization-specific policies" in prompt
    assert "combine product knowledge, uploaded knowledge, and live capabilities" in prompt


def test_prompt_requires_grounded_state_reuse():
    prompt = normalized_prompt()
    assert "grounded structured conversation state" in prompt
    assert "internal ids" in prompt
    assert "unambiguous" in prompt


def test_prompt_requires_agentic_multi_step_behavior():
    prompt = normalized_prompt()
    assert "use another appropriate capability" in prompt
    assert "continue across multiple steps" in prompt
    assert "available search/resolution capability" in prompt


def test_prompt_enforces_rbac_and_action_safety():
    prompt = normalized_prompt()
    assert "respect rbac" in prompt
    assert "state-changing or external actions require explicit user intent" in prompt
    assert "destructive actions" in prompt


def test_prompt_distinguishes_failure_from_empty_data():
    prompt = normalized_prompt()
    assert "a failed data operation is not an empty result" in prompt
    assert "do not claim that data is unavailable until an appropriate capability has actually been attempted" in prompt
    assert "0 results" in prompt


def test_prompt_forbids_internal_capability_and_json_leakage():
    prompt = normalized_prompt()
    assert "raw json" in prompt
    assert "tool names" in prompt or "internal" in prompt
    assert "return only the final user-facing answer" in prompt


def test_prompt_does_not_hardcode_domain_tool_names():
    prompt = normalized_prompt()
    for tool_name in (
        "get_dashboard_summary",
        "search_duplicate_groups",
        "investigate_accounts",
        "search_orphan_accounts",
        "generate_report",
        "create_remediation_ticket",
        "search_knowledge_base",
    ):
        assert tool_name not in prompt


def test_prompt_does_not_hardcode_a_live_duplicate_count():
    match = re.search(
        r"there are\s+\d+\s+duplicate accounts across all current integrations",
        IDENTITY_OPERATIONS_INSTRUCTIONS,
        flags=re.IGNORECASE,
    )
    assert match is None
