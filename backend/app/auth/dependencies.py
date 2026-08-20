from fastapi import Depends, HTTPException, Request, status

def get_current_user(request: Request):
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return user

def require_roles(*roles: str):
    allowed = {role.upper() for role in roles}

    def dependency(user=Depends(get_current_user)):
        if str(user.role).upper() not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        return user

    return dependency
