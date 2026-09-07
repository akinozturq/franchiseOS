from decimal import Decimal
import pytest

from backend.app.services.bonus_service import (
    RoleTierDTO,
    BonusTransactionDTO,
    EmployeeDTO,
    find_applicable_role_tier,
    calculate_employee_bonus,
    calculate_period_bonuses,
    quantize_money,
)

@pytest.fixture
def sales_advisor_role_tiers():
    return [
        RoleTierDTO(min_amount=Decimal("0.00"), max_amount=Decimal("150000.00"), rate=Decimal("0.05")),
        RoleTierDTO(min_amount=Decimal("150000.01"), max_amount=Decimal("300000.00"), rate=Decimal("0.07")),
        RoleTierDTO(min_amount=Decimal("300000.01"), max_amount=None, rate=Decimal("0.09")),
    ]

@pytest.fixture
def general_manager_role_tiers():
    return [
        RoleTierDTO(min_amount=Decimal("0.00"), max_amount=Decimal("500000.00"), rate=Decimal("0.02")),
        RoleTierDTO(min_amount=Decimal("500000.01"), max_amount=Decimal("1000000.00"), rate=Decimal("0.03")),
        RoleTierDTO(min_amount=Decimal("1000000.01"), max_amount=None, rate=Decimal("0.04")),
    ]

def test_find_applicable_role_tier(sales_advisor_role_tiers):
    # Exactly 0.00 -> first tier (0.05)
    t0 = find_applicable_role_tier(Decimal("0.00"), sales_advisor_role_tiers)
    assert t0 is not None and t0.rate == Decimal("0.05")

    # Boundary exact 150,000.00 -> first tier (0.05)
    t1 = find_applicable_role_tier(Decimal("150000.00"), sales_advisor_role_tiers)
    assert t1 is not None and t1.rate == Decimal("0.05")

    # Boundary just above 150,000.01 -> second tier (0.07)
    t2 = find_applicable_role_tier(Decimal("150000.01"), sales_advisor_role_tiers)
    assert t2 is not None and t2.rate == Decimal("0.07")

    # Middle 250,000.00 -> second tier (0.07)
    t3 = find_applicable_role_tier(Decimal("250000.00"), sales_advisor_role_tiers)
    assert t3 is not None and t3.rate == Decimal("0.07")

    # Boundary exact 300,000.00 -> second tier (0.07)
    t4 = find_applicable_role_tier(Decimal("300000.00"), sales_advisor_role_tiers)
    assert t4 is not None and t4.rate == Decimal("0.07")

    # Boundary just above 300,000.01 -> third tier (0.09)
    t5 = find_applicable_role_tier(Decimal("300000.01"), sales_advisor_role_tiers)
    assert t5 is not None and t5.rate == Decimal("0.09")

    # High amount 1,500,000.00 -> third tier (0.09)
    t6 = find_applicable_role_tier(Decimal("1500000.00"), sales_advisor_role_tiers)
    assert t6 is not None and t6.rate == Decimal("0.09")


def test_employee_bonus_standard_only(sales_advisor_role_tiers):
    """
    Employee with only standard transactions (no category overrides).
    Turnover: 200,000 TL -> falls into 150,000.01-300,000 tier (%7).
    Bonus: 200,000 * 0.07 = 14,000 TL.
    """
    emp = EmployeeDTO(
        id=1,
        full_name="Ahmet Danışman",
        role_id=1,
        role_name="Satış Danışmanı",
        turnover_source="kendi_islemleri",
        department_id=1,
        commission_tiers=sales_advisor_role_tiers
    )
    txs = [
        BonusTransactionDTO(id=1, employee_id=1, department_id=1, amount_excl_vat=Decimal("120000.00")),
        BonusTransactionDTO(id=2, employee_id=1, department_id=1, amount_excl_vat=Decimal("80000.00")),
        # Another employee's transaction - should NOT be counted
        BonusTransactionDTO(id=3, employee_id=2, department_id=1, amount_excl_vat=Decimal("50000.00")),
    ]

    res = calculate_employee_bonus(emp, txs)
    assert res.transaction_count == 2
    assert res.standard_turnover_excl_vat == Decimal("200000.00")
    assert res.override_turnover_excl_vat == Decimal("0.00")
    assert res.total_turnover_excl_vat == Decimal("200000.00")
    assert res.standard_tier_rate == Decimal("0.07")
    assert res.standard_bonus == Decimal("14000.00")
    assert res.override_bonus == Decimal("0.00")
    assert res.total_bonus == Decimal("14000.00")
    assert res.effective_bonus_rate == Decimal("0.0700")


def test_employee_bonus_mixed_standard_and_category_override(sales_advisor_role_tiers):
    """
    Mixed scenario:
    Standard turnover: 100,000 TL -> falls into 0-150,000 tier (%5) -> 5,000 TL.
    Override turnover (Komple PPF %7): 50,000 TL -> 50,000 * 0.07 = 3,500 TL.
    Total bonus = 5,000 + 3,500 = 8,500 TL.
    Total turnover = 150,000 TL.
    """
    emp = EmployeeDTO(
        id=1,
        full_name="Merve Satış",
        role_id=1,
        role_name="Satış Danışmanı",
        turnover_source="kendi_islemleri",
        department_id=1,
        commission_tiers=sales_advisor_role_tiers
    )
    txs = [
        BonusTransactionDTO(id=1, employee_id=1, department_id=1, bonus_override_rate=None, amount_excl_vat=Decimal("100000.00")),
        BonusTransactionDTO(id=2, employee_id=1, department_id=1, bonus_override_rate=Decimal("0.07"), amount_excl_vat=Decimal("50000.00")),
    ]

    res = calculate_employee_bonus(emp, txs)
    assert res.transaction_count == 2
    assert res.standard_turnover_excl_vat == Decimal("100000.00")
    assert res.override_turnover_excl_vat == Decimal("50000.00")
    assert res.total_turnover_excl_vat == Decimal("150000.00")
    assert res.standard_bonus == Decimal("5000.00")
    assert res.override_bonus == Decimal("3500.00")
    assert res.total_bonus == Decimal("8500.00")
    # Effective rate: 8,500 / 150,000 = 0.0567
    assert res.effective_bonus_rate == Decimal("0.0567")


