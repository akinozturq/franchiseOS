from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict
from pydantic import BaseModel

def quantize_money(amount: Decimal) -> Decimal:
    """Round to 2 decimal places using standard half-up rounding."""
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class RoleTierDTO(BaseModel):
    id: Optional[int] = None
    min_amount: Decimal
    max_amount: Optional[Decimal] = None  # None = infinity
    rate: Decimal  # e.g. Decimal("0.05") for 5%


class BonusTransactionDTO(BaseModel):
    id: int
    employee_id: Optional[int] = None
    employee_name: Optional[str] = None
    department_id: int
    department_name: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    bonus_override_rate: Optional[Decimal] = None  # Sabit istisna prim oranı (örn: 0.07 -> %7)
    amount_excl_vat: Decimal


class EmployeeDTO(BaseModel):
    id: int
    full_name: str
    role_id: int
    role_name: str
    turnover_source: str  # "kendi_islemleri" | "kendi_departmani" | "tum_bayi"
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    is_active: bool = True
    commission_tiers: List[RoleTierDTO] = []


class EmployeeBonusItem(BaseModel):
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
    effective_bonus_rate: Decimal  # total_bonus / total_turnover
    tier_explanation: str


class PeriodBonusReportResult(BaseModel):
    period: str
    total_employees: int
    total_transactions: int
    total_turnover_excl_vat: Decimal
    grand_total_bonus: Decimal
    items: List[EmployeeBonusItem]


def find_applicable_role_tier(turnover: Decimal, tiers: List[RoleTierDTO]) -> Optional[RoleTierDTO]:
    """
    Finds the applicable role commission tier for the given turnover.
    Tiers are evaluated such that turnover falls within [min_amount, max_amount].
    If max_amount is None, tier applies for min_amount to infinity.
    """
    if not tiers:
        return None

    sorted_tiers = sorted(tiers, key=lambda t: t.min_amount)

    for tier in sorted_tiers:
        if tier.max_amount is not None:
            if tier.min_amount <= turnover <= tier.max_amount:
                return tier
        else:
            if tier.min_amount <= turnover:
                return tier

    return sorted_tiers[-1] if turnover >= sorted_tiers[-1].min_amount else None


