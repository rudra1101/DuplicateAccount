from __future__ import annotations

from typing import Any

from sqlalchemy import (
    func,
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
from app.db_models.integration import (
    IntegrationRecord,
)
from app.db_models.scan import (
    ScanRecord,
)


# =========================================================
# Aliases
# =========================================================

INTEGRATION_ALIASES = {
    "ad": "Active Directory",
    "active directory": "Active Directory",

    "entra": "Entra ID",
    "entra id": "Entra ID",
    "azure ad": "Entra ID",
    "azure active directory": "Entra ID",

    "adp": "ADP",
    "adp hr": "ADP",

    "sap": "SAP",

    "snow": "ServiceNow",
    "service now": "ServiceNow",
    "servicenow": "ServiceNow",

    "workday": "Workday",

    "sample": "Sample accounts",
    "sample accounts": "Sample accounts",
}


APPLICATION_ALIASES = {
    "ad": "Active Directory",
    "active directory": "Active Directory",

    "entra": "Entra ID",
    "entra id": "Entra ID",

    "adp": "ADP HR",
    "adp hr": "ADP HR",

    "sap": "SAP",

    "snow": "ServiceNow",
    "service now": "ServiceNow",
    "servicenow": "ServiceNow",

    "workday": "Workday",
}


# =========================================================
# Helpers
# =========================================================


def normalize_text(
    value: Any,
) -> str:
    return " ".join(
        str(
            value
            or ""
        )
        .strip()
        .split()
    )


def normalize_application(
    value: Any,
) -> str | None:
    text = normalize_text(
        value
    )

    if not text:
        return None

    return APPLICATION_ALIASES.get(
        text.lower(),
        text,
    )


def normalize_confidence(
    value: Any,
) -> float:
    confidence = float(
        value
        or 0
    )

    # Ollama may occasionally return:
    # 0.90 instead of 90
    # 0.95 instead of 95
    if (
        confidence > 0
        and confidence <= 1
    ):
        confidence *= 100

    return max(
        0,
        min(
            confidence,
            100,
        ),
    )


def resolve_integration(
    db: Session,
    value: Any,
) -> IntegrationRecord | None:
    text = normalize_text(
        value
    )

    if not text:
        return None

    # Numeric integration ID
    if text.isdigit():
        return db.get(
            IntegrationRecord,
            int(text),
        )

    normalized = (
        INTEGRATION_ALIASES.get(
            text.lower(),
            text,
        )
    )

    # Exact name match first
    integration = db.scalars(
        select(
            IntegrationRecord
        )
        .where(
            func.lower(
                IntegrationRecord.name
            )
            == normalized.lower()
        )
        .limit(1)
    ).first()

    if integration is not None:
        return integration

    # Partial name / connector match
    integration = db.scalars(
        select(
            IntegrationRecord
        )
        .where(
            or_(
                func.lower(
                    IntegrationRecord.name
                ).like(
                    f"%{normalized.lower()}%"
                ),

                func.lower(
                    IntegrationRecord.connector_type
                ).like(
                    f"%{normalized.lower()}%"
                ),
            )
        )
        .order_by(
            IntegrationRecord.name.asc()
        )
        .limit(1)
    ).first()

    return integration


def get_latest_completed_scan(
    db: Session,
    *,
    integration_id: int,
) -> ScanRecord | None:
    return db.scalars(
        select(
            ScanRecord
        )
        .where(
            ScanRecord.integration_id
            == integration_id,

            ScanRecord.status
            == "COMPLETED",
        )
        .order_by(
            ScanRecord.created_at.desc(),
            ScanRecord.id.desc(),
        )
        .limit(1)
    ).first()


def get_latest_completed_scan_ids(
    db: Session,
) -> list[int]:
    """
    Return only the latest completed scan
    for each configured integration.
    """

    scans = list(
        db.scalars(
            select(
                ScanRecord
            )
            .where(
                ScanRecord.status
                == "COMPLETED"
            )
            .order_by(
                ScanRecord.created_at.desc(),
                ScanRecord.id.desc(),
            )
        ).all()
    )

    latest: dict[
        int,
        int,
    ] = {}

    for scan in scans:
        if (
            scan.integration_id
            is None
        ):
            continue

        integration_id = int(
            scan.integration_id
        )

        if (
            integration_id
            not in latest
        ):
            latest[
                integration_id
            ] = scan.id

    return list(
        latest.values()
    )


def find_primary_account(
    db: Session,
    group: DuplicateGroupRecord,
) -> AccountRecord | None:
    return db.scalars(
        select(
            AccountRecord
        )
        .where(
            AccountRecord.scan_id
            == group.scan_id,

            func.lower(
                AccountRecord.application
            )
            == str(
                group.application
            ).strip().lower(),

            AccountRecord.username
            == group.primary_username,
        )
        .order_by(
            AccountRecord.id.asc()
        )
        .limit(1)
    ).first()


def account_to_dict(
    account: AccountRecord | None,
) -> dict[str, Any] | None:
    if account is None:
        return None

    return {
        "id":
            account.id,

        "sourceAccountId":
            account.source_account_id,

        "scanId":
            account.scan_id,

        "application":
            account.application,

        "username":
            account.username,

        "displayName":
            account.display_name,

        "email":
            account.email,

        "employeeId":
            account.employee_id,

        "department":
            account.department,

        "manager":
            account.manager,

        "status":
            account.status,

        "created":
            account.created,
    }


# =========================================================
# Duplicate Summary
# =========================================================


class GetDuplicateSummaryTool(
    BaseAITool
):
    name = "get_duplicate_summary"

    description = (
        "Get CURRENT duplicate-account statistics from "
        "the latest completed scan. Use this when the user "
        "asks how many duplicate groups, duplicate accounts, "
        "or high-confidence groups exist for an integration "
        "or application."
    )

    parameters = {
        "type": "object",

        "properties": {
            "integration": {
                "type": [
                    "string",
                    "null",
                ],

                "description": (
                    "Integration name or alias. "
                    "Examples: AD, Active Directory, "
                    "ADP, SAP, Entra, ServiceNow."
                ),
            },

            "application": {
                "type": [
                    "string",
                    "null",
                ],

                "description": (
                    "Optional application name."
                ),
            },
        },

        "required": [
            "integration",
            "application",
        ],

        "additionalProperties":
            False,
    }

    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:

        integration_value = (
            arguments.get(
                "integration"
            )
        )

        application = (
            normalize_application(
                arguments.get(
                    "application"
                )
            )
        )

        integration = None

        scan_ids: list[int] = []

        # -------------------------------------------------
        # Integration-specific request
        # -------------------------------------------------

        if integration_value:
            integration = (
                resolve_integration(
                    db,
                    integration_value,
                )
            )

            if integration is None:
                return {
                    "found": False,

                    "integration":
                        integration_value,

                    "message":
                        "Integration was not found.",
                }

            latest_scan = (
                get_latest_completed_scan(
                    db,
                    integration_id=(
                        integration.id
                    ),
                )
            )

            if latest_scan is None:
                return {
                    "found": False,

                    "integrationId":
                        integration.id,

                    "integrationName":
                        integration.name,

                    "message": (
                        "No completed scan was found "
                        "for this integration."
                    ),
                }

            scan_ids = [
                latest_scan.id
            ]

        # -------------------------------------------------
        # System-wide / application request
        # -------------------------------------------------

        else:
            scan_ids = (
                get_latest_completed_scan_ids(
                    db
                )
            )

            if not scan_ids:
                return {
                    "found": False,

                    "message": (
                        "No completed integration "
                        "scans were found."
                    ),
                }

        # -------------------------------------------------
        # Main summary
        # -------------------------------------------------

        statement = (
            select(
                func.count(
                    DuplicateGroupRecord.id
                ).label(
                    "duplicate_groups"
                ),

                func.coalesce(
                    func.sum(
                        DuplicateGroupRecord
                        .duplicate_count
                    ),
                    0,
                ).label(
                    "duplicate_accounts"
                ),

                func.coalesce(
                    func.max(
                        DuplicateGroupRecord
                        .highest_confidence
                    ),
                    0,
                ).label(
                    "highest_confidence"
                ),
            )
            .where(
                DuplicateGroupRecord
                .scan_id
                .in_(
                    scan_ids
                )
            )
        )

        if application:
            statement = statement.where(
                func.lower(
                    DuplicateGroupRecord
                    .application
                )
                == application.lower()
            )

        row = db.execute(
            statement
        ).one()

        # -------------------------------------------------
        # High-confidence group count
        # -------------------------------------------------

        high_statement = (
            select(
                func.count(
                    DuplicateGroupRecord.id
                )
            )
            .where(
                DuplicateGroupRecord
                .scan_id
                .in_(
                    scan_ids
                ),

                DuplicateGroupRecord
                .highest_confidence
                >= 95,
            )
        )

        if application:
            high_statement = (
                high_statement.where(
                    func.lower(
                        DuplicateGroupRecord
                        .application
                    )
                    == application.lower()
                )
            )

        high_confidence_groups = (
            db.scalar(
                high_statement
            )
            or 0
        )

        duplicate_groups = int(
            row.duplicate_groups
            or 0
        )

        duplicate_accounts = int(
            row.duplicate_accounts
            or 0
        )

        return {
            "found":
                duplicate_groups > 0,

            "integrationId": (
                integration.id
                if integration
                else None
            ),

            "integrationName": (
                integration.name
                if integration
                else None
            ),

            "application":
                application,

            "scanIds":
                scan_ids,

            "duplicateGroups":
                duplicate_groups,

            "duplicateAccounts":
                duplicate_accounts,

            "highConfidenceGroups":
                int(
                    high_confidence_groups
                ),

            "highestConfidence":
                float(
                    row.highest_confidence
                    or 0
                ),
        }


# =========================================================
# Search Duplicate Groups
# =========================================================


class SearchDuplicateGroupsTool(
    BaseAITool
):
    name = "search_duplicate_groups"

    description = (
        "Search CURRENT duplicate groups from the latest "
        "completed integration scans. Supports integration, "
        "application, confidence threshold, username, email, "
        "employee ID and display name. "
        "totalMatchingGroups is the TOTAL number of duplicate "
        "groups matching the filters before applying the result "
        "limit. totalMatchingDuplicateAccounts is the TOTAL "
        "number of duplicate accounts across all matching groups. "
        "returnedGroups is only the number of detailed group "
        "records returned after applying the limit."
    )

    parameters = {
        "type": "object",

        "properties": {
            "integration": {
                "type": [
                    "string",
                    "null",
                ],

                "description": (
                    "Optional integration name or alias."
                ),
            },

            "application": {
                "type": [
                    "string",
                    "null",
                ],

                "description": (
                    "Optional application name."
                ),
            },

            "minimum_confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 100,

                "description": (
                    "Minimum confidence using the 0-100 "
                    "percentage scale. Use 90 for 90 percent."
                ),
            },

            "search": {
                "type": [
                    "string",
                    "null",
                ],

                "description": (
                    "Optional username, display name, "
                    "email, employee ID, or group search."
                ),
            },

            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 50,

                "description": (
                    "Maximum number of detailed group "
                    "records to return. This does not "
                    "affect totalMatchingGroups."
                ),
            },
        },

        "required": [
            "integration",
            "application",
            "minimum_confidence",
            "search",
            "limit",
        ],

        "additionalProperties":
            False,
    }

    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:

        # =====================================================
        # Arguments
        # =====================================================

        integration_value = (
            arguments.get(
                "integration"
            )
        )

        application = (
            normalize_application(
                arguments.get(
                    "application"
                )
            )
        )

        minimum_confidence = (
            normalize_confidence(
                arguments.get(
                    "minimum_confidence",
                    0,
                )
            )
        )

        limit = int(
            arguments.get(
                "limit",
                20,
            )
            or 20
        )

        limit = max(
            1,
            min(
                limit,
                50,
            ),
        )

        integration = None

        # =====================================================
        # Resolve scan scope
        # =====================================================

        if integration_value:
            integration = (
                resolve_integration(
                    db,
                    integration_value,
                )
            )

            if integration is None:
                return {
                    "found": False,

                    "integration":
                        integration_value,

                    "totalMatchingGroups":
                        0,

                    "totalMatchingDuplicateAccounts":
                        0,

                    "returnedGroups":
                        0,

                    "groups":
                        [],

                    "message":
                        "Integration was not found.",
                }

            latest_scan = (
                get_latest_completed_scan(
                    db,
                    integration_id=(
                        integration.id
                    ),
                )
            )

            if latest_scan is None:
                return {
                    "found": False,

                    "integrationId":
                        integration.id,

                    "integrationName":
                        integration.name,

                    "totalMatchingGroups":
                        0,

                    "totalMatchingDuplicateAccounts":
                        0,

                    "returnedGroups":
                        0,

                    "groups":
                        [],

                    "message": (
                        "No completed scan was found "
                        "for this integration."
                    ),
                }

            scan_ids = [
                latest_scan.id
            ]

        else:
            scan_ids = (
                get_latest_completed_scan_ids(
                    db
                )
            )

        if not scan_ids:
            return {
                "found": False,

                "totalMatchingGroups":
                    0,

                "totalMatchingDuplicateAccounts":
                    0,

                "returnedGroups":
                    0,

                "groups":
                    [],

                "message": (
                    "No completed integration "
                    "scans were found."
                ),
            }

        # =====================================================
        # Build filtered query WITHOUT limit
        # =====================================================

        filtered_statement = (
            select(
                DuplicateGroupRecord
            )
            .where(
                DuplicateGroupRecord
                .scan_id
                .in_(
                    scan_ids
                ),

                DuplicateGroupRecord
                .highest_confidence
                >= minimum_confidence,
            )
        )

        # =====================================================
        # Application filter
        # =====================================================

        if application:
            filtered_statement = (
                filtered_statement.where(
                    func.lower(
                        DuplicateGroupRecord
                        .application
                    )
                    == application.lower()
                )
            )

        # =====================================================
        # Search filter
        # =====================================================

        search = normalize_text(
            arguments.get(
                "search"
            )
        )

        if search:
            search_value = (
                f"%{search}%"
            )

            primary_group_ids = (
                select(
                    DuplicateGroupRecord.id
                )
                .join(
                    AccountRecord,
                    (
                        AccountRecord.scan_id
                        == DuplicateGroupRecord
                        .scan_id
                    )
                    & (
                        func.lower(
                            AccountRecord.application
                        )
                        == func.lower(
                            DuplicateGroupRecord.application
                        )
                    )
                    & (
                        AccountRecord.username
                        == DuplicateGroupRecord
                        .primary_username
                    ),
                )
                .where(
                    or_(
                        AccountRecord.username
                        .ilike(
                            search_value
                        ),

                        AccountRecord.display_name
                        .ilike(
                            search_value
                        ),

                        AccountRecord.email
                        .ilike(
                            search_value
                        ),

                        AccountRecord.employee_id
                        .ilike(
                            search_value
                        ),
                    )
                )
            )

            candidate_group_ids = (
                select(
                    DuplicateCandidateRecord
                    .group_id
                )
                .where(
                    DuplicateCandidateRecord
                    .username
                    .ilike(
                        search_value
                    )
                )
            )

            filtered_statement = (
                filtered_statement.where(
                    or_(
                        DuplicateGroupRecord
                        .primary_username
                        .ilike(
                            search_value
                        ),

                        DuplicateGroupRecord
                        .id
                        .in_(
                            primary_group_ids
                        ),

                        DuplicateGroupRecord
                        .id
                        .in_(
                            candidate_group_ids
                        ),
                    )
                )
            )

        # =====================================================
        # Calculate REAL totals before limit
        # =====================================================

        count_subquery = (
            filtered_statement
            .with_only_columns(
                DuplicateGroupRecord.id,

                DuplicateGroupRecord
                .duplicate_count,
            )
            .subquery()
        )

        summary_row = db.execute(
            select(
                func.count(
                    count_subquery.c.id
                ).label(
                    "group_count"
                ),

                func.coalesce(
                    func.sum(
                        count_subquery.c
                        .duplicate_count
                    ),
                    0,
                ).label(
                    "duplicate_account_count"
                ),
            )
        ).one()

        total_matching_groups = int(
            summary_row.group_count
            or 0
        )

        total_matching_duplicate_accounts = int(
            summary_row
            .duplicate_account_count
            or 0
        )

        # =====================================================
        # Only now apply ordering + result limit
        # =====================================================

        limited_statement = (
            filtered_statement
            .order_by(
                DuplicateGroupRecord
                .highest_confidence
                .desc(),

                DuplicateGroupRecord
                .id
                .asc(),
            )
            .limit(
                limit
            )
        )

        groups = list(
            db.scalars(
                limited_statement
            ).all()
        )

        # =====================================================
        # Build detailed records
        # =====================================================

        result: list[
            dict[str, Any]
        ] = []

        for group in groups:
            primary = (
                find_primary_account(
                    db,
                    group,
                )
            )

            result.append(
                {
                    "groupId":
                        group.id,

                    "scanId":
                        group.scan_id,

                    "application":
                        group.application,

                    "primaryUsername":
                        group.primary_username,

                    "primaryDisplayName": (
                        primary.display_name
                        if primary
                        else None
                    ),

                    "duplicateAccounts":
                        int(
                            group.duplicate_count
                            or 0
                        ),

                    "highestConfidence":
                        float(
                            group
                            .highest_confidence
                            or 0
                        ),
                }
            )

        # =====================================================
        # Response
        # =====================================================

        return {
            "found":
                total_matching_groups > 0,

            "integrationId": (
                integration.id
                if integration
                else None
            ),

            "integrationName": (
                integration.name
                if integration
                else None
            ),

            "application":
                application,

            "scanIds":
                scan_ids,

            "minimumConfidence":
                minimum_confidence,

            "totalMatchingGroups":
                total_matching_groups,

            "totalMatchingDuplicateAccounts":
                total_matching_duplicate_accounts,

            "returnedGroups":
                len(
                    result
                ),

            "limit":
                limit,

            "groups":
                result,
        }


