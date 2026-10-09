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
    assert "tool schemas and descriptions define what identityai can do" in prompt


def test_prompt_requires_live_tools_for_live_product_state():
    prompt = normalized_prompt()
    assert "use live identityai tools" in prompt
    assert "current product data" in prompt
    assert "successful tool results as authoritative" in prompt


def test_prompt_has_rag_and_hybrid_rules_without_naming_specific_tools():
    prompt = normalized_prompt()
    assert "knowledge/rag tools" in prompt
    assert "combine live tools and knowledge tools" in prompt
    assert "uploaded documentation" in prompt


def test_prompt_requires_grounded_state_reuse():
    prompt = normalized_prompt()
    assert "grounded structured conversation state" in prompt
    assert "internal ids" in prompt
    assert "unambiguous" in prompt


def test_prompt_requires_multi_tool_agent_loop():
    prompt = normalized_prompt()
    assert "multiple tools in one turn" in prompt
    assert "after each tool result" in prompt
    assert "another tool is required" in prompt


def test_prompt_enforces_rbac_and_action_safety():
    prompt = normalized_prompt()
    assert "respect rbac" in prompt
    assert "state-changing or external actions require explicit user intent" in prompt
    assert "destructive actions" in prompt


def test_prompt_forbids_internal_tool_and_json_leakage():
    prompt = normalized_prompt()
    assert "raw json" in prompt
    assert "tool names" in prompt or "internal tool names" in prompt
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
