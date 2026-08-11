from typing import Any

from sqlalchemy import (
    or_,
    select,
)
from sqlalchemy.orm import Session

from app.ai.tools.base import (
    BaseAITool,
)
from app.db_models.account import (
    AccountRecord,
)
from app.db_models.duplicate_candidate import (
    DuplicateCandidateRecord,
)
from app.db_models.duplicate_group import (
    DuplicateGroupRecord,
)


class SearchDuplicateGroupsTool(
    BaseAITool
):
    name = "search_duplicate_groups"

    description = (
        "Search duplicate-account groups by application, "
        "confidence threshold, username, email, or employee ID."
    )

    parameters = {
        "type": "object",
        "properties": {
            "application": {
                "type": [
                    "string",
                    "null",
                ],
            },
            "minimum_confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 100,
            },
            "search": {
                "type": [
                    "string",
                    "null",
                ],
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 50,
            },
        },
        "required": [
            "application",
            "minimum_confidence",
            "search",
            "limit",
        ],
        "additionalProperties": False,
    }

    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:
        statement = (
            select(
                DuplicateGroupRecord,
                AccountRecord,
            )
            .join(
                AccountRecord,
                AccountRecord.id
                == DuplicateGroupRecord.primary_account_id,
            )
        )

        application = arguments.get(
            "application"
        )

        if application:
            statement = statement.where(
                AccountRecord.application
                == application
            )

        minimum_confidence = float(
            arguments.get(
                "minimum_confidence",
                0,
            )
        )

        statement = statement.where(
            DuplicateGroupRecord.confidence
            >= minimum_confidence
        )

        search = arguments.get(
            "search"
        )

        if search:
            search_value = (
                f"%{str(search).strip()}%"
            )

            statement = statement.where(
                or_(
                    AccountRecord.username.ilike(
                        search_value
                    ),
                    AccountRecord.email.ilike(
                        search_value
                    ),
                    AccountRecord.employee_id.ilike(
                        search_value
                    ),
                    AccountRecord.display_name.ilike(
                        search_value
                    ),
                )
            )

        statement = (
            statement
            .order_by(
                DuplicateGroupRecord
                .confidence.desc()
            )
            .limit(
                int(
                    arguments.get(
                        "limit",
                        20,
                    )
                )
            )
        )

        rows = db.execute(
            statement
        ).all()

        return [
            {
                "groupId": group.id,
                "application": (
                    primary.application
                ),
                "primaryUsername": (
                    primary.username
                ),
                "primaryDisplayName": (
                    primary.display_name
                ),
                "confidence": (
                    group.confidence
                ),
            }
            for group, primary in rows
        ]


class GetDuplicateGroupDetailsTool(
    BaseAITool
):
    name = "get_duplicate_group_details"

    description = (
        "Get the primary account, duplicate candidates, "
        "confidence score, matched attributes, and "
        "different attributes for one duplicate group."
    )

    parameters = {
        "type": "object",
        "properties": {
            "group_id": {
                "type": "integer",
                "minimum": 1,
            },
        },
        "required": [
            "group_id",
        ],
        "additionalProperties": False,
    }

    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:
        group_id = int(
            arguments["group_id"]
        )

        group = db.get(
            DuplicateGroupRecord,
            group_id,
        )

        if group is None:
            return {
                "found": False,
                "message": (
                    "Duplicate group was not found."
                ),
            }

        primary = db.get(
            AccountRecord,
            group.primary_account_id,
        )

        candidate_statement = (
            select(
                DuplicateCandidateRecord,
                AccountRecord,
            )
            .join(
                AccountRecord,
                AccountRecord.id
                == DuplicateCandidateRecord
                .candidate_account_id,
            )
            .where(
                DuplicateCandidateRecord
                .duplicate_group_id
                == group.id
            )
            .order_by(
                DuplicateCandidateRecord
                .confidence.desc()
            )
        )

        rows = db.execute(
            candidate_statement
        ).all()

        return {
            "found": True,
            "groupId": group.id,
            "confidence": group.confidence,
            "primaryAccount": (
                _account_to_dict(primary)
                if primary
                else None
            ),
            "candidates": [
                {
                    "candidate": (
                        _account_to_dict(
                            account
                        )
                    ),
                    "confidence": (
                        candidate.confidence
                    ),
                    "matchedAttributes": (
                        candidate
                        .matched_attributes
                    ),
                    "differentAttributes": (
                        candidate
                        .different_attributes
                    ),
                }
                for candidate, account in rows
            ],
        }


def _account_to_dict(
    account: AccountRecord,
) -> dict[str, Any]:
    return {
        "id": account.id,
        "application": account.application,
        "username": account.username,
        "displayName": account.display_name,
        "email": account.email,
        "employeeId": account.employee_id,
        "department": account.department,
        "manager": account.manager,
        "status": account.status,
        "created": account.created,
    }