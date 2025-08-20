# backend/app/schemas/user.py

from pydantic import BaseModel, computed_field
from typing import Optional
from .employee import EmployeeForUser

class UserBase(BaseModel):
    # Removed empno from UserBase
    name: str
    email: Optional[str] = None # Added email as optional string

class UserCreate(UserBase):
    password: str
    department: str
    is_supervisor: bool = False

class User(UserBase):
    id: int
    is_active: bool
    is_supervisor: bool
    employee: Optional[EmployeeForUser] = None

    @computed_field
    @property
    def empno(self) -> Optional[str]:
        return self.employee.empno if self.employee else None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    empno: Optional[str] = None # Changed from email: Optional[str]

class LoginResponse(BaseModel):
    token: Token
    user: User