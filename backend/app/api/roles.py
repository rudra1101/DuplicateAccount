from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import require_permission
from app.database.session import get_db
from app.db_models.permission import PermissionRecord
from app.db_models.role import RoleRecord
from app.db_models.user import UserRecord
from app.schemas.role import (
    PermissionResponse,
    RoleCreate,
    RolePermissionsUpdate,
    RoleResponse,
    RoleUpdate,
)
from app.services.rbac_service import permission_codes_for_role

router = APIRouter(prefix="/roles", tags=["Role Management"])


def serialize_role(role: RoleRecord) -> RoleResponse:
    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        isSystem=role.is_system,
        permissions=permission_codes_for_role(role),
    )


@router.get("/permissions", response_model=list[PermissionResponse])
def list_permissions(
    db: Session = Depends(get_db),
    _user=Depends(require_permission("role.view")),
):
    items = db.scalars(select(PermissionRecord).order_by(PermissionRecord.category, PermissionRecord.name)).all()
    return [
        PermissionResponse(
            id=item.id,
            code=item.code,
            name=item.name,
            description=item.description,
            category=item.category,
        )
        for item in items
    ]


@router.get("/", response_model=list[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    _user=Depends(require_permission("role.view")),
):
    roles = db.scalars(select(RoleRecord).order_by(RoleRecord.name)).all()
    return [serialize_role(role) for role in roles]


@router.post("/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("role.create")),
):
    name = payload.name.strip().upper()
    if db.scalar(select(RoleRecord).where(RoleRecord.name == name)) is not None:
        raise HTTPException(status_code=409, detail="Role already exists.")

    permission_map = {
        item.code: item for item in db.scalars(select(PermissionRecord)).all()
    }
    unknown = sorted(set(payload.permissions) - set(permission_map))
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown permissions: {', '.join(unknown)}")

    role = RoleRecord(name=name, description=payload.description.strip(), is_system=False)
    role.permissions = [permission_map[code] for code in sorted(set(payload.permissions))]
    db.add(role)
    db.commit()
    db.refresh(role)
    return serialize_role(role)


@router.put("/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: int,
    payload: RoleUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("role.edit")),
):
    role = db.get(RoleRecord, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found.")
    if role.name == "OWNER":
        raise HTTPException(status_code=400, detail="OWNER role cannot be modified.")

    role.description = payload.description.strip()
    db.commit()
    db.refresh(role)
    return serialize_role(role)


@router.put("/{role_id}/permissions", response_model=RoleResponse)
def update_role_permissions(
    role_id: int,
    payload: RolePermissionsUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("role.manage_permissions")),
):
    role = db.get(RoleRecord, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found.")
    if role.name == "OWNER":
        raise HTTPException(status_code=400, detail="OWNER permissions are fixed to unrestricted access.")

    permission_map = {
        item.code: item for item in db.scalars(select(PermissionRecord)).all()
    }
    unknown = sorted(set(payload.permissions) - set(permission_map))
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown permissions: {', '.join(unknown)}")

    role.permissions = [permission_map[code] for code in sorted(set(payload.permissions))]
    db.commit()
    db.refresh(role)
    return serialize_role(role)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("role.delete")),
):
    role = db.get(RoleRecord, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found.")
    if role.is_system:
        raise HTTPException(status_code=400, detail="System roles cannot be deleted.")

    assigned = db.scalar(select(func.count(UserRecord.id)).where(UserRecord.role == role.name)) or 0
    if assigned:
        raise HTTPException(status_code=409, detail="Role is assigned to one or more users.")

    db.delete(role)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
