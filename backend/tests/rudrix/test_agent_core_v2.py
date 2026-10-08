from __future__ import annotations

from app.ai.agent_core.history_state import hydrate_state_from_history
from app.ai.agent_core.models import AgentEntity, AgentState, EntityType
from app.ai.agent_core.planner import parse_capability_plan
from app.ai.fast_agent_service import _initial_agent_state, _is_fast_path_selection
from app.ai.tools import create_ai_tool_registry
from app.ai.agent_core.capabilities import CapabilityCatalog
from app.schemas.chat import ChatHistoryMessage


def test_planner_accepts_only_authorized_known_capabilities():
    plan = parse_capability_plan(
        '{"goal":"confirm duplicate","capabilities":["get_review_statistics","made_up_tool","get_review_statistics"],"needsClarification":false}',
        {"get_review_statistics", "search_duplicate_groups"},
    )

    assert plan.capabilities == ("get_review_statistics",)
    assert plan.goal == "confirm duplicate"
    assert plan.needs_clarification is False


def test_planner_recovers_json_from_model_wrapping_text():
    plan = parse_capability_plan(
        'Plan:\n```json\n{"goal":"find account","capabilities":["investigate_accounts"],"needsClarification":false}\n```',
        {"investigate_accounts"},
    )

    assert plan.capabilities == ("investigate_accounts",)


def test_history_hydrates_duplicate_candidate_state_from_grounded_response():
    history = [
        ChatHistoryMessage(
            role="assistant",
            content=(
                "**Aditya Sinha has current duplicate candidate(s).**\n"
                "Application: Active Directory\n"
                "Primary account: asinha.legacy\n"
                "Employee ID: W00003\n"
                "Duplicate Group ID: 2477\n"
                "Highest Confidence: 97%\n\n"
                "Candidates:\n\n"
                "- **asinha** — candidate ID 9694, 97% confidence"
            ),
        )
    ]

    state = hydrate_state_from_history(history)

    assert state.current_account is not None
    assert state.current_account.entity_type == EntityType.SOURCE_ACCOUNT
    assert state.current_account.attributes["employeeId"] == "W00003"
    assert state.current_duplicate_group is not None
    assert state.current_duplicate_group.id == 2477
    assert state.current_duplicate_candidate is not None
    assert state.current_duplicate_candidate.id == 9694
    assert state.current_duplicate_candidate.label == "asinha"


def test_history_does_not_treat_user_text_as_grounded_state():
    history = [
        ChatHistoryMessage(
            role="user",
            content="Duplicate Group ID: 9999\n- **fake** — candidate ID 1234, 99% confidence",
        )
    ]

    state = hydrate_state_from_history(history)

    assert state.current_duplicate_group is None
    assert state.current_duplicate_candidate is None


def test_persisted_agent_state_wins_over_reconstructed_history():
    persisted = AgentState(
        current_account=AgentEntity(
            entity_type=EntityType.SOURCE_ACCOUNT,
            id=203,
            label="Aditya Sinha",
            attributes={"employeeId": "W00003", "username": "asinha.legacy"},
            source="search_duplicate_groups",
        ),
        current_duplicate_group=AgentEntity(
            entity_type=EntityType.DUPLICATE_GROUP,
            id=2477,
            label="asinha.legacy",
            attributes={"highestConfidence": 97},
            source="search_duplicate_groups",
        ),
        current_duplicate_candidate=AgentEntity(
            entity_type=EntityType.DUPLICATE_CANDIDATE,
            id=9694,
            label="asinha",
            attributes={"groupId": 2477, "confidence": 97},
            source="search_duplicate_groups",
        ),
    ).model_dump(exclude_none=True)

    conflicting_history = [
        ChatHistoryMessage(
            role="assistant",
            content=(
                "Employee ID: WRONG01\n"
                "Duplicate Group ID: 9999\n"
                "- **wrong** — candidate ID 8888, 99% confidence"
            ),
        )
    ]

    state = _initial_agent_state(
        persisted_state=persisted,
        history=conflicting_history,
    )

    assert state.current_account is not None
    assert state.current_account.id == 203
    assert state.current_account.attributes["employeeId"] == "W00003"
    assert state.current_duplicate_group is not None
    assert state.current_duplicate_group.id == 2477
    assert state.current_duplicate_candidate is not None
    assert state.current_duplicate_candidate.id == 9694


def test_invalid_persisted_agent_state_falls_back_to_grounded_history():
    history = [
        ChatHistoryMessage(
            role="assistant",
            content=(
                "Employee ID: W00003\n"
                "Duplicate Group ID: 2477\n"
                "- **asinha** — candidate ID 9694, 97% confidence"
            ),
        )
    ]

    state = _initial_agent_state(
        persisted_state={"current_account": "invalid"},
        history=history,
    )

    assert state.current_account is not None
    assert state.current_account.attributes["employeeId"] == "W00003"
    assert state.current_duplicate_candidate is not None
    assert state.current_duplicate_candidate.id == 9694


def test_single_fast_capability_uses_low_latency_path():
    registry = create_ai_tool_registry()
    catalog = CapabilityCatalog(registry)
    definitions = [
        definition
        for definition in registry.definitions()
        if definition["name"] == "investigate_accounts"
    ]

    assert _is_fast_path_selection(definitions, catalog) is True


def test_write_capability_is_not_treated_as_fast_path():
    registry = create_ai_tool_registry()
    catalog = CapabilityCatalog(registry)
    definitions = [
        definition
        for definition in registry.definitions()
        if definition["name"] == "generate_report"
    ]

    assert _is_fast_path_selection(definitions, catalog) is False
