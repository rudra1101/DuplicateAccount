from __future__ import annotations

import ast
import re
from typing import Any

from app.ai.agent_core.capability_retriever import CapabilityRetriever
from app.ai.agent_core.models import AgentCapability, CapabilityKind
from app.ai.agent_service import extract_text_tool_calls
from app.ai.providers.base import ProviderToolCall


SAFE_GROUNDING_KINDS = {CapabilityKind.READ, CapabilityKind.KNOWLEDGE}
# A WRITE capability must be explicitly allowlisted here before the deterministic
# second-chance planner may consider it. This keeps forced grounding read-only by
# default while allowing carefully selected, non-destructive operational writes to
# recover when a small local model returns prose instead of a native tool call.
RECOVERABLE_WRITE_CAPABILITIES = {"run_integration"}
MIN_PRIMARY_GROUNDING_SCORE = 0.22
MIN_RECOVERABLE_WRITE_SCORE = 0.40
_REFERENTIAL_REQUEST = re.compile(
    r"\b(?:this|that|these|those|them|it|same|previous|above)\b"
    r"|\b(?:what|which)\s+(?:was|is)\s+the\s+(?:result|status)\b"
    r"|\b(?:the|last|latest|previous)\s+(?:run|execution|aggregation)\b"
    r"|\bhow\s+many\s+(?:accounts?|records?)\b.*\b(?:scanned|processed|created|updated|unchanged|deleted)\b"
    r"|\bhow\s+many\s+(?:duplicates?|duplicate\s+accounts?|duplicate\s+groups?)\b",
    flags=re.IGNORECASE,
)
_EXPLICIT_WRITE_REQUEST = re.compile(
    r"^\s*(?:(?:please|kindly)\s+)?"
    r"(?:(?:can|could|would|will)\s+you\s+)?"
    r"(?:run|start|execute|trigger|aggregate|sync|refresh)\b",
    flags=re.IGNORECASE,
)
_MISSING = object()


def safe_grounding_definitions(
    definitions: list[dict[str, Any]],
    capabilities: list[AgentCapability],
) -> list[dict[str, Any]]:
    safe_names = {
        capability.name
        for capability in capabilities
        if (
            capability.kind in SAFE_GROUNDING_KINDS
            or (
                capability.kind == CapabilityKind.WRITE
                and capability.name in RECOVERABLE_WRITE_CAPABILITIES
            )
        )
        and not capability.destructive
    }
    return [
        definition
        for definition in definitions
        if str(definition.get("name") or "") in safe_names
    ]


def primary_grounding_definition(
    definitions: list[dict[str, Any]],
    user_message: str,
) -> dict[str, Any] | None:
    """Choose a sufficiently relevant capability from its tool contract.

    Read/knowledge capabilities retain the normal grounding threshold. Allowlisted
    WRITE capabilities are deliberately stricter: the request must look like an
    explicit action command and the capability must clear a higher relevance score.
    This prevents informational questions from being converted into side effects.
    """

    if not definitions:
        return None

    message = str(user_message or "")
    ranked = CapabilityRetriever(definitions).rank(message)
    for item in ranked:
        if item.score < MIN_PRIMARY_GROUNDING_SCORE:
            break

        name = str(item.definition.get("name") or "")
        if name in RECOVERABLE_WRITE_CAPABILITIES:
            if item.score < MIN_RECOVERABLE_WRITE_SCORE:
                continue
            if not _EXPLICIT_WRITE_REQUEST.search(message):
                continue

        return item.definition

    return None


def _normalized_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").casefold())


