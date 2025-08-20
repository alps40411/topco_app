# backend/app/schemas/user.py

from pydantic import BaseModel, EmailStr
from typing import Optional
from .employee import EmployeeForUser
from .employee import EmployeeForUser

class UserBase(BaseModel):
    email: EmailStr
    name: str

class UserCreate(UserBase):
    password: str
    department: str
    is_supervisor: bool = False

class User(UserBase):
    id: int
    is_active: bool
    is_supervisor: bool
    employee: Optional[EmployeeForUser] = None
    employee: Optional[EmployeeForUser] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class LoginResponse(BaseModel):
    token: Token
    user: User