def calculate_employee_bonus(
    employee: EmployeeDTO,
    all_period_transactions: List[BonusTransactionDTO]
) -> EmployeeBonusItem:
    """
    Calculates bonus for a single employee based on their role, turnover_source,
    role commission tiers, and transaction category override rates.
    
    Calculation order:
    1. Filter transactions according to employee's role.turnover_source:
       - 'kendi_islemleri': tx.employee_id == employee.id
       - 'kendi_departmani': tx.department_id == employee.department_id
       - 'tum_bayi': all transactions
    2. Separate filtered transactions into:
       - Category Override transactions (bonus_override_rate is not None)
       - Standard transactions (bonus_override_rate is None)
    3. Category Override bonus = sum(quantize_money(tx.amount_excl_vat * tx.bonus_override_rate))
    4. Standard bonus = find tier for standard_turnover in employee.commission_tiers ->
       quantize_money(standard_turnover * tier.rate)
    5. Total bonus = override_bonus + standard_bonus
    """
    # 1. Filter relevant transactions
    source = employee.turnover_source or "kendi_islemleri"
    if source == "kendi_islemleri":
        relevant_txs = [tx for tx in all_period_transactions if tx.employee_id == employee.id]
    elif source == "kendi_departmani":
        relevant_txs = [tx for tx in all_period_transactions if employee.department_id is not None and tx.department_id == employee.department_id]
    elif source == "tum_bayi":
        relevant_txs = list(all_period_transactions)
    else:
        # Default fallback to own transactions
        relevant_txs = [tx for tx in all_period_transactions if tx.employee_id == employee.id]

    tx_count = len(relevant_txs)

    # 2. Separate into override and standard
    override_txs = [tx for tx in relevant_txs if tx.bonus_override_rate is not None]
    standard_txs = [tx for tx in relevant_txs if tx.bonus_override_rate is None]

    override_turnover = sum((quantize_money(tx.amount_excl_vat) for tx in override_txs), Decimal("0.00"))
    standard_turnover = sum((quantize_money(tx.amount_excl_vat) for tx in standard_txs), Decimal("0.00"))
    total_turnover = override_turnover + standard_turnover

    # 3. Calculate Override Bonus
    override_bonus = sum(
        (quantize_money(tx.amount_excl_vat * tx.bonus_override_rate) for tx in override_txs),
        Decimal("0.00")
    )

    # 4. Calculate Standard Bonus using Role Tiers
    applicable_tier = find_applicable_role_tier(standard_turnover, employee.commission_tiers)
    if applicable_tier and standard_turnover > Decimal("0.00"):
        standard_rate = applicable_tier.rate
        standard_bonus = quantize_money(standard_turnover * standard_rate)
        max_str = f"{applicable_tier.max_amount:,.2f} TL" if applicable_tier.max_amount is not None else "Sonsuz"
        tier_explanation = (
            f"Standart ciro ({standard_turnover:,.2f} TL) "
            f"[{applicable_tier.min_amount:,.2f} TL - {max_str}] "
            f"dilimine düşmektedir (%{standard_rate * Decimal('100'):.2f})."
        )
    else:
        standard_rate = Decimal("0.00")
        standard_bonus = Decimal("0.00")
        if standard_turnover > Decimal("0.00"):
            tier_explanation = f"Standart ciro ({standard_turnover:,.2f} TL) için geçerli kademe bulunamadı."
        else:
            tier_explanation = "Standart ciro bulunmuyor."

    if override_txs:
        tier_explanation += (
            f" Ayrıca {len(override_txs)} adet istisnalı işlemde ({override_turnover:,.2f} TL) "
            f"sabit prim oranı uygulandı."
        )

    # 5. Combine Totals
    total_bonus = override_bonus + standard_bonus
    effective_rate = (total_bonus / total_turnover).quantize(Decimal("0.0001")) if total_turnover > Decimal("0.00") else Decimal("0.0000")

    return EmployeeBonusItem(
        employee_id=employee.id,
        employee_name=employee.full_name,
        role_id=employee.role_id,
        role_name=employee.role_name,
        department_id=employee.department_id,
        department_name=employee.department_name,
        turnover_source=source,
        transaction_count=tx_count,
        standard_turnover_excl_vat=standard_turnover,
        standard_tier_rate=standard_rate,
        standard_bonus=standard_bonus,
        override_turnover_excl_vat=override_turnover,
        override_bonus=override_bonus,
        total_turnover_excl_vat=total_turnover,
        total_bonus=total_bonus,
        effective_bonus_rate=effective_rate,
        tier_explanation=tier_explanation
    )


def calculate_period_bonuses(
    period: str,
    employees: List[EmployeeDTO],
    all_period_transactions: List[BonusTransactionDTO]
) -> PeriodBonusReportResult:
    """
    Calculates bonus report for all active employees for the specified period.
    Returns individual breakdown + grand total bonus.
    """
    items: List[EmployeeBonusItem] = []
    
    for emp in employees:
        item = calculate_employee_bonus(emp, all_period_transactions)
        items.append(item)

    # Sort items by total_bonus descending, then by employee_name
    items.sort(key=lambda x: (x.total_bonus, x.total_turnover_excl_vat), reverse=True)

    total_tx_count = len(all_period_transactions)
    total_turnover = sum((quantize_money(tx.amount_excl_vat) for tx in all_period_transactions), Decimal("0.00"))
    grand_total_bonus = sum((item.total_bonus for item in items), Decimal("0.00"))

    return PeriodBonusReportResult(
        period=period,
        total_employees=len(employees),
        total_transactions=total_tx_count,
        total_turnover_excl_vat=total_turnover,
        grand_total_bonus=grand_total_bonus,
        items=items
    )
