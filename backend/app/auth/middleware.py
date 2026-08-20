from fastapi import Request
from fastapi.responses import JSONResponse
from jwt import ExpiredSignatureError, InvalidTokenError
from app.auth.security import decode_access_token
from app.database.session import SessionLocal
from app.db_models.user import UserRecord

PUBLIC = {
    "/api/auth/login",
    "/api/auth/logout",
    "/api/health",
    "/api/health/",
    "/api/ai-health",
    "/api/ai-health/",
}

async def authentication_middleware(request: Request, call_next):
    if request.method == "OPTIONS" or not request.url.path.startswith("/api/") or request.url.path in PUBLIC:
        return await call_next(request)

    token = request.cookies.get("identityai_access_token")
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Authentication required."})

    try:
        user_id = int(decode_access_token(token)["sub"])
    except (ExpiredSignatureError, InvalidTokenError, KeyError, ValueError, TypeError):
        return JSONResponse(status_code=401, content={"detail": "Session expired or invalid."})

    db = SessionLocal()
    try:
        user = db.get(UserRecord, user_id)
        if user is None or not user.is_active:
            return JSONResponse(status_code=401, content={"detail": "Account unavailable."})
        request.state.user = user
        return await call_next(request)
    finally:
        db.close()
