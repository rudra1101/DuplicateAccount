from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CATALOG_DIR = Path(__file__).resolve().parent.parent / "service_catalog"


@dataclass(frozen=True)
class PermissionManifest:
    code: str
    name: str
    description: str


@dataclass(frozen=True)
class ServiceManifest:
    key: str
    name: str
    description: str
    category: str
    route: str | None
    icon: str | None
    enabled: bool
    sort_order: int
    permissions: tuple[PermissionManifest, ...]
    default_roles: dict[str, str | tuple[str, ...]]


@dataclass(frozen=True)
class SystemRoleManifest:
    name: str
    description: str


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid service catalog JSON in {path.name}: {exc}") from exc

    if not isinstance(data, dict):
        raise RuntimeError(f"Service catalog file {path.name} must contain a JSON object.")
    return data


def load_system_roles() -> tuple[SystemRoleManifest, ...]:
    path = CATALOG_DIR / "system_roles.json"
    data = _load_json(path)
    raw_roles = data.get("roles")
    if not isinstance(raw_roles, list) or not raw_roles:
        raise RuntimeError("system_roles.json must contain a non-empty roles array.")

    roles: list[SystemRoleManifest] = []
    for item in raw_roles:
        if not isinstance(item, dict):
            raise RuntimeError("Each system role entry must be an object.")
        name = str(item.get("name") or "").strip().upper()
        description = str(item.get("description") or "").strip()
        if not name:
            raise RuntimeError("System role name is required.")
        roles.append(SystemRoleManifest(name=name, description=description))
    return tuple(roles)


def load_service_manifests() -> tuple[ServiceManifest, ...]:
    manifests: list[ServiceManifest] = []
    permission_codes: set[str] = set()
    service_keys: set[str] = set()

    for path in sorted(CATALOG_DIR.glob("*.json")):
        if path.name == "system_roles.json":
            continue

        data = _load_json(path)
        raw_service = data.get("service")
        raw_permissions = data.get("permissions", [])
        raw_defaults = data.get("defaultRoles", {})

        if not isinstance(raw_service, dict):
            raise RuntimeError(f"{path.name} must contain a service object.")
        if not isinstance(raw_permissions, list):
            raise RuntimeError(f"{path.name} permissions must be an array.")
        if not isinstance(raw_defaults, dict):
            raise RuntimeError(f"{path.name} defaultRoles must be an object.")

        key = str(raw_service.get("key") or "").strip().lower()
        name = str(raw_service.get("name") or "").strip()
        if not key or not name:
            raise RuntimeError(f"{path.name} service.key and service.name are required.")
        if key in service_keys:
            raise RuntimeError(f"Duplicate service key in catalog: {key}")
        service_keys.add(key)

        permissions: list[PermissionManifest] = []
        local_codes: set[str] = set()
        for item in raw_permissions:
            if not isinstance(item, dict):
                raise RuntimeError(f"{path.name} permission entries must be objects.")
            code = str(item.get("code") or "").strip()
            permission_name = str(item.get("name") or "").strip()
            description = str(item.get("description") or permission_name).strip()
            if not code or not permission_name:
                raise RuntimeError(f"{path.name} permission code and name are required.")
            if code in permission_codes:
                raise RuntimeError(f"Duplicate permission code in catalog: {code}")
            permission_codes.add(code)
            local_codes.add(code)
            permissions.append(
                PermissionManifest(code=code, name=permission_name, description=description)
            )

        default_roles: dict[str, str | tuple[str, ...]] = {}
        for role_name, value in raw_defaults.items():
            normalized_role = str(role_name).strip().upper()
            if value == "ALL":
                default_roles[normalized_role] = "ALL"
                continue
            if not isinstance(value, list):
                raise RuntimeError(
                    f"{path.name} default role {normalized_role} must be ALL or an array."
                )
            codes = tuple(str(code).strip() for code in value if str(code).strip())
            unknown = sorted(set(codes) - local_codes)
            if unknown:
                raise RuntimeError(
                    f"{path.name} default role {normalized_role} references unknown permissions: "
                    + ", ".join(unknown)
                )
            default_roles[normalized_role] = codes

        manifests.append(
            ServiceManifest(
                key=key,
                name=name,
                description=str(raw_service.get("description") or "").strip(),
                category=str(raw_service.get("category") or name).strip(),
                route=(str(raw_service.get("route")).strip() if raw_service.get("route") else None),
                icon=(str(raw_service.get("icon")).strip() if raw_service.get("icon") else None),
                enabled=bool(raw_service.get("enabled", True)),
                sort_order=int(raw_service.get("sortOrder", 100)),
                permissions=tuple(permissions),
                default_roles=default_roles,
            )
        )

    if not manifests:
        raise RuntimeError(f"No service manifests found in {CATALOG_DIR}.")
    return tuple(manifests)
