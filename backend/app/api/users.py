from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth import require_roles
from app.auth.security import hash_password
from app.database.session import get_db
from app.db_models.user import UserRecord
from app.schemas.auth import UserCreate, UserResponse


router = APIRouter(
    prefix="/users",
    tags=["User Management"],
    dependencies=[Depends(require_roles("ADMIN"))],
)


def serialize(user: UserRecord) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        fullName=user.full_name,
        role=user.role,
        isActive=user.is_active,
    )


@router.get("/", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db)):
    users = db.scalars(select(UserRecord).order_by(UserRecord.username)).all()
    return [serialize(user) for user in users]


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    username = payload.username.strip()
    email = payload.email.strip()

    existing = db.scalar(
        select(UserRecord).where(
            or_(UserRecord.username == username, UserRecord.email == email)
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Username or email already exists.")

    user = UserRecord(
        username=username,
        email=email,
        full_name=payload.fullName.strip(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return serialize(user)
