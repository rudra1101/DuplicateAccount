from typing import Any

from ollama import Client
from ollama import ResponseError

from app.ai.config import AISettings
from app.ai.providers.base import (
    BaseAIProvider,
    ProviderResponse,
    ProviderToolCall,
)


class OllamaProvider(BaseAIProvider):
    def __init__(
        self,
        settings: AISettings,
    ) -> None:
        self._client = Client(
            host=settings.ollama_base_url
        )

    @staticmethod
    def _normalize_tools(
        tools: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        normalized_tools: list[
            dict[str, Any]
        ] = []

        for tool in tools:
            if "function" in tool:
                normalized_tools.append(
                    tool
                )
                continue

            normalized_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get(
                            "description",
                            "",
                        ),
                        "parameters": tool.get(
                            "parameters",
                            {
                                "type": "object",
                                "properties": {},
                                "required": [],
                            },
                        ),
                    },
                }
            )

        return normalized_tools

    @staticmethod
    def _message_to_dict(
        message: Any,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "role": (
                getattr(
                    message,
                    "role",
                    None,
                )
                or "assistant"
            ),
            "content": (
                getattr(
                    message,
                    "content",
                    None,
                )
                or ""
            ),
        }

        raw_tool_calls = getattr(
            message,
            "tool_calls",
            None,
        )

        if raw_tool_calls:
            result["tool_calls"] = []

            for call in raw_tool_calls:
                function = call.function

                result["tool_calls"].append(
                    {
                        "type": "function",
                        "function": {
                            "name": function.name,
                            "arguments": dict(
                                function.arguments
                                or {}
                            ),
                        },
                    }
                )

        return result

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ProviderResponse:
        try:
            response = self._client.chat(
                model=model,
                messages=messages,
                tools=self._normalize_tools(
                    tools
                ),
                stream=False,
            )
        except ResponseError as exc:
            raise RuntimeError(
                "Ollama chat request failed: "
                f"{exc.error}"
            ) from exc
        except ConnectionError as exc:
            raise RuntimeError(
                "Unable to connect to Ollama. "
                "Confirm Ollama is running on "
                "http://127.0.0.1:11434."
            ) from exc

        message = response.message

        tool_calls: list[
            ProviderToolCall
        ] = []

        for call in (
            message.tool_calls or []
        ):
            tool_calls.append(
                ProviderToolCall(
                    name=call.function.name,
                    arguments=dict(
                        call.function.arguments
                        or {}
                    ),
                )
            )

        return ProviderResponse(
            text=message.content or "",
            assistant_message=(
                self._message_to_dict(
                    message
                )
            ),
            tool_calls=tool_calls,
            model=model,
        )

    def embed(
        self,
        *,
        model: str,
        inputs: list[str],
    ) -> list[list[float]]:
        if not inputs:
            return []

        try:
            response = self._client.embed(
                model=model,
                input=inputs,
            )
        except ResponseError as exc:
            raise RuntimeError(
                "Ollama embedding request failed: "
                f"{exc.error}"
            ) from exc
        except ConnectionError as exc:
            raise RuntimeError(
                "Unable to connect to Ollama."
            ) from exc

        return [
            list(embedding)
            for embedding in response.embeddings
        ]