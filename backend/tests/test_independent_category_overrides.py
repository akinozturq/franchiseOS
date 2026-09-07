from decimal import Decimal
import pytest

from backend.app.services.commission_service import (
    TierDTO,
    TransactionDTO,
    CollectorParty,
    calculate_reconciliation
)
from backend.app.services.bonus_service import (
    RoleTierDTO,
    BonusTransactionDTO,
    EmployeeDTO,
    calculate_employee_bonus,
    calculate_period_bonuses
)

@pytest.fixture
def bayi_tiers():
    return [
        TierDTO(min_amount=Decimal("0.00"), max_amount=Decimal("750000.00"), rate=Decimal("0.30")),
        TierDTO(min_amount=Decimal("750000.01"), max_amount=None, rate=Decimal("0.35")),
    ]

@pytest.fixture
def role_tiers():
    return [
        RoleTierDTO(min_amount=Decimal("0.00"), max_amount=Decimal("150000.00"), rate=Decimal("0.05")),
        RoleTierDTO(min_amount=Decimal("150000.01"), max_amount=None, rate=Decimal("0.08")),
    ]

def test_independent_category_overrides_matrix(bayi_tiers, role_tiers):
    """
    Test all 4 combinations of category overrides to prove independence:
    1. Cat A: general_override_rate = 0.15, bonus_override_rate = None
       -> In reconciliation: 15% fixed override
       -> In bonus: standard tiered table (not fixed!)
    2. Cat B: general_override_rate = None, bonus_override_rate = 0.07
       -> In reconciliation: standard tiered table (not fixed!)
       -> In bonus: 7% fixed override
    3. Cat C: general_override_rate = None, bonus_override_rate = None
       -> In reconciliation: standard tiered table
       -> In bonus: standard tiered table
    4. Cat D: general_override_rate = 0.12, bonus_override_rate = 0.06
       -> In reconciliation: 12% fixed override
       -> In bonus: 6% fixed override
    """
    emp = EmployeeDTO(
        id=1,
        full_name="Ahmet Danışman",
        role_id=1,
        role_name="Satış Danışmanı",
        turnover_source="kendi_islemleri",
        department_id=1,
        commission_tiers=role_tiers
    )

    # 4 transactions of 100,000 TL each
    amount = Decimal("100000.00")

    # --- Case 1: Mutabakatta istisnalı (%15), Primde istisnasız (None) ---
    tx1_rec = TransactionDTO(department_id=1, amount_excl_vat=amount, general_override_rate=Decimal("0.15"))
    tx1_bon = BonusTransactionDTO(id=1, employee_id=1, department_id=1, amount_excl_vat=amount, bonus_override_rate=None)

    # In reconciliation: should be in override bucket with 15k bayi share
    rec1 = calculate_reconciliation([tx1_rec], bayi_tiers)
    assert rec1.override_turnover_excl_vat == Decimal("100000.00")
    assert rec1.standard_turnover_excl_vat == Decimal("0.00")
    assert rec1.override_bayi_share_excl_vat == Decimal("15000.00")

    # In bonus: should be in standard bucket (100k < 150k -> 5% = 5,000 TL)
    bon1 = calculate_employee_bonus(emp, [tx1_bon])
    assert bon1.override_turnover_excl_vat == Decimal("0.00")
    assert bon1.standard_turnover_excl_vat == Decimal("100000.00")
    assert bon1.standard_tier_rate == Decimal("0.05")
    assert bon1.standard_bonus == Decimal("5000.00")
    assert bon1.override_bonus == Decimal("0.00")

    # --- Case 2: Mutabakatta istisnasız (None), Primde istisnalı (%7) ---
    tx2_rec = TransactionDTO(department_id=1, amount_excl_vat=amount, general_override_rate=None)
    tx2_bon = BonusTransactionDTO(id=2, employee_id=1, department_id=1, amount_excl_vat=amount, bonus_override_rate=Decimal("0.07"))

    # In reconciliation: standard turnover 100k -> 30% = 30,000 TL
    rec2 = calculate_reconciliation([tx2_rec], bayi_tiers)
    assert rec2.override_turnover_excl_vat == Decimal("0.00")
    assert rec2.standard_turnover_excl_vat == Decimal("100000.00")
    assert rec2.standard_bayi_share_excl_vat == Decimal("30000.00")

    # In bonus: override turnover 100k -> 7% = 7,000 TL (ignores role tiers)
    bon2 = calculate_employee_bonus(emp, [tx2_bon])
    assert bon2.standard_turnover_excl_vat == Decimal("0.00")
    assert bon2.override_turnover_excl_vat == Decimal("100000.00")
    assert bon2.override_bonus == Decimal("7000.00")
    assert bon2.standard_bonus == Decimal("0.00")

    # --- Combined Test: Both transactions together ---
    rec_combo = calculate_reconciliation([tx1_rec, tx2_rec], bayi_tiers)
    assert rec_combo.total_turnover_excl_vat == Decimal("200000.00")
    assert rec_combo.override_turnover_excl_vat == Decimal("100000.00")  # Only tx1
    assert rec_combo.standard_turnover_excl_vat == Decimal("100000.00")  # Only tx2
    assert rec_combo.bayi_share_excl_vat == Decimal("15000.00") + Decimal("30000.00")

    bon_combo = calculate_employee_bonus(emp, [tx1_bon, tx2_bon])
    assert bon_combo.total_turnover_excl_vat == Decimal("200000.00")
    assert bon_combo.standard_turnover_excl_vat == Decimal("100000.00")  # Only tx1 is standard for bonus
    assert bon_combo.override_turnover_excl_vat == Decimal("100000.00")  # Only tx2 is override for bonus
    assert bon_combo.standard_bonus == Decimal("5000.00")
    assert bon_combo.override_bonus == Decimal("7000.00")
    assert bon_combo.total_bonus == Decimal("12000.00")


