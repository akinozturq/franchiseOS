from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from decimal import Decimal
from datetime import datetime, date

class CommissionTierBase(BaseModel):
    min_amount: Decimal = Field(..., ge=0, description="Alt sınır (TL)")
    max_amount: Optional[Decimal] = Field(None, ge=0, description="Üst sınır (TL, boş = sonsuz)")
    rate: Decimal = Field(..., ge=0, le=1, description="Bayi payı oranı (0.00 - 1.00 arası, örn: 0.30)")

class CommissionTierCreate(CommissionTierBase):
    pass

class CommissionTierUpdate(BaseModel):
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    rate: Optional[Decimal] = None

class CommissionTierOut(CommissionTierBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    branch_id: int
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    created_at: datetime
    updated_at: datetime

class CommissionTierBatch(BaseModel):

    tiers: List[CommissionTierCreate]
