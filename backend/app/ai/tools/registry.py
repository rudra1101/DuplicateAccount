from typing import Any

from sqlalchemy.orm import Session

from app.ai.tools.base import (
    BaseAITool,
)


class AIToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[
            str,
            BaseAITool,
        ] = {}

    def register(
        self,
        tool: BaseAITool,
    ) -> None:
        if tool.name in self._tools:
            raise ValueError(
                "AI tool already registered: "
                f"{tool.name}"
            )

        self._tools[tool.name] = tool

    def get(
        self,
        name: str,
    ) -> BaseAITool:
        tool = self._tools.get(name)

        if tool is None:
            raise ValueError(
                f"Unknown AI tool: {name}"
            )

        return tool

    def definitions(
        self,
    ) -> list[dict[str, Any]]:
        return [
            tool.to_openai_definition()
            for tool in self._tools.values()
        ]

    def execute(
        self,
        *,
        name: str,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:
        tool = self.get(name)

        return tool.execute(
            db=db,
            arguments=arguments,
        )