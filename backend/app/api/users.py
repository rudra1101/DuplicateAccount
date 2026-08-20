from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth import get_current_user, has_permission, require_permission
from app.auth.security import hash_password
from app.database.session import get_db
from app.db_models.role import RoleRecord
from app.db_models.user import UserRecord
from app.schemas.auth import UserCreate, UserResponse, UserRoleUpdate
from app.services.rbac_service import permission_codes_for_role

router = APIRouter(prefix="/users", tags=["User Management"])


def serialize(user: UserRecord) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        fullName=user.full_name,
        role=user.role,
        permissions=permission_codes_for_role(user.role_record),
        isActive=user.is_active,
    )


def validate_assignable_role(db: Session, role_name: str, actor) -> RoleRecord:
    normalized = role_name.strip().upper()
    role = db.scalar(select(RoleRecord).where(RoleRecord.name == normalized))
    if role is None:
        raise HTTPException(status_code=400, detail="Role does not exist.")
    if normalized == "OWNER" and str(actor.role).upper() != "OWNER":
        raise HTTPException(status_code=403, detail="Only OWNER can assign the OWNER role.")
    return role


@router.get("/", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _user=Depends(require_permission("user.view")),
):
    users = db.scalars(select(UserRecord).order_by(UserRecord.username)).all()
    return [serialize(user) for user in users]


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    actor=Depends(get_current_user),
):
    if not has_permission(actor, "user.create"):
        raise HTTPException(status_code=403, detail="Missing permission: user.create")

    username = payload.username.strip()
    email = payload.email.strip()
    role = validate_assignable_role(db, payload.role, actor)

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
        role=role.name,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return serialize(user)


@router.put("/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    actor=Depends(get_current_user),
):
    if not has_permission(actor, "user.assign_role"):
        raise HTTPException(status_code=403, detail="Missing permission: user.assign_role")

    user = db.get(UserRecord, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    role = validate_assignable_role(db, payload.role, actor)
    if user.role == "OWNER" and str(actor.role).upper() != "OWNER":
        raise HTTPException(status_code=403, detail="Only OWNER can change an OWNER account.")

    user.role = role.name
    db.commit()
    db.refresh(user)
    return serialize(user)
