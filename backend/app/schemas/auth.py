from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    fullName: str
    role: str
    permissions: list[str] = []
    isActive: bool


class AuthResponse(BaseModel):
    user: UserResponse


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: EmailStr
    fullName: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=12, max_length=1024)
    role: str = Field(min_length=1, max_length=100)


class UserRoleUpdate(BaseModel):
    role: str = Field(min_length=1, max_length=100)
