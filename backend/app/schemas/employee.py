from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from backend.app.schemas.role import RoleOut

class EmployeeBase(BaseModel):
    role_id: int
    department_id: Optional[int] = None
    full_name: str = Field(..., max_length=150)
    is_active: bool = True

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(BaseModel):
    role_id: Optional[int] = None
    department_id: Optional[int] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None

class EmployeeOut(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    branch_id: int
    role_name: Optional[str] = None
    department_name: Optional[str] = None
    role: Optional[RoleOut] = None
    created_at: datetime
    updated_at: datetime
