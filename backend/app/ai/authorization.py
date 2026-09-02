from __future__ import annotations

from contextvars import ContextVar, Token

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_models.role import RoleRecord
from app.services.rbac_service import permission_codes_for_role


_rudrix_permissions: ContextVar[frozenset[str] | None] = ContextVar(
    "rudrix_permissions",
    default=None,
)


def permissions_for_user(
    user,
    *,
    db: Session | None = None,
) -> frozenset[str]:
    role_name = str(getattr(user, "role", "")).upper()

    if role_name == "OWNER":
        return frozenset({"*"})

    # When a request-scoped database session is available, resolve the role
    # directly from that session. This avoids relying on a role relationship
    # attached to the authentication middleware's separate database session and
    # ensures newly assigned permissions are reflected consistently in Rudrix.
    if db is not None and role_name:
        role_record = db.scalars(
            select(RoleRecord)
            .where(RoleRecord.name == role_name)
            .limit(1)
        ).first()
        return frozenset(permission_codes_for_role(role_record))

    return frozenset(
        permission_codes_for_role(
            getattr(user, "role_record", None)
        )
    )


def set_rudrix_permissions(
    permissions: frozenset[str] | set[str] | list[str],
) -> Token:
    return _rudrix_permissions.set(frozenset(permissions))


def reset_rudrix_permissions(token: Token) -> None:
    _rudrix_permissions.reset(token)


def get_rudrix_permissions() -> frozenset[str] | None:
    return _rudrix_permissions.get()


def has_rudrix_permission(permission: str) -> bool:
    permissions = get_rudrix_permissions()

    # None means no request-scoped authorization context exists. This keeps
    # direct internal calls and existing isolated unit/live tests backwards
    # compatible. Authenticated API requests always set a concrete set.
    if permissions is None:
        return True

    return "*" in permissions or permission in permissions
