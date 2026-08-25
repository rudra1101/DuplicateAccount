from fastapi import Request
from fastapi.responses import JSONResponse
from jwt import ExpiredSignatureError, InvalidTokenError

from app.ai.authorization import (
    permissions_for_user,
    reset_rudrix_permissions,
    set_rudrix_permissions,
)
from app.auth.security import decode_access_token
from app.database.session import SessionLocal
from app.db_models.user import UserRecord


PUBLIC_PATHS = {
    "/api/auth/login",
    "/api/auth/logout",
    "/api/health",
    "/api/health/",
    "/api/ai-health",
    "/api/ai-health/",
}


async def authentication_middleware(request: Request, call_next):
    path = request.url.path

    if request.method == "OPTIONS" or not path.startswith("/api/") or path in PUBLIC_PATHS:
        return await call_next(request)

    token = request.cookies.get("identityai_access_token")
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Authentication required."})

    try:
        user_id = int(decode_access_token(token)["sub"])
    except (ExpiredSignatureError, InvalidTokenError, KeyError, TypeError, ValueError):
        return JSONResponse(status_code=401, content={"detail": "Session expired or invalid."})

    db = SessionLocal()
    permission_token = None

    try:
        user = db.get(UserRecord, user_id)
        if user is None or not user.is_active:
            return JSONResponse(status_code=401, content={"detail": "Account unavailable."})

        request.state.user = user

        permission_token = set_rudrix_permissions(
            permissions_for_user(user)
        )

        return await call_next(request)
    finally:
        if permission_token is not None:
            reset_rudrix_permissions(permission_token)
        db.close()
