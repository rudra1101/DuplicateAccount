from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_models.permission import PermissionRecord
from app.db_models.role import RoleRecord
from app.db_models.service import ServiceRecord
from app.services.service_catalog_loader import (
    ServiceManifest,
    load_service_manifests,
    load_system_roles,
)


def _requested_permissions_for_role(
    manifest: ServiceManifest,
    role_name: str,
) -> set[str]:
    requested = manifest.default_roles.get(role_name.upper())
    if requested is None:
        return set()
    if requested == "ALL":
        return {permission.code for permission in manifest.permissions}
    return set(requested)


def seed_rbac(db: Session) -> None:
    """Synchronize deploy-time service manifests into the database.

    Runtime authorization reads permissions and role assignments from the DB.
    OWNER remains unrestricted for backward compatibility. SUPER_ADMIN is the
    operational super-administrator role and receives every declared platform
    permission. ADMIN is synchronized to the permissions explicitly granted by
    the service manifests, allowing sensitive capabilities such as ML training
    and model evaluation to remain super-admin only.
    """

    manifests = load_service_manifests()
    system_roles = load_system_roles()

    existing_services = {
        item.key: item
        for item in db.scalars(select(ServiceRecord)).all()
    }
    existing_permissions = {
        item.code: item
        for item in db.scalars(select(PermissionRecord)).all()
    }

    newly_created_permission_codes: set[str] = set()

    for manifest in manifests:
        service = existing_services.get(manifest.key)
        if service is None:
            service = ServiceRecord(
                key=manifest.key,
                name=manifest.name,
                description=manifest.description,
                category=manifest.category,
                route=manifest.route,
                icon=manifest.icon,
                enabled=manifest.enabled,
                sort_order=manifest.sort_order,
            )
            db.add(service)
            existing_services[manifest.key] = service
        else:
            service.name = manifest.name
            service.description = manifest.description
            service.category = manifest.category
            service.route = manifest.route
            service.icon = manifest.icon
            service.enabled = manifest.enabled
            service.sort_order = manifest.sort_order

        for permission_manifest in manifest.permissions:
            permission = existing_permissions.get(permission_manifest.code)
            if permission is None:
                permission = PermissionRecord(
                    code=permission_manifest.code,
                    name=permission_manifest.name,
                    description=permission_manifest.description,
                    category=manifest.category,
                )
                db.add(permission)
                db.flush()
                existing_permissions[permission_manifest.code] = permission
                newly_created_permission_codes.add(permission_manifest.code)
            else:
                permission.name = permission_manifest.name
                permission.description = permission_manifest.description
                permission.category = manifest.category

    existing_roles = {
        item.name.upper(): item
        for item in db.scalars(select(RoleRecord)).all()
    }

    newly_created_roles: set[str] = set()

    for role_manifest in system_roles:
        role_name = role_manifest.name.upper()
        role = existing_roles.get(role_name)
        if role is None:
            role = RoleRecord(
                name=role_name,
                description=role_manifest.description,
                is_system=True,
            )
            db.add(role)
            db.flush()
            existing_roles[role_name] = role
            newly_created_roles.add(role_name)
        else:
            role.is_system = True
            role.description = role_manifest.description

    all_permission_codes = set(existing_permissions)

    for role_manifest in system_roles:
        role_name = role_manifest.name.upper()
        role = existing_roles[role_name]
        current_codes = {permission.code for permission in role.permissions}

        requested_codes: set[str] = set()
        for manifest in manifests:
            requested_codes.update(
                _requested_permissions_for_role(manifest, role_name)
            )

        if role_name == "SUPER_ADMIN":
            desired_codes = all_permission_codes
        elif role_name == "ADMIN":
            # ADMIN is a managed system role. Keep it aligned with service
            # manifests so permissions removed from ADMIN (for example ML)
            # are actually revoked from existing installations as well.
            desired_codes = requested_codes
        elif role_name in newly_created_roles:
            desired_codes = requested_codes
        else:
            # Preserve administrator changes for normal roles. Only seed
            # defaults for permissions introduced by this deployment.
            desired_codes = current_codes | (
                requested_codes & newly_created_permission_codes
            )

        role.permissions = [
            existing_permissions[code]
            for code in sorted(desired_codes)
            if code in existing_permissions
        ]

    db.commit()


def permission_codes_for_role(role: RoleRecord | None) -> list[str]:
    if role is None:
        return []
    return sorted(permission.code for permission in role.permissions)
