from __future__ import annotations

from typing import Any

from app.ai.agent_core.models import AgentEntity, AgentState, EntityType, PendingAction


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _first(items: Any) -> dict[str, Any]:
    if not isinstance(items, list) or not items:
        return {}
    return _dict(items[0])


def _entity(
    entity_type: EntityType,
    *,
    id_value: Any,
    label: Any = None,
    attributes: dict[str, Any] | None = None,
    source: str,
) -> AgentEntity:
    return AgentEntity(
        entity_type=entity_type,
        id=id_value,
        label=str(label) if label not in (None, "") else None,
        attributes=attributes or {},
        source=source,
    )


def reduce_tool_result(
    state: AgentState,
    *,
    tool_name: str,
    tool_result: Any,
) -> AgentState:
    """Merge grounded tool output into structured agent state.

    Only explicit fields returned by successful tools are stored. This prevents
    conversational prose or model assumptions from becoming authoritative state.
    """

    if not isinstance(tool_result, dict) or tool_result.get("success") is not True:
        return state

    data = _dict(tool_result.get("data"))
    updated = state.model_copy(deep=True)

    if tool_name == "investigate_accounts":
        items = data.get("items")
        if isinstance(items, list) and len(items) == 1:
            account = _dict(items[0])
            updated.current_account = _entity(
                EntityType.SOURCE_ACCOUNT,
                id_value=account.get("sourceAccountId"),
                label=account.get("displayName") or account.get("username"),
                attributes={
                    "integrationId": account.get("integrationId"),
                    "integrationName": account.get("integrationName"),
                    "application": account.get("application"),
                    "nativeIdentity": account.get("nativeIdentity"),
                    "username": account.get("username"),
                    "displayName": account.get("displayName"),
                    "email": account.get("email"),
                    "employeeId": account.get("employeeId"),
                    "orphaned": account.get("orphaned"),
                    "orphanType": account.get("orphanType"),
                },
                source=tool_name,
            )
            if account.get("integrationId") is not None:
                updated.current_integration = _entity(
                    EntityType.INTEGRATION,
                    id_value=account.get("integrationId"),
                    label=account.get("integrationName") or account.get("application"),
                    attributes={"application": account.get("application")},
                    source=tool_name,
                )

    elif tool_name == "search_orphan_accounts":
        items = data.get("items")
        report_filters = data.get("reportFilters")
        updated.last_filters = {
            "context": "orphan_accounts",
            "reportType": str(data.get("reportType") or "orphan_accounts"),
            "filters": dict(report_filters) if isinstance(report_filters, dict) else {},
        }

        if isinstance(items, list) and len(items) == 1:
            account = _dict(items[0])
            updated.current_account = _entity(
                EntityType.SOURCE_ACCOUNT,
                id_value=account.get("sourceAccountId"),
                label=account.get("displayName") or account.get("username"),
                attributes=account,
                source=tool_name,
            )
            if account.get("integrationId") is not None:
                updated.current_integration = _entity(
                    EntityType.INTEGRATION,
                    id_value=account.get("integrationId"),
                    label=account.get("integrationName") or account.get("application"),
                    attributes={"application": account.get("application")},
                    source=tool_name,
                )

    elif tool_name in {"search_duplicate_groups", "get_duplicate_group_details"}:
        groups = data.get("groups")
        if groups is None and data.get("found"):
            groups = [data]
        if isinstance(groups, list) and len(groups) == 1:
            group = _dict(groups[0])
            group_id = group.get("groupId") or group.get("id")
            updated.current_duplicate_group = _entity(
                EntityType.DUPLICATE_GROUP,
                id_value=group_id,
                label=group.get("primaryUsername"),
                attributes={
                    "application": group.get("application"),
                    "primaryUsername": group.get("primaryUsername"),
                    "highestConfidence": group.get("highestConfidence"),
                    "duplicateCount": group.get("duplicateCount"),
                },
                source=tool_name,
            )

            primary = _dict(group.get("primaryAccount"))
            if primary:
                updated.current_account = _entity(
                    EntityType.SOURCE_ACCOUNT,
                    id_value=primary.get("sourceAccountId") or primary.get("id"),
                    label=primary.get("displayName") or primary.get("username"),
                    attributes=primary,
                    source=tool_name,
                )

            candidates = group.get("candidates")
            if isinstance(candidates, list) and len(candidates) == 1:
                candidate = _dict(candidates[0])
                updated.current_duplicate_candidate = _entity(
                    EntityType.DUPLICATE_CANDIDATE,
                    id_value=candidate.get("id") or candidate.get("candidateId"),
                    label=candidate.get("username"),
                    attributes={
                        **candidate,
                        "groupId": group_id,
                    },
                    source=tool_name,
                )

    elif tool_name == "generate_report":
        report_type = str(data.get("reportType") or "").strip()
        client_action = _dict(data.get("clientAction"))
        filters = client_action.get("filters")
        if report_type:
            updated.last_filters = {
                "context": report_type,
                "reportType": report_type,
                "filters": dict(filters) if isinstance(filters, dict) else {},
                "downloadUrl": data.get("downloadUrl"),
            }

    elif tool_name == "search_remediation_items":
        items = data.get("items") or data.get("results")
        if isinstance(items, list) and len(items) == 1:
            item = _dict(items[0])
            updated.current_remediation_item = _entity(
                EntityType.REMEDIATION_ITEM,
                id_value=item.get("id") or item.get("remediationItemId"),
                label=item.get("status"),
                attributes=item,
                source=tool_name,
            )

    elif tool_name == "create_remediation_ticket":
        item_id = data.get("remediationItemId")
        if item_id is not None:
            updated.current_remediation_item = _entity(
                EntityType.REMEDIATION_ITEM,
                id_value=item_id,
                label=data.get("ticketNumber") or data.get("ticketId") or data.get("status"),
                attributes=data,
                source=tool_name,
            )

        if data.get("requiresInput") and item_id is not None:
            missing_fields: list[str] = []
            if not data.get("target"):
                missing_fields.append("target")
            if not data.get("action"):
                missing_fields.append("action")
            updated.pending_action = PendingAction(
                capability="create_remediation_ticket",
                arguments={"remediation_item_id": item_id},
                requires_confirmation=False,
                missing_fields=missing_fields or ["target", "action"],
            )
        elif data.get("ticketId") or data.get("ticketNumber") or data.get("created") is True:
            updated.pending_action = None

    elif tool_name in {"get_integration_details", "list_integrations"}:
        integration = data
        if tool_name == "list_integrations":
            integrations = data.get("integrations") or data.get("items")
            if isinstance(integrations, list) and len(integrations) == 1:
                integration = _dict(integrations[0])
        integration_id = integration.get("id") or integration.get("integrationId")
        if integration_id is not None:
            updated.current_integration = _entity(
                EntityType.INTEGRATION,
                id_value=integration_id,
                label=integration.get("name"),
                attributes=integration,
                source=tool_name,
            )

    elif tool_name in {"get_latest_execution", "get_execution_details"}:
        execution = data.get("execution") if isinstance(data.get("execution"), dict) else data
        execution_id = execution.get("id") or execution.get("executionId")
        if execution_id is not None:
            updated.current_execution = _entity(
                EntityType.EXECUTION,
                id_value=execution_id,
                label=execution.get("status"),
                attributes=execution,
                source=tool_name,
            )

    return updated


def render_state_for_planner(state: AgentState) -> str:
    compact = state.compact()
    if not compact:
        return "No structured entity context has been established yet."
    return "Structured conversation state (grounded): " + str(compact)
