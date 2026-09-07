from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Any, Dict, List
from datetime import datetime

class PeriodClosureRequest(BaseModel):
    year: int
    month: int

class PeriodClosureCreate(BaseModel):
    year: int
    month: int

class PeriodClosureReopen(BaseModel):
    reopen_reason: str = Field(..., min_length=5, description="Yeniden acma zorunlu gerekcesi")

class PeriodClosureStatusOut(BaseModel):
    year: int
    month: int
    is_closed: bool
    status: Optional[str] = None
    closure_id: Optional[int] = None
    closed_at: Optional[datetime] = None
    closed_by_name: Optional[str] = None
    reopen_reason: Optional[str] = None

class PeriodClosureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    branch_id: int
    year: int
    month: int
    status: str
    closed_at: datetime
    closed_by_user_id: Optional[int] = None
    reconciliation_snapshot: Optional[Dict[str, Any]] = None
    bonus_snapshot: Optional[Dict[str, Any]] = None
    calculation_engine_version: Optional[str] = None
    input_hash: Optional[str] = None
    result_hash: Optional[str] = None
    reopened_at: Optional[datetime] = None
    reopened_by_user_id: Optional[int] = None
    reopen_reason: Optional[str] = None
    created_at: datetime

class InvoiceDataExportOut(BaseModel):
    document_id: str
    issue_date: str
    period: str
    currency: str = "TRY"
    invoice_direction: str
    collector_party: str
    issuer: Dict[str, Any]
    recipient: Dict[str, Any]
    amount_excl_vat: str
    vat_rate: str
    vat_amount: str
    total_amount_incl_vat: str
    line_items: List[Dict[str, Any]]
    closure_audit: Dict[str, Any]
