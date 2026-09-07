from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal

class BranchTurnoverSummary(BaseModel):
    branch_id: int
    branch_name: str
    total_turnover: Decimal
    franchisor_share: Decimal
    bayi_share: Decimal
    transaction_count: int
    collector_party: str
    invoice_direction: str
    invoice_net_payable: Decimal

class FranchisorDashboardTotals(BaseModel):
    total_branches: int
    active_branches: int
    total_turnover: Decimal
    total_franchisor_share: Decimal
    total_bayi_share: Decimal
    total_transactions: int

class FranchisorDashboardResponse(BaseModel):
    year: int
    month: int
    totals: FranchisorDashboardTotals
    branches: List[BranchTurnoverSummary]

class MonthlyTrendItem(BaseModel):
    period: str
    year: int
    month: int
    turnover: Decimal
    franchisor_share: Decimal
    bayi_share: Decimal
    transaction_count: int

class DepartmentBreakdownItem(BaseModel):
    department_id: int
    department_name: str
    turnover: Decimal
    transaction_count: int
    percentage: Decimal

class TopEmployeeBonusItem(BaseModel):
    rank: int
    employee_id: int
    employee_name: str
    role_name: str
    department_name: Optional[str] = None
    turnover: Decimal
    bonus_amount: Decimal

class BranchDashboardSummary(BaseModel):
    branch_id: int
    branch_name: str
    year: int
    month: int
    total_turnover: Decimal
    franchisor_share: Decimal
    bayi_share: Decimal
    total_bonuses: Decimal
    net_bayi_margin: Decimal
    transaction_count: int
    collector_party: str

class BranchDashboardResponse(BaseModel):
    summary: BranchDashboardSummary
    monthly_trends: List[MonthlyTrendItem]
    department_breakdown: List[DepartmentBreakdownItem]
    top_bonus_employees: List[TopEmployeeBonusItem]
