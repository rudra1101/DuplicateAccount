from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class ProviderResponse:
    text: str
    assistant_message: dict[str, Any]
    tool_calls: list[ProviderToolCall] = field(
        default_factory=list
    )
    model: str = ""


class BaseAIProvider(ABC):
    @abstractmethod
    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ProviderResponse:
        raise NotImplementedError

    @abstractmethod
    def embed(
        self,
        *,
        model: str,
        inputs: list[str],
    ) -> list[list[float]]:
        raise NotImplementedError