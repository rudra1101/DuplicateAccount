from app.ai.agent_core.models import AgentState
from app.ai.agent_core.persistence import (
    agent_state_system_message,
    dump_agent_state,
    load_agent_state,
    reduce_tool_history,
)
from app.schemas.chat import ToolInvocationResponse


def test_invalid_persisted_state_falls_back_to_empty_state():
    assert load_agent_state(None) == AgentState()
    assert load_agent_state(["bad"]) == AgentState()
    assert load_agent_state({"current_account": {"entity_type": "BAD"}}) == AgentState()


def test_tool_history_builds_durable_duplicate_context():
    tools = [
        ToolInvocationResponse(
            name="search_duplicate_groups",
            arguments={"search": "W00003"},
            result={
                "success": True,
                "data": {
                    "groups": [
                        {
                            "groupId": 2477,
                            "application": "Active Directory",
                            "primaryUsername": "asinha.legacy",
                            "highestConfidence": 97,
                            "duplicateCount": 1,
                            "primaryAccount": {
                                "sourceAccountId": 203,
                                "username": "asinha.legacy",
                                "displayName": "Aditya Sinha",
                                "employeeId": "W00003",
                            },
                            "candidates": [
                                {
                                    "id": 9694,
                                    "username": "asinha",
                                    "confidence": 97,
                                }
                            ],
                        }
                    ]
                },
            },
        )
    ]

    state = reduce_tool_history(AgentState(), tools)
    persisted = dump_agent_state(state)
    restored = load_agent_state(persisted)

    assert restored.current_account is not None
    assert restored.current_account.attributes["employeeId"] == "W00003"
    assert restored.current_duplicate_group is not None
    assert restored.current_duplicate_group.id == 2477
    assert restored.current_duplicate_candidate is not None
    assert restored.current_duplicate_candidate.id == 9694


def test_grounded_state_message_contains_entity_ids_not_chat_prose():
    state = reduce_tool_history(
        AgentState(),
        [
            ToolInvocationResponse(
                name="search_duplicate_groups",
                arguments={"search": "W00003"},
                result={
                    "success": True,
                    "data": {
                        "groups": [
                            {
                                "groupId": 2477,
                                "primaryUsername": "asinha.legacy",
                                "candidates": [
                                    {
                                        "id": 9694,
                                        "username": "asinha",
                                        "confidence": 97,
                                    }
                                ],
                            }
                        ]
                    },
                },
            )
        ],
    )

    message = agent_state_system_message(state)
    assert message is not None
    assert message["role"] == "system"
    assert "2477" in message["content"]
    assert "9694" in message["content"]
    assert "Do not invent missing values" in message["content"]
