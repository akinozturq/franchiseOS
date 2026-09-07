from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    full_name: Optional[str] = None
    role: str
    franchisor_id: Optional[int] = None
    branch_id: Optional[int] = None

class UserBase(BaseModel):
    username: str
    full_name: Optional[str] = None
    role: str = "BAYI_ADMIN"
    branch_id: Optional[int] = None
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    branch_id: Optional[int] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: Optional[str] = None
    role: str
    franchisor_id: Optional[int] = None
    branch_id: Optional[int] = None
    is_active: bool
    created_at: datetime