def test_unassigned_transactions_reconciliation_total_integrity(bayi_tiers):
    """
    CRITICAL CHECK:
    Verify that transactions with employee_id = None (or unassigned staff):
    1. Are 100% included in total turnover in reconciliation.
    2. Do NOT cause any kuruş to be dropped from franchisor-bayi revenue share or invoices.
    3. Exactly match whether employee_id is populated or None.
    """
    # 3 transactions: one assigned to emp 1, one assigned to emp 2, one unassigned (employee_id is None)
    tx_assigned_1 = TransactionDTO(id=1, department_id=1, department_name="PPF", amount_excl_vat=Decimal("300000.00"))
    tx_assigned_2 = TransactionDTO(id=2, department_id=2, department_name="Mekanik", amount_excl_vat=Decimal("200000.00"))
    tx_unassigned = TransactionDTO(id=3, department_id=1, department_name="PPF", amount_excl_vat=Decimal("150000.00"))

    all_txs = [tx_assigned_1, tx_assigned_2, tx_unassigned]
    rec = calculate_reconciliation(all_txs, bayi_tiers, collector_party=CollectorParty.BAYI)

    # Total turnover must be 650,000 TL (including the unassigned 150k TL)
    assert rec.total_transactions == 3
    assert rec.total_turnover_excl_vat == Decimal("650000.00")

    # 650,000 TL falls into 0-750,000 tier (%30)
    assert rec.bayi_share_excl_vat == Decimal("195000.00")
    assert rec.franchisor_share_excl_vat == Decimal("455000.00")
    assert rec.bayi_share_excl_vat + rec.franchisor_share_excl_vat == rec.total_turnover_excl_vat

    # Invoice covers the full amount
    assert rec.invoice_summary.amount_excl_vat == Decimal("455000.00")

    # Department totals must equal total turnover
    dept_sum = sum(d.total_turnover_excl_vat for d in rec.department_breakdown)
    assert dept_sum == Decimal("650000.00")
