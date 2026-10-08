from __future__ import annotations

from typing import Any

from app.ai.agent_core.models import AgentCapability, CapabilityKind
from app.ai.tools.registry import TOOL_PERMISSION_MAP, AIToolRegistry


_CAPABILITY_METADATA: dict[str, dict[str, Any]] = {
    "get_dashboard_summary": {"domain": "dashboard", "kind": CapabilityKind.READ, "fast_path": True},
    "list_integrations": {"domain": "integration", "kind": CapabilityKind.READ},
    "get_integration_details": {"domain": "integration", "kind": CapabilityKind.READ},
    "investigate_accounts": {"domain": "account", "kind": CapabilityKind.READ, "fast_path": True},
    "search_orphan_accounts": {"domain": "orphan", "kind": CapabilityKind.READ, "fast_path": True},
    "get_operations_summary": {"domain": "operations", "kind": CapabilityKind.READ},
    "search_operations": {"domain": "operations", "kind": CapabilityKind.READ},
    "get_latest_execution": {"domain": "operations", "kind": CapabilityKind.READ},
    "get_execution_details": {"domain": "operations", "kind": CapabilityKind.READ},
    "get_duplicate_summary": {"domain": "duplicate", "kind": CapabilityKind.READ},
    "search_duplicate_groups": {"domain": "duplicate", "kind": CapabilityKind.READ, "fast_path": True},
    "get_duplicate_group_details": {"domain": "duplicate", "kind": CapabilityKind.READ},
    "get_review_statistics": {"domain": "duplicate", "kind": CapabilityKind.READ},
    "review_duplicate_candidate": {"domain": "duplicate", "kind": CapabilityKind.WRITE},
    "get_confidence_breakdown": {"domain": "duplicate", "kind": CapabilityKind.READ},
    "get_training_label_summary": {"domain": "ml", "kind": CapabilityKind.READ},
    "search_knowledge_base": {"domain": "knowledge", "kind": CapabilityKind.KNOWLEDGE},
    "list_knowledge_documents": {"domain": "knowledge", "kind": CapabilityKind.KNOWLEDGE},
    "generate_report": {"domain": "report", "kind": CapabilityKind.WRITE},
    "search_remediation_items": {"domain": "remediation", "kind": CapabilityKind.READ},
    "create_remediation_ticket": {"domain": "remediation", "kind": CapabilityKind.WRITE},
    "navigate_app": {"domain": "navigation", "kind": CapabilityKind.NAVIGATION, "fast_path": True},
}


class CapabilityCatalog:
    """Machine-readable catalog of everything Rudrix can do.

    The catalog is generated from the actual authorized tool registry, so the
    agent learns product capabilities from tool contracts instead of relying on
    sentence-specific prompt rules.
    """

    def __init__(self, registry: AIToolRegistry):
        self._registry = registry

    def capabilities(self) -> list[AgentCapability]:
        items: list[AgentCapability] = []
        for definition in self._registry.definitions():
            name = str(definition.get("name") or "")
            if not name:
                continue
            metadata = _CAPABILITY_METADATA.get(name, {})
            items.append(
                AgentCapability(
                    name=name,
                    domain=str(metadata.get("domain") or "general"),
                    kind=metadata.get("kind") or CapabilityKind.READ,
                    description=str(definition.get("description") or ""),
                    required_permission=TOOL_PERMISSION_MAP.get(name),
                    destructive=bool(metadata.get("destructive", False)),
                    fast_path=bool(metadata.get("fast_path", False)),
                    parameters=dict(definition.get("parameters") or {}),
                )
            )
        return items

    def compact_for_planner(self) -> list[dict[str, Any]]:
        """Return a low-token catalog suitable for a planner prompt."""
        return [
            {
                "name": item.name,
                "domain": item.domain,
                "kind": item.kind.value,
                "description": item.description,
                "destructive": item.destructive,
                "fastPath": item.fast_path,
            }
            for item in self.capabilities()
        ]
