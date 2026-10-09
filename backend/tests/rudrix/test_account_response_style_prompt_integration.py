from app.ai.prompts import IDENTITY_OPERATIONS_INSTRUCTIONS


def test_user_facing_response_policy_is_generic():
    prompt = IDENTITY_OPERATIONS_INSTRUCTIONS.lower()

    assert "return only the final user-facing answer" in prompt
    assert "do not expose tool names" in prompt
    assert "raw json" in prompt
    assert "do not narrate the mechanics of calling tools" in prompt
