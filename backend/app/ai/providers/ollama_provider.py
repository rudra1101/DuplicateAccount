import json
import re
from typing import Any

import httpx

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
            ),
            timeout=httpx.Timeout(
                connect=30.0,
                read=300.0,
                write=60.0,
                pool=30.0,
            ),
        )

    # ---------------------------------------------------------
    # Tool schema normalization
    # ---------------------------------------------------------

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
                            tool[
                                "name"
                            ],

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

    # ---------------------------------------------------------
    # Assistant message conversion
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Fallback parsing
    # ---------------------------------------------------------

    @staticmethod
    def _extract_json_block(
        text: str,
    ) -> dict[
        str,
        Any,
    ] | None:
        """
        Parse only content that clearly looks like
        a tool-call JSON object.

        This intentionally does NOT parse arbitrary
        prose containing JSON.
        """

        value = (
            text
            .strip()
        )

        if not value:
            return None

        # Remove Markdown JSON fences if the model
        # returned:
        #
        # ```json
        # {...}
        # ```

        fence_match = re.fullmatch(
            r"\s*```(?:json)?\s*"
            r"(\{.*\})"
            r"\s*```\s*",
            value,
            flags=re.DOTALL
            | re.IGNORECASE,
        )

        if fence_match:
            value = (
                fence_match
                .group(1)
                .strip()
            )

        # Do not try to extract JSON from arbitrary
        # natural-language responses.
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
            parsed = (
                json.loads(
                    value
                )
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
        """
        Convert a model-generated JSON tool request into
        a real ProviderToolCall.

        Supported shapes:

        {
            "name": "tool_name",
            "arguments": {...}
        }

        {
            "name": "tool_name",
            "parameters": {...}
        }

        {
            "function": {
                "name": "tool_name",
                "arguments": {...}
            }
        }
        """

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
            name = (
                payload.get(
                    "name"
                )
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

        name = (
            name
            .strip()
        )

        # Critical safety check:
        # never execute a model-invented tool name.
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

    # ---------------------------------------------------------
    # Chat
    # ---------------------------------------------------------

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

        allowed_tool_names = {
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

        try:
            response = (
                self._client.chat(
                    model=model,

                    messages=
                        messages,

                    tools=
                        normalized_tools,

                    stream=
                        False,
                )
            )

        except (
            ResponseError
        ) as exc:
            raise RuntimeError(
                "Ollama chat request "
                "failed: "
                f"{exc.error}"
            ) from exc

        except (
            httpx.TimeoutException
        ) as exc:
            raise RuntimeError(
                "Ollama request timed out. "
                "The model may still be loading "
                "or the system may be under heavy CPU load."
            ) from exc

        except (
            ConnectionError
        ) as exc:
            raise RuntimeError(
                "Unable to connect "
                "to Ollama. Confirm "
                "Ollama is running on "
                "http://127.0.0.1:11434."
            ) from exc

        message = (
            response.message
        )

        tool_calls: list[
            ProviderToolCall
        ] = []

        # -----------------------------------------------------
        # Native Ollama tool calls
        # -----------------------------------------------------

        for call in (
            message.tool_calls
            or []
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

        assistant_message = (
            self._message_to_dict(
                message
            )
        )

        text = (
            message.content
            or ""
        )

        # -----------------------------------------------------
        # Fallback:
        # Model wrote tool JSON into content rather than
        # response.message.tool_calls
        # -----------------------------------------------------

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

                # Convert it to the same structure used by
                # actual Ollama tool calls.
                assistant_message = {
                    "role":
                        "assistant",

                    "content":
                        "",

                    "tool_calls": [
                        {
                            "type":
                                "function",

                            "function": {
                                "name":
                                    fallback_tool_call
                                    .name,

                                "arguments":
                                    fallback_tool_call
                                    .arguments,
                            },
                        }
                    ],
                }

                # Do not display raw JSON to the user.
                text = ""

        return ProviderResponse(
            text=text,

            assistant_message=
                assistant_message,

            tool_calls=
                tool_calls,

            model=
                model,
        )

    # ---------------------------------------------------------
    # Embeddings
    # ---------------------------------------------------------

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

        except (
            ResponseError
        ) as exc:
            raise RuntimeError(
                "Ollama embedding request "
                "failed: "
                f"{exc.error}"
            ) from exc

        except (
            httpx.TimeoutException
        ) as exc:
            raise RuntimeError(
                "Ollama embedding request timed out."
            ) from exc

        except (
            ConnectionError
        ) as exc:
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