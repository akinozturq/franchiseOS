from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from decimal import Decimal

class EmployeeBonusItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: int
    employee_name: str
    role_id: int
    role_name: str
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    turnover_source: str
    transaction_count: int
    
    standard_turnover_excl_vat: Decimal
    standard_tier_rate: Decimal
    standard_bonus: Decimal
    
    override_turnover_excl_vat: Decimal
    override_bonus: Decimal
    
    total_turnover_excl_vat: Decimal
    total_bonus: Decimal
    effective_bonus_rate: Decimal
    tier_explanation: str

class PeriodBonusReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period: str
    total_employees: int
    total_transactions: int
    total_turnover_excl_vat: Decimal
    grand_total_bonus: Decimal
    items: List[EmployeeBonusItemSchema]
    is_closed: bool = False
    closed_at: Optional[str] = None
    closed_by_name: Optional[str] = None