def test_turnover_source_kendi_departmani():
    """
    Role with turnover_source='kendi_departmani' (e.g. Satış Müdürü).
    Should pool all transactions belonging to that department, regardless of employee_id.
    """
    tiers = [
        RoleTierDTO(min_amount=Decimal("0.00"), max_amount=Decimal("300000.00"), rate=Decimal("0.04")),
        RoleTierDTO(min_amount=Decimal("300000.01"), max_amount=None, rate=Decimal("0.05")),
    ]
    emp = EmployeeDTO(
        id=10,
        full_name="Mehmet Satış Müdürü",
        role_id=2,
        role_name="Satış Müdürü",
        turnover_source="kendi_departmani",
        department_id=1,
        commission_tiers=tiers
    )
    txs = [
        # In department 1 (various employees)
        BonusTransactionDTO(id=1, employee_id=1, department_id=1, amount_excl_vat=Decimal("200000.00")),
        BonusTransactionDTO(id=2, employee_id=2, department_id=1, amount_excl_vat=Decimal("150000.00")),
        # In department 2 - should NOT be included
        BonusTransactionDTO(id=3, employee_id=3, department_id=2, amount_excl_vat=Decimal("100000.00")),
    ]

    res = calculate_employee_bonus(emp, txs)
    assert res.transaction_count == 2
    assert res.total_turnover_excl_vat == Decimal("350000.00")
    # 350,000 falls in >300,000 tier (%5)
    assert res.standard_tier_rate == Decimal("0.05")
    assert res.total_bonus == Decimal("17500.00")


def test_turnover_source_tum_bayi(general_manager_role_tiers):
    """
    Role with turnover_source='tum_bayi' (e.g. Genel Müdür).
    Calculates bonus over ALL branch transactions across all departments.
    """
    emp = EmployeeDTO(
        id=99,
        full_name="Serdar Genel Müdür",
        role_id=5,
        role_name="Genel Müdür",
        turnover_source="tum_bayi",
        department_id=None,
        commission_tiers=general_manager_role_tiers
    )
    txs = [
        BonusTransactionDTO(id=1, employee_id=1, department_id=1, amount_excl_vat=Decimal("400000.00")),
        BonusTransactionDTO(id=2, employee_id=2, department_id=2, amount_excl_vat=Decimal("300000.00")),
        BonusTransactionDTO(id=3, employee_id=3, department_id=3, amount_excl_vat=Decimal("150000.00")),
    ]

    res = calculate_employee_bonus(emp, txs)
    assert res.transaction_count == 3
    # Total turnover = 850,000 TL
    assert res.total_turnover_excl_vat == Decimal("850000.00")
    # 850,000 falls in [500,000.01 - 1,000,000] tier (%3)
    assert res.standard_tier_rate == Decimal("0.03")
    assert res.total_bonus == Decimal("25500.00")


def test_calculate_period_bonuses_grand_total(sales_advisor_role_tiers, general_manager_role_tiers):
    """
    Period bonus report with multiple employees:
    Ensures individual items are ordered and grand total matches sum of items.
    """
    emp1 = EmployeeDTO(
        id=1, full_name="Danışman A", role_id=1, role_name="Satış Danışmanı",
        turnover_source="kendi_islemleri", department_id=1, commission_tiers=sales_advisor_role_tiers
    )
    emp2 = EmployeeDTO(
        id=2, full_name="Danışman B", role_id=1, role_name="Satış Danışmanı",
        turnover_source="kendi_islemleri", department_id=1, commission_tiers=sales_advisor_role_tiers
    )
    emp_gm = EmployeeDTO(
        id=3, full_name="Genel Müdür", role_id=5, role_name="Genel Müdür",
        turnover_source="tum_bayi", department_id=None, commission_tiers=general_manager_role_tiers
    )

    txs = [
        BonusTransactionDTO(id=1, employee_id=1, department_id=1, amount_excl_vat=Decimal("100000.00")),
        BonusTransactionDTO(id=2, employee_id=2, department_id=1, amount_excl_vat=Decimal("200000.00")),
    ]

    report = calculate_period_bonuses(
        period="2024-01",
        employees=[emp1, emp2, emp_gm],
        all_period_transactions=txs
    )

    assert report.period == "2024-01"
    assert report.total_employees == 3
    assert report.total_transactions == 2
    assert report.total_turnover_excl_vat == Decimal("300000.00")
    
    # Check individual bonuses:
    # emp1: 100k * 0.05 = 5,000
    # emp2: 200k * 0.07 = 14,000
    # emp_gm: 300k * 0.02 = 6,000
    # grand_total = 5,000 + 14,000 + 6,000 = 25,000
    assert report.grand_total_bonus == Decimal("25000.00")
    assert sum(item.total_bonus for item in report.items) == report.grand_total_bonus