class GetConfidenceBreakdownTool(
    BaseAITool
):
    name = "get_confidence_breakdown"

    description = (
        "Get CURRENT duplicate candidate account counts grouped "
        "by application for a confidence threshold. "
        "Use this when the user asks how many duplicate accounts "
        "have confidence above, at least, below, or equal to a "
        "specific percentage, especially application-wise. "
        "This tool counts candidate accounts using each candidate's "
        "own confidence score."
    )

    parameters = {
        "type": "object",

        "properties": {
            "minimum_confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 100,
            },

            "operator": {
                "type": "string",
                "enum": [
                    "gt",
                    "gte",
                    "lt",
                    "lte",
                    "eq",
                ],
            },

            "integration": {
                "type": [
                    "string",
                    "null",
                ],
            },
        },

        "required": [
            "minimum_confidence",
            "operator",
            "integration",
        ],

        "additionalProperties": False,
    }

    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:

        confidence = normalize_confidence(
            arguments.get(
                "minimum_confidence",
                0,
            )
        )

        operator = str(
            arguments.get(
                "operator",
                "gte",
            )
        ).strip().lower()

        integration_value = (
            arguments.get(
                "integration"
            )
        )

        integration = None

        # -------------------------------------------------
        # Scan scope
        # -------------------------------------------------

        if integration_value:
            integration = resolve_integration(
                db,
                integration_value,
            )

            if integration is None:
                return {
                    "found": False,
                    "totalMatchingAccounts": 0,
                    "applications": [],
                    "message": (
                        "Integration was not found."
                    ),
                }

            latest_scan = (
                get_latest_completed_scan(
                    db,
                    integration_id=(
                        integration.id
                    ),
                )
            )

            if latest_scan is None:
                return {
                    "found": False,
                    "totalMatchingAccounts": 0,
                    "applications": [],
                    "message": (
                        "No completed scan was found "
                        "for this integration."
                    ),
                }

            scan_ids = [
                latest_scan.id
            ]

        else:
            scan_ids = (
                get_latest_completed_scan_ids(
                    db
                )
            )

        if not scan_ids:
            return {
                "found": False,
                "totalMatchingAccounts": 0,
                "applications": [],
                "message": (
                    "No completed integration scans "
                    "were found."
                ),
            }

        # -------------------------------------------------
        # Confidence condition
        # -------------------------------------------------

        confidence_column = (
            DuplicateCandidateRecord
            .confidence
        )

        if operator == "gt":
            confidence_condition = (
                confidence_column > confidence
            )

        elif operator == "gte":
            confidence_condition = (
                confidence_column >= confidence
            )

        elif operator == "lt":
            confidence_condition = (
                confidence_column < confidence
            )

        elif operator == "lte":
            confidence_condition = (
                confidence_column <= confidence
            )

        elif operator == "eq":
            confidence_condition = (
                confidence_column == confidence
            )

        else:
            return {
                "found": False,
                "totalMatchingAccounts": 0,
                "applications": [],
                "message": (
                    "Unsupported confidence operator."
                ),
            }

        # -------------------------------------------------
        # Application-wise aggregation
        # -------------------------------------------------

        statement = (
            select(
                DuplicateGroupRecord.application,

                func.count(
                    DuplicateCandidateRecord.id
                ).label(
                    "matching_accounts"
                ),

                func.max(
                    DuplicateCandidateRecord
                    .confidence
                ).label(
                    "highest_confidence"
                ),

                func.avg(
                    DuplicateCandidateRecord
                    .confidence
                ).label(
                    "average_confidence"
                ),
            )
            .join(
                DuplicateGroupRecord,

                DuplicateGroupRecord.id
                == DuplicateCandidateRecord
                .group_id,
            )
            .where(
                DuplicateGroupRecord
                .scan_id
                .in_(
                    scan_ids
                ),

                confidence_condition,
            )
            .group_by(
                DuplicateGroupRecord
                .application
            )
            .order_by(
                func.count(
                    DuplicateCandidateRecord.id
                ).desc(),

                DuplicateGroupRecord
                .application
                .asc(),
            )
        )

        rows = db.execute(
            statement
        ).all()

        applications = [
            {
                "application": str(
                    row.application
                    or ""
                ).strip(),

                "matchingAccounts": int(
                    row.matching_accounts
                    or 0
                ),

                "highestConfidence": float(
                    row.highest_confidence
                    or 0
                ),

                "averageConfidence": round(
                    float(
                        row.average_confidence
                        or 0
                    ),
                    2,
                ),
            }

            for row in rows
        ]

        total_matching_accounts = sum(
            int(
                item[
                    "matchingAccounts"
                ]
            )
            for item in applications
        )

        return {
            "found": (
                total_matching_accounts
                > 0
            ),

            "integrationId": (
                integration.id
                if integration
                else None
            ),

            "integrationName": (
                integration.name
                if integration
                else None
            ),

            "scanIds":
                scan_ids,

            "confidence":
                confidence,

            "operator":
                operator,

            "totalMatchingAccounts":
                total_matching_accounts,

            "applicationCount":
                len(
                    applications
                ),

            "applications":
                applications,
        }
