from typing import Literal
from pydantic import BaseModel, EmailStr, Field

Role = Literal["ADMIN", "USER"]

class LoginRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    fullName: str
    role: Role
    isActive: bool

class AuthResponse(BaseModel):
    user: UserResponse

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: EmailStr
    fullName: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=12, max_length=1024)
    role: Role
