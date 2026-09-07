from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from decimal import Decimal
from backend.app.services.commission_service import (
    CollectorParty,
    TierDTO,
    DepartmentSummary,
    InvoiceSummary,
    ReconciliationResult
)

class ReconciliationQuery(BaseModel):
    year: int
    month: int
    collector_party: Optional[CollectorParty] = None
    default_vat_rate: Optional[Decimal] = None

class PeriodSettingUpdate(BaseModel):
    year: int
    month: int
    collector_party: CollectorParty
    vat_rate: Optional[Decimal] = Decimal("0.20")
    is_locked: Optional[bool] = False

class PeriodSettingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    branch_id: int
    year: int
    month: int
    collector_party: CollectorParty
    vat_rate: Decimal
    is_locked: bool


class ReconciliationResponse(ReconciliationResult):
    year: int
    month: int
    branch_name: str
    is_setting_persisted: bool = True
    is_locked: bool = False
    is_closed: bool = False
    closed_at: Optional[str] = None
    closed_by_name: Optional[str] = None

