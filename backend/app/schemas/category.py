from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime, date

class TransactionCategoryBase(BaseModel):
    name: str = Field(..., max_length=150)
    general_override_rate: Optional[Decimal] = Field(default=None, ge=0, le=1, description="Franchisor-Bayi genel komisyon sabit istisna oranı (örn 0.15)")
    bonus_override_rate: Optional[Decimal] = Field(default=None, ge=0, le=1, description="Personel prim sabit istisna oranı (örn 0.07)")
    is_active: bool = True

class TransactionCategoryCreate(TransactionCategoryBase):
    pass

class TransactionCategoryUpdate(BaseModel):
    name: Optional[str] = None
    general_override_rate: Optional[Decimal] = None
    bonus_override_rate: Optional[Decimal] = None
    is_active: Optional[bool] = None

class TransactionCategoryOut(TransactionCategoryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    branch_id: int
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    created_at: datetime
    updated_at: datetime