# =========================================================
# Duplicate Group Details
# =========================================================


class GetDuplicateGroupDetailsTool(
    BaseAITool
):
    name = (
        "get_duplicate_group_details"
    )

    description = (
        "Get full details for one duplicate group, "
        "including its primary account, duplicate "
        "candidates, confidence, model reasoning "
        "and review status."
    )

    parameters = {
        "type": "object",

        "properties": {
            "group_id": {
                "type":
                    "integer",

                "minimum":
                    1,
            },
        },

        "required": [
            "group_id",
        ],

        "additionalProperties":
            False,
    }

    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:

        group_id = int(
            arguments[
                "group_id"
            ]
        )

        group = db.get(
            DuplicateGroupRecord,
            group_id,
        )

        if group is None:
            return {
                "found": False,

                "message": (
                    "Duplicate group "
                    "was not found."
                ),
            }

        primary = (
            find_primary_account(
                db,
                group,
            )
        )

        candidates = list(
            db.scalars(
                select(
                    DuplicateCandidateRecord
                )
                .where(
                    DuplicateCandidateRecord
                    .group_id
                    == group.id
                )
                .order_by(
                    DuplicateCandidateRecord
                    .confidence
                    .desc(),

                    DuplicateCandidateRecord
                    .candidate_number
                    .asc(),

                    DuplicateCandidateRecord
                    .id
                    .asc(),
                )
            ).all()
        )

        return {
            "found":
                True,

            "groupId":
                group.id,

            "scanId":
                group.scan_id,

            "application":
                group.application,

            "primaryUsername":
                group.primary_username,

            "duplicateAccounts":
                group.duplicate_count,

            "highestConfidence":
                group.highest_confidence,

            "primaryAccount":
                account_to_dict(
                    primary
                ),

            "candidates": [
                {
                    "id":
                        candidate.id,

                    "candidateNumber":
                        candidate
                        .candidate_number,

                    "username":
                        candidate.username,

                    "confidence":
                        candidate.confidence,

                    "recommendation":
                        candidate
                        .recommendation,

                    "classification":
                        candidate
                        .classification,

                    "matchedAttributes":
                        candidate
                        .matched_attributes
                        or [],

                    "differentAttributes":
                        candidate
                        .different_attributes
                        or [],

                    "account":
                        candidate
                        .account_data
                        or {},

                    "modelVersion":
                        candidate
                        .model_version,

                    "reasons":
                        candidate.reasons
                        or [],

                    "warnings":
                        candidate.warnings
                        or [],

                    "features":
                        candidate.features
                        or {},

                    "reviewDecision":
                        candidate
                        .review_decision,

                    "reviewComment":
                        candidate
                        .review_comment,

                    "reviewerName":
                        candidate
                        .reviewer_name,

                    "reviewedAt": (
                        candidate
                        .reviewed_at
                        .isoformat()
                        if candidate
                        .reviewed_at
                        else None
                    ),
                }

                for candidate
                in candidates
            ],
        }


