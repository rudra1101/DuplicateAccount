from __future__ import annotations

from contextvars import ContextVar, Token

from app.services.rbac_service import permission_codes_for_role


_rudrix_permissions: ContextVar[frozenset[str] | None] = ContextVar(
    "rudrix_permissions",
    default=None,
)


def permissions_for_user(user) -> frozenset[str]:
    if str(getattr(user, "role", "")).upper() == "OWNER":
        return frozenset({"*"})

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