def _parse_grounded_state(value: str) -> dict[str, Any]:
    """Parse the private planner-state rendering produced by state.py.

    The renderer intentionally emits Python primitive representations only. Using
    ``literal_eval`` keeps this local and non-executable while allowing the
    grounding layer to reuse values that successful tools have already proved.
    """

    text = str(value or "").strip()
    marker = "Structured conversation state (grounded):"
    if marker not in text:
        return {}
    payload = text.split(marker, 1)[1].strip()
    try:
        parsed = ast.literal_eval(payload)
    except (SyntaxError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _find_state_value(node: Any, key: str) -> Any:
    wanted = _normalized_key(key)
    if isinstance(node, dict):
        # Prefer the nearest exact key match before descending into nested state.
        for candidate_key, value in node.items():
            if _normalized_key(candidate_key) == wanted:
                return value
        for value in node.values():
            found = _find_state_value(value, key)
            if found is not _MISSING:
                return found
    elif isinstance(node, list):
        for value in node:
            found = _find_state_value(value, key)
            if found is not _MISSING:
                return found
    return _MISSING


def _grounded_required_arguments(
    definition: dict[str, Any],
    *,
    user_message: str,
    grounded_state: str,
) -> dict[str, Any] | None:
    """Reuse already-grounded required arguments for referential follow-ups.

    This is schema-driven rather than capability-name driven. For example, a report
    capability requiring ``report_type`` and ``filters`` can reuse the previous
    result set's grounded ``reportType``/``filters`` when the user says "these".
    We deliberately do not do this for fresh/non-referential requests because new
    user-supplied filters should be interpreted by the argument planner.
    """

    if not _REFERENTIAL_REQUEST.search(str(user_message or "")):
        return None

    parameters = definition.get("parameters")
    if not isinstance(parameters, dict):
        return None
    required = parameters.get("required")
    if not isinstance(required, list) or not required:
        return None
    properties = parameters.get("properties")
    if not isinstance(properties, dict):
        return None

    state = _parse_grounded_state(grounded_state)
    if not state:
        return None

    arguments: dict[str, Any] = {}
    for name in required:
        if not isinstance(name, str):
            return None
        value = _find_state_value(state, name)
        if value is _MISSING or value is None:
            return None

        schema = properties.get(name)
        if isinstance(schema, dict):
            enum = schema.get("enum")
            if isinstance(enum, list) and enum and value not in enum:
                return None
            schema_type = schema.get("type")
            if schema_type == "object" and not isinstance(value, dict):
                return None

        arguments[name] = value

    return arguments


def _grounded_referential_call(
    definitions: list[dict[str, Any]],
    *,
    user_message: str,
    grounded_state: str,
) -> ProviderToolCall | None:
    """Bind a referential read directly when state satisfies the tool schema.

    The definitions reaching forced grounding have already been authorized and
    filtered for safety. For a short follow-up, prefer an exact grounded entity-ID
    capability over broader state-derived filters. This makes ``Did it complete?``
    resolve the execution that was just started rather than a later execution that
    merely happens to match the same source/status. Recoverable writes deliberately
    stay on the explicit write-recovery path below.
    """

    message = str(user_message or "")
    if not _REFERENTIAL_REQUEST.search(message):
        return None

    candidates: list[tuple[int, float, str, dict[str, Any]]] = []
    for item in CapabilityRetriever(definitions).rank(message):
        definition = item.definition
        name = str(definition.get("name") or "")
        if not name or name in RECOVERABLE_WRITE_CAPABILITIES:
            continue

        arguments = _grounded_required_arguments(
            definition,
            user_message=message,
            grounded_state=grounded_state,
        )
        if arguments is None:
            continue

        exact_id_arguments = sum(
            1
            for key in arguments
            if _normalized_key(key).endswith("id")
        )
        candidates.append((exact_id_arguments, item.score, name, arguments))

    if not candidates:
        return None

    _, _, name, arguments = max(
        candidates,
        key=lambda candidate: (candidate[0], candidate[1]),
    )
    return ProviderToolCall(name=name, arguments=arguments)


def force_grounding_tool_calls(
    *,
    provider,
    model: str,
    user_message: str,
    grounded_state: str,
    definitions: list[dict[str, Any]],
) -> list[Any]:
    """Constrained second-chance planner for models that answer without grounding.

    Capability choice is deterministic from the retrieved tool contracts. The model
    only fills arguments for that single selected capability. Read/knowledge tools
    are safe by default; a WRITE tool reaches this path only when it is explicitly
    allowlisted, non-destructive, highly relevant, and the user clearly requested
    the action. Referential follow-ups can reuse required arguments from grounded
    state instead of asking the model to guess them again.
    """

    grounded_call = _grounded_referential_call(
        definitions,
        user_message=user_message,
        grounded_state=grounded_state,
    )
    if grounded_call is not None:
        return [grounded_call]

    selected = primary_grounding_definition(definitions, user_message)
    if selected is None:
        return []

    selected_name = str(selected.get("name") or "")
    if not selected_name:
        return []

    grounded_arguments = _grounded_required_arguments(
        selected,
        user_message=user_message,
        grounded_state=grounded_state,
    )
    if grounded_arguments is not None:
        return [
            ProviderToolCall(
                name=selected_name,
                arguments=grounded_arguments,
            )
        ]

    messages = [
        {
            "role": "system",
            "content": (
                "You are the argument planner for one preselected IdentityAI capability. "
                "Do not answer the user and do not choose another capability. Fill the "
                "arguments for the supplied capability using only the user's request and "
                "grounded state. Use native tool calling when available. Otherwise output "
                "only one JSON object with keys name and arguments. Never invent internal "
                "IDs or values not supported by the request/state."
            ),
        },
        {
            "role": "user",
            "content": f"Request:\n{user_message}\n\nGrounded state:\n{grounded_state}",
        },
    ]

    response = provider.chat(model=model, messages=messages, tools=[selected])
    native_calls = [
        call
        for call in list(response.tool_calls or [])
        if getattr(call, "name", None) == selected_name
    ]
    if native_calls:
        return native_calls[:1]

    return extract_text_tool_calls(response.text, {selected_name})[:1]
