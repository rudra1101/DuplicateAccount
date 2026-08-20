from pydantic import BaseModel, Field


class PermissionResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str
    category: str


class RoleResponse(BaseModel):
    id: int
    name: str
    description: str
    isSystem: bool
    permissions: list[str]


class RoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(default="", max_length=1000)
    permissions: list[str] = []


class RoleUpdate(BaseModel):
    description: str = Field(default="", max_length=1000)


class RolePermissionsUpdate(BaseModel):
    permissions: list[str]
