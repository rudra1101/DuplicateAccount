import os

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.security import create_access_token, verify_password
from app.database.session import get_db
from app.db_models.user import UserRecord
from app.schemas.auth import AuthResponse, LoginRequest, UserResponse


router = APIRouter(prefix="/auth", tags=["Authentication"])


def serialize(user: UserRecord) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        fullName=user.full_name,
        role=user.role,
        isActive=user.is_active,
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    identifier = payload.username.strip()
    user = db.scalar(
        select(UserRecord).where(
            or_(UserRecord.username == identifier, UserRecord.email == identifier)
        )
    )

    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    token = create_access_token(user.id, user.username, user.role)
    response.set_cookie(
        key="identityai_access_token",
        value=token,
        httponly=True,
        secure=os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
        path="/",
        max_age=int(os.getenv("AUTH_ACCESS_TOKEN_MINUTES", "480")) * 60,
    )

    return AuthResponse(user=serialize(user))


@router.get("/me", response_model=AuthResponse)
def me(user=Depends(get_current_user)):
    return AuthResponse(user=serialize(user))


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("identityai_access_token", path="/")
    return {"message": "Signed out successfully."}
