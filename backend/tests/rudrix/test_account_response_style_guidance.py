from app.ai.prompts.account_response_style_guidance import ACCOUNT_RESPONSE_STYLE_GUIDANCE


def test_account_response_guidance_forbids_internal_meta_commentary():
    guidance = ACCOUNT_RESPONSE_STYLE_GUIDANCE.lower()

    assert "based on the tool call response" in guidance
    assert "original user question" in guidance
    assert "only the user-facing answer" in guidance
    assert "do not invent missing values" in guidance
