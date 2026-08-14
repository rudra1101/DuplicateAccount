from typing import Any

from sqlalchemy.orm import Session

from app.ai.tools.base import BaseAITool
from app.services.training_label_service import (
    get_training_label_summary,
)


class GetTrainingLabelSummaryTool(BaseAITool):
    name = "get_training_label_summary"

    description = (
        "Get the number of usable duplicate and not-duplicate reviewer "
        "labels and whether enough balanced labels exist to train the model."
    )

    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }

    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:
        return get_training_label_summary(db)
