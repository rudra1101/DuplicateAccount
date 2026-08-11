from abc import (
    ABC,
    abstractmethod,
)
from typing import Any

from sqlalchemy.orm import Session


class BaseAITool(ABC):
    name: str
    description: str
    parameters: dict[str, Any]

    @abstractmethod
    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:
        raise NotImplementedError

    def to_openai_definition(
        self,
    ) -> dict[str, Any]:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "strict": True,
        }