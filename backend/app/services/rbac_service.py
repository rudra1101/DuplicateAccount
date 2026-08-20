from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_models.permission import PermissionRecord
from app.db_models.role import RoleRecord

PERMISSIONS = [
    ("dashboard.view", "View dashboard", "Dashboard"),
    ("duplicate.view", "View duplicate detection", "Duplicates"),
    ("duplicate.review", "Review duplicate accounts", "Duplicates"),
    ("report.view", "View reports", "Reports"),
    ("integration.view", "View integrations", "Integrations"),
    ("integration.run", "Run integrations", "Integrations"),
    ("integration.schedule", "Manage integration schedules", "Integrations"),
    ("integration.create", "Create integrations", "Integrations"),
    ("integration.edit", "Edit integrations", "Integrations"),
    ("integration.delete", "Delete integrations", "Integrations"),
    ("integration.test", "Test integrations", "Integrations"),
    ("upload.manage", "Upload account data", "Data"),
    ("operations.view", "View operations", "Operations"),
    ("settings.view", "View settings", "Settings"),
    ("ml.view", "View ML training", "Machine Learning"),
    ("ml.train", "Run ML training", "Machine Learning"),
    ("knowledge.view", "View knowledge base", "Knowledge"),
    ("knowledge.manage", "Manage knowledge base", "Knowledge"),
    ("user.view", "View users", "Administration"),
    ("user.create", "Create users", "Administration"),
    ("user.edit", "Edit users", "Administration"),
    ("user.disable", "Disable users", "Administration"),
    ("user.assign_role", "Assign roles to users", "Administration"),
    ("role.view", "View roles and permissions", "Administration"),
    ("role.create", "Create roles", "Administration"),
    ("role.edit", "Edit roles", "Administration"),
    ("role.delete", "Delete roles", "Administration"),
    ("role.manage_permissions", "Manage role permissions", "Administration"),
]

DEFAULT_ROLE_PERMISSIONS = {
    "OWNER": "ALL",
    "ADMIN": {
        code for code, _, _ in PERMISSIONS if not code.startswith("role.")
    },
    "USER": {
        "dashboard.view",
        "duplicate.view",
        "report.view",
        "integration.view",
        "integration.run",
        "integration.schedule",
        "operations.view",
        "settings.view",
        "knowledge.view",
    },
}

ROLE_DESCRIPTIONS = {
    "OWNER": "System owner with unrestricted access and role-management authority.",
    "ADMIN": "Application administrator. Can manage users and integrations but cannot change role definitions.",
    "USER": "Standard operational user with run and schedule capabilities.",
}


def seed_rbac(db: Session) -> None:
    existing_permissions = {
        item.code: item for item in db.scalars(select(PermissionRecord)).all()
    }

    for code, name, category in PERMISSIONS:
        if code not in existing_permissions:
            item = PermissionRecord(code=code, name=name, description=name, category=category)
            db.add(item)
            db.flush()
            existing_permissions[code] = item

    existing_roles = {
        item.name: item for item in db.scalars(select(RoleRecord)).all()
    }

    for role_name in ("OWNER", "ADMIN", "USER"):
        role = existing_roles.get(role_name)
        if role is None:
            role = RoleRecord(
                name=role_name,
                description=ROLE_DESCRIPTIONS[role_name],
                is_system=True,
            )
            db.add(role)
            db.flush()
            existing_roles[role_name] = role

        # Seed defaults only when a system role has no permissions yet so OWNER can
        # later customize ADMIN/USER without startup overwriting those choices.
        if not role.permissions:
            requested = DEFAULT_ROLE_PERMISSIONS[role_name]
            if requested == "ALL":
                role.permissions = list(existing_permissions.values())
            else:
                role.permissions = [existing_permissions[code] for code in requested]

    db.commit()


def permission_codes_for_role(role: RoleRecord | None) -> list[str]:
    if role is None:
        return []
    if role.name == "OWNER":
        return sorted(code for code, _, _ in PERMISSIONS)
    return sorted(permission.code for permission in role.permissions)
