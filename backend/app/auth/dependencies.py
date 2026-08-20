from fastapi import Depends, HTTPException, Request, status

from app.services.rbac_service import permission_codes_for_role


def get_current_user(request: Request):
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    return user


def has_permission(user, permission: str) -> bool:
    if str(user.role).upper() == "OWNER":
        return True
    return permission in set(permission_codes_for_role(user.role_record))


def require_permission(permission: str):
    def dependency(user=Depends(get_current_user)):
        if not has_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )
        return user

    return dependency


def require_any_permission(*permissions: str):
    def dependency(user=Depends(get_current_user)):
        if not any(has_permission(user, permission) for permission in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied.",
            )
        return user

    return dependency


# Kept temporarily for backwards compatibility while older endpoints migrate.
def require_roles(*roles: str):
    allowed = {role.upper() for role in roles}

    def dependency(user=Depends(get_current_user)):
        if str(user.role).upper() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied.",
            )
        return user

    return dependency
