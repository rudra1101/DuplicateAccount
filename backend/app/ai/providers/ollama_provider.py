import json
import re
from collections.abc import Iterator
from typing import Any

from ollama import Client
from ollama import ResponseError

from app.ai.config import AISettings
from app.ai.providers.base import (
    BaseAIProvider,
    ProviderResponse,
    ProviderToolCall,
)


class OllamaProvider(
    BaseAIProvider
):
    def __init__(
        self,
        settings: AISettings,
    ) -> None:
        self._client = Client(
            host=(
                settings
                .ollama_base_url
            )
        )

    @staticmethod
    def _normalize_tools(
        tools: list[
            dict[str, Any]
        ],
    ) -> list[
        dict[str, Any]
    ]:
        normalized_tools: list[
            dict[str, Any]
        ] = []

        for tool in tools:
            if (
                "function"
                in tool
            ):
                normalized_tools.append(
                    tool
                )
                continue

            normalized_tools.append(
                {
                    "type":
                        "function",
                    "function": {
                        "name":
                            tool["name"],
                        "description":
                            tool.get(
                                "description",
                                "",
                            ),
                        "parameters":
                            tool.get(
                                "parameters",
                                {
                                    "type":
                                        "object",
                                    "properties":
                                        {},
                                    "required":
                                        [],
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
        result: dict[
            str,
            Any,
        ] = {
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
            result[
                "tool_calls"
            ] = []

            for call in raw_tool_calls:
                function = (
                    call.function
                )

                result[
                    "tool_calls"
                ].append(
                    {
                        "type":
                            "function",
                        "function": {
                            "name":
                                function.name,
                            "arguments":
                                dict(
                                    function
                                    .arguments
                                    or {}
                                ),
                        },
                    }
                )

        return result

    @staticmethod
    def _extract_json_block(
        text: str,
    ) -> dict[
        str,
        Any,
    ] | None:
        value = text.strip()

        if not value:
            return None

        fence_match = re.fullmatch(
            r"\s*```(?:json)?\s*"
            r"(\{.*\})"
            r"\s*```\s*",
            value,
            flags=(
                re.DOTALL
                | re.IGNORECASE
            ),
        )

        if fence_match:
            value = (
                fence_match
                .group(1)
                .strip()
            )

        if not (
            value.startswith(
                "{"
            )
            and value.endswith(
                "}"
            )
        ):
            return None

        try:
            parsed = json.loads(
                value
            )
        except (
            json.JSONDecodeError,
            TypeError,
        ):
            return None

        if not isinstance(
            parsed,
            dict,
        ):
            return None

        return parsed

    @classmethod
    def _parse_text_tool_call(
        cls,
        *,
        text: str,
        allowed_tool_names:
            set[str],
    ) -> ProviderToolCall | None:
        payload = (
            cls._extract_json_block(
                text
            )
        )

        if payload is None:
            return None

        name: Any = None
        arguments: Any = None

        function_payload = (
            payload.get(
                "function"
            )
        )

        if isinstance(
            function_payload,
            dict,
        ):
            name = (
                function_payload.get(
                    "name"
                )
            )
            arguments = (
                function_payload.get(
                    "arguments",
                    function_payload.get(
                        "parameters",
                        {},
                    ),
                )
            )
        else:
            name = payload.get(
                "name"
            )
            arguments = (
                payload.get(
                    "arguments",
                    payload.get(
                        "parameters",
                        {},
                    ),
                )
            )

        if not isinstance(
            name,
            str,
        ):
            return None

        name = name.strip()

        if (
            name
            not in allowed_tool_names
        ):
            return None

        if arguments is None:
            arguments = {}

        if not isinstance(
            arguments,
            dict,
        ):
            return None

        return ProviderToolCall(
            name=name,
            arguments=dict(
                arguments
            ),
        )

    @staticmethod
    def _allowed_tool_names(
        normalized_tools:
            list[dict[str, Any]],
    ) -> set[str]:
        return {
            str(
                tool[
                    "function"
                ][
                    "name"
                ]
            )
            for tool
            in normalized_tools
            if (
                isinstance(
                    tool.get(
                        "function"
                    ),
                    dict,
                )
                and tool[
                    "function"
                ].get(
                    "name"
                )
            )
        }

    def _build_provider_response(
        self,
        *,
        model: str,
        content: str,
        tool_calls:
            list[ProviderToolCall],
    ) -> ProviderResponse:
        assistant_message: dict[str, Any] = {
                "role":
                    "assistant",
                "content":
                    content,
            }

        if tool_calls:
            assistant_message[
                "content"
            ] = ""

            assistant_message[
                "tool_calls"
            ] = [
                {
                    "type":
                        "function",
                    "function": {
                        "name":
                            call.name,
                        "arguments":
                            call.arguments,
                    },
                }
                for call
                in tool_calls
            ]

            content = ""

        return ProviderResponse(
            text=content,
            assistant_message=
                assistant_message,
            tool_calls=
                tool_calls,
            model=model,
        )

    def chat(
        self,
        *,
        model: str,
        messages: list[
            dict[str, Any]
        ],
        tools: list[
            dict[str, Any]
        ],
    ) -> ProviderResponse:
        normalized_tools = (
            self._normalize_tools(
                tools
            )
        )

        allowed_tool_names = (
            self._allowed_tool_names(
                normalized_tools
            )
        )

        try:
            response = (
                self._client.chat(
                    model=model,
                    messages=messages,
                    tools=
                        normalized_tools,
                    stream=False,
                )
            )
        except ResponseError as exc:
            raise RuntimeError(
                "Ollama chat request "
                "failed: "
                f"{exc.error}"
            ) from exc
        except ConnectionError as exc:
            raise RuntimeError(
                "Unable to connect "
                "to Ollama. Confirm "
                "Ollama is running on "
                "http://127.0.0.1:11434."
            ) from exc

        message = response.message

        tool_calls: list[
            ProviderToolCall
        ] = []

        for call in (
            message.tool_calls
            or []
        ):
            tool_calls.append(
                ProviderToolCall(
                    name=(
                        call.function.name
                    ),
                    arguments=dict(
                        call.function
                        .arguments
                        or {}
                    ),
                )
            )

        text = (
            message.content
            or ""
        )

        if not tool_calls:
            fallback_tool_call = (
                self
                ._parse_text_tool_call(
                    text=text,
                    allowed_tool_names=
                        allowed_tool_names,
                )
            )

            if (
                fallback_tool_call
                is not None
            ):
                tool_calls.append(
                    fallback_tool_call
                )

        return (
            self._build_provider_response(
                model=model,
                content=text,
                tool_calls=
                    tool_calls,
            )
        )

    def stream_chat(
        self,
        *,
        model: str,
        messages: list[
            dict[str, Any]
        ],
        tools: list[
            dict[str, Any]
        ],
    ) -> Iterator[
        dict[str, Any]
    ]:
        """
        True Ollama token streaming.

        Events yielded:
        {"type": "delta", "text": "..."}
        {"type": "result", "response": ProviderResponse}

        Safety:
        - Native tool-call content is never emitted.
        - JSON-looking prefixes are buffered so fallback textual
          tool calls are never shown to the user.
        """
        normalized_tools = (
            self._normalize_tools(
                tools
            )
        )

        allowed_tool_names = (
            self._allowed_tool_names(
                normalized_tools
            )
        )

        try:
            chat_kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "stream": True,
            }

            # For final-answer streaming we intentionally omit the
            # tools argument completely when there are no tools.
            # This avoids Ollama entering its tool-capable streaming
            # path unnecessarily.
            if normalized_tools:
                chat_kwargs[
                    "tools"
                ] = normalized_tools

            stream = (
                self._client.chat(
                    **chat_kwargs
                )
            )
        except ResponseError as exc:
            raise RuntimeError(
                "Ollama chat request "
                "failed: "
                f"{exc.error}"
            ) from exc
        except ConnectionError as exc:
            raise RuntimeError(
                "Unable to connect "
                "to Ollama. Confirm "
                "Ollama is running on "
                "http://127.0.0.1:11434."
            ) from exc

        content_parts: list[
            str
        ] = []

        tool_calls: list[
            ProviderToolCall
        ] = []

        # We delay the first small prefix until we know the response
        # is natural language rather than textual tool-call JSON.
        prefix_buffer = ""
        streaming_enabled = False
        suppress_content = False

        try:
            for chunk in stream:
                message = (
                    chunk.message
                )

                raw_tool_calls = (
                    message.tool_calls
                    or []
                )

                if raw_tool_calls:
                    suppress_content = True

                    for call in (
                        raw_tool_calls
                    ):
                        tool_calls.append(
                            ProviderToolCall(
                                name=(
                                    call
                                    .function
                                    .name
                                ),
                                arguments=dict(
                                    call
                                    .function
                                    .arguments
                                    or {}
                                ),
                            )
                        )

                text = (
                    message.content
                    or ""
                )

                if not text:
                    continue

                content_parts.append(
                    text
                )

                if suppress_content:
                    continue

                if streaming_enabled:
                    yield {
                        "type":
                            "delta",
                        "text":
                            text,
                    }
                    continue

                prefix_buffer += text

                stripped = (
                    prefix_buffer
                    .lstrip()
                )

                # Hold JSON/markdown-code prefixes until completion.
                # These may be fallback tool requests.
                if (
                    stripped.startswith(
                        "{"
                    )
                    or stripped.startswith(
                        "```"
                    )
                ):
                    continue

                # Once we have a clearly natural-language prefix,
                # begin true token streaming.
                if (
                    len(
                        stripped
                    ) >= 8
                    or any(
                        character
                        in stripped
                        for character
                        in (
                            " ",
                            "\n",
                            ".",
                            ":",
                            "-",
                        )
                    )
                ):
                    streaming_enabled = True

                    yield {
                        "type":
                            "delta",
                        "text":
                            prefix_buffer,
                    }

                    prefix_buffer = ""

        finally:
            close_method = getattr(
                stream,
                "close",
                None,
            )

            if callable(
                close_method
            ):
                close_method()

        full_text = "".join(
            content_parts
        )

        if not tool_calls:
            fallback_tool_call = (
                self
                ._parse_text_tool_call(
                    text=full_text,
                    allowed_tool_names=
                        allowed_tool_names,
                )
            )

            if (
                fallback_tool_call
                is not None
            ):
                tool_calls.append(
                    fallback_tool_call
                )
                suppress_content = True

        # If we buffered a short natural answer and it was not a tool call,
        # flush it now.
        if (
            not suppress_content
            and not tool_calls
            and prefix_buffer
        ):
            yield {
                "type":
                    "delta",
                "text":
                    prefix_buffer,
            }

        response = (
            self._build_provider_response(
                model=model,
                content=full_text,
                tool_calls=
                    tool_calls,
            )
        )

        yield {
            "type":
                "result",
            "response":
                response,
        }

    def embed(
        self,
        *,
        model: str,
        inputs: list[
            str
        ],
    ) -> list[
        list[float]
    ]:
        if not inputs:
            return []

        try:
            response = (
                self._client.embed(
                    model=model,
                    input=inputs,
                )
            )
        except ResponseError as exc:
            raise RuntimeError(
                "Ollama embedding request "
                "failed: "
                f"{exc.error}"
            ) from exc
        except ConnectionError as exc:
            raise RuntimeError(
                "Unable to connect "
                "to Ollama."
            ) from exc

        return [
            list(
                embedding
            )
            for embedding
            in response.embeddings
        ]