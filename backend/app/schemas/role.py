from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from decimal import Decimal
from datetime import datetime, date

class RoleCommissionTierBase(BaseModel):
    min_amount: Decimal = Field(..., ge=0, description="Alt sınır (TL)")
    max_amount: Optional[Decimal] = Field(default=None, ge=0, description="Üst sınır (TL, boş = sonsuz)")
    rate: Decimal = Field(..., ge=0, le=1, description="Prim oranı (örn 0.05 -> %5)")

class RoleCommissionTierCreate(RoleCommissionTierBase):
    pass

class RoleCommissionTierOut(RoleCommissionTierBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role_id: int
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    created_at: datetime
    updated_at: datetime

class RoleBase(BaseModel):
    name: str = Field(..., max_length=100)
    turnover_source: str = Field(default="kendi_islemleri", description="kendi_islemleri | kendi_departmani | tum_bayi")
    is_active: bool = True

class RoleCreate(RoleBase):
    tiers: Optional[List[RoleCommissionTierCreate]] = []

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    turnover_source: Optional[str] = None
    is_active: Optional[bool] = None
    tiers: Optional[List[RoleCommissionTierCreate]] = None

class RoleOut(RoleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    branch_id: int
    commission_tiers: List[RoleCommissionTierOut] = []
    created_at: datetime
    updated_at: datetime
