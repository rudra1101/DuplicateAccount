from __future__ import annotations

from contextvars import ContextVar, Token

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db_models.role import RoleRecord
from app.services.rbac_service import permission_codes_for_role


_rudrix_permissions: ContextVar[frozenset[str] | None] = ContextVar(
    "rudrix_permissions",
    default=None,
)
_rudrix_actor: ContextVar[str | None] = ContextVar(
    "rudrix_actor",
    default=None,
)


def permissions_for_user(
    user,
    *,
    db: Session | None = None,
) -> frozenset[str]:
    raw_role_name = str(getattr(user, "role", "")).strip()
    role_name = raw_role_name.upper()

    if role_name == "OWNER":
        return frozenset({"*"})

    # Resolve current permissions from the request-scoped DB when possible.
    # Role names on older installations may use mixed casing (for example
    # ``Admin`` instead of ``ADMIN``), so the lookup must be case-insensitive.
    # This remains permission-based: only the permissions actually assigned to
    # the matched role are returned.
    if db is not None and raw_role_name and hasattr(db, "scalars"):
        role_record = db.scalars(
            select(RoleRecord)
            .where(func.lower(RoleRecord.name) == raw_role_name.lower())
            .limit(1)
        ).first()
        return frozenset(permission_codes_for_role(role_record))

    # Lightweight internal/test DB stubs may not expose ``scalars``. Fall back
    # to the relationship already attached to the authenticated user.
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


def set_rudrix_actor(actor: str | None) -> Token:
    value = str(actor or "").strip() or None
    return _rudrix_actor.set(value)


def reset_rudrix_actor(token: Token) -> None:
    _rudrix_actor.reset(token)


def get_rudrix_actor() -> str:
    return _rudrix_actor.get() or "Rudrix"


def has_rudrix_permission(permission: str) -> bool:
    permissions = get_rudrix_permissions()

    # None means no request-scoped authorization context exists. This keeps
    # direct internal calls and existing isolated unit/live tests backwards
    # compatible. Authenticated API requests always set a concrete set.
    if permissions is None:
        return True

    return "*" in permissions or permission in permissions
