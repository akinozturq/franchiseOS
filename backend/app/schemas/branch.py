from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class BranchBase(BaseModel):
    name: str
    tax_id: Optional[str] = None
    tax_office: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: bool = True

class BranchCreate(BranchBase):
    pass

class BranchUpdate(BaseModel):
    name: Optional[str] = None
    tax_id: Optional[str] = None
    tax_office: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None

class BranchOut(BranchBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    franchisor_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