# =========================================================
# Review Statistics
# =========================================================


class GetReviewStatisticsTool(
    BaseAITool
):
    name = (
        "get_review_statistics"
    )

    description = (
        "Get CURRENT review statistics from the latest "
        "completed integration scans, including pending, "
        "duplicate, not-duplicate and uncertain candidates."
    )

    parameters = {
        "type": "object",

        "properties": {
            "integration": {
                "type": [
                    "string",
                    "null",
                ],
            },

            "application": {
                "type": [
                    "string",
                    "null",
                ],
            },
        },

        "required": [
            "integration",
            "application",
        ],

        "additionalProperties":
            False,
    }

    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:

        integration_value = (
            arguments.get(
                "integration"
            )
        )

        application = (
            normalize_application(
                arguments.get(
                    "application"
                )
            )
        )

        integration = None

        if integration_value:
            integration = (
                resolve_integration(
                    db,
                    integration_value,
                )
            )

            if integration is None:
                return {
                    "found":
                        False,

                    "message":
                        "Integration was not found.",
                }

            latest_scan = (
                get_latest_completed_scan(
                    db,
                    integration_id=(
                        integration.id
                    ),
                )
            )

            if latest_scan is None:
                return {
                    "found":
                        False,

                    "message": (
                        "No completed scan was found "
                        "for this integration."
                    ),
                }

            scan_ids = [
                latest_scan.id
            ]

        else:
            scan_ids = (
                get_latest_completed_scan_ids(
                    db
                )
            )

        if not scan_ids:
            return {
                "found":
                    False,

                "totalCandidates":
                    0,

                "pending":
                    0,

                "duplicate":
                    0,

                "notDuplicate":
                    0,

                "uncertain":
                    0,
            }

        statement = (
            select(
                DuplicateCandidateRecord
                .review_decision,

                func.count(
                    DuplicateCandidateRecord
                    .id
                ),
            )
            .join(
                DuplicateGroupRecord,

                DuplicateGroupRecord.id
                == DuplicateCandidateRecord
                .group_id,
            )
            .where(
                DuplicateGroupRecord
                .scan_id
                .in_(
                    scan_ids
                )
            )
        )

        if application:
            statement = (
                statement.where(
                    func.lower(
                        DuplicateGroupRecord
                        .application
                    )
                    == application.lower()
                )
            )

        rows = db.execute(
            statement.group_by(
                DuplicateCandidateRecord
                .review_decision
            )
        ).all()

        counts = {
            "PENDING":
                0,

            "DUPLICATE":
                0,

            "NOT_DUPLICATE":
                0,

            "UNCERTAIN":
                0,
        }

        for decision, count in rows:
            key = (
                str(
                    decision
                )
                .strip()
                .upper()
                if decision
                else "PENDING"
            )

            counts[
                key
            ] = (
                counts.get(
                    key,
                    0,
                )
                + int(
                    count
                )
            )

        total_candidates = sum(
            counts.values()
        )

        return {
            "found":
                total_candidates > 0,

            "integrationId": (
                integration.id
                if integration
                else None
            ),

            "integrationName": (
                integration.name
                if integration
                else None
            ),

            "application":
                application,

            "scanIds":
                scan_ids,

            "totalCandidates":
                total_candidates,

            "pending":
                counts.get(
                    "PENDING",
                    0,
                ),

            "duplicate":
                counts.get(
                    "DUPLICATE",
                    0,
                ),

            "notDuplicate":
                counts.get(
                    "NOT_DUPLICATE",
                    0,
                ),

            "uncertain":
                counts.get(
                    "UNCERTAIN",
                    0,
                ),
        }


