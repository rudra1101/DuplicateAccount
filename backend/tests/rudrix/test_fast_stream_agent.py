from __future__ import annotations

from types import SimpleNamespace

from app.ai.providers.base import ProviderResponse
from app.schemas.chat import ChatRequest


class _FakeProvider:
    def __init__(self) -> None:
        self.stream_calls = 0
        self.blocking_calls = 0

    def stream_chat(self, *, model, messages, tools):
        self.stream_calls += 1
        yield {"type": "delta", "text": "Fast answer"}
        yield {
            "type": "result",
            "response": ProviderResponse(
                text="Fast answer",
                assistant_message={"role": "assistant", "content": "Fast answer"},
                tool_calls=[],
                model=model,
            ),
        }

    def chat(self, *, model, messages, tools):
        self.blocking_calls += 1
        raise AssertionError("Blocking provider.chat must not run on the streaming fast path")


class _FakeRegistry:
    def definitions(self):
        return []


def test_plain_chat_uses_one_streaming_model_call(monkeypatch):
    import app.ai.fast_agent_service as fast_agent

    provider = _FakeProvider()

    monkeypatch.setattr(
        fast_agent,
        "get_ai_settings",
        lambda: SimpleNamespace(
            fast_model="fast-model",
            reasoning_model="reasoning-model",
            max_tool_iterations=4,
        ),
    )
    monkeypatch.setattr(
        fast_agent.AIProviderFactory,
        "create",
        lambda settings: provider,
    )
    monkeypatch.setattr(
        fast_agent,
        "create_ai_tool_registry",
        lambda: _FakeRegistry(),
    )

    events = list(
        fast_agent.run_identity_agent_stream_fast(
            db=object(),
            request=ChatRequest(message="Explain duplicate matching"),
        )
    )

    deltas = [event["text"] for event in events if event.get("type") == "delta"]
    done = [event for event in events if event.get("type") == "done"]

    assert deltas == ["Fast answer"]
    assert len(done) == 1
    assert done[0]["response"].message == "Fast answer"
    assert provider.stream_calls == 1
    assert provider.blocking_calls == 0
