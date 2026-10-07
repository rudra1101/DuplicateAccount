from app.ai.prompts import IDENTITY_OPERATIONS_INSTRUCTIONS


def test_account_response_style_is_in_rudrix_system_prompt():
    prompt = IDENTITY_OPERATIONS_INSTRUCTIONS.lower()

    assert "account lookup response output" in prompt
    assert "based on the tool call response" in prompt
    assert "the response must contain only the user-facing answer" in prompt
