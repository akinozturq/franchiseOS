from decimal import Decimal
import pytest

from backend.app.services.commission_service import (
    TierDTO,
    TransactionDTO,
    CollectorParty,
    calculate_reconciliation,
    quantize_money,
)

@pytest.fixture
def standard_tiers():
    return [
        TierDTO(min_amount=Decimal("0.00"), max_amount=Decimal("750000.00"), rate=Decimal("0.30")),
        TierDTO(min_amount=Decimal("750000.01"), max_amount=None, rate=Decimal("0.35")),
    ]

def test_mixed_category_override_and_standard_reconciliation(standard_tiers):
    """
    Mixed scenario:
    Standard transactions:
      Dept 1: 300,000 TL
      Dept 2: 300,000 TL
      Total standard: 600,000 TL -> falls into 0-750,000 tier (%30)
      Standard Bayi Share = 600,000 * 0.30 = 180,000 TL

    Category override transactions (e.g. Komple TPU PPF %15 fixed):
      Dept 1: 200,000 TL with general_override_rate = 0.15
      Override Bayi Share = 200,000 * 0.15 = 30,000 TL

    Totals:
      Total Turnover = 800,000 TL
      Total Bayi Share = 180,000 + 30,000 = 210,000 TL
      Franchisor Share = 800,000 - 210,000 = 590,000 TL
    """
    transactions = [
        TransactionDTO(department_id=1, department_name="PPF & Kaplama", amount_excl_vat=Decimal("300000.00"), general_override_rate=None),
        TransactionDTO(department_id=2, department_name="Mekanik Servis", amount_excl_vat=Decimal("300000.00"), general_override_rate=None),
        TransactionDTO(department_id=1, department_name="PPF & Kaplama", amount_excl_vat=Decimal("200000.00"), general_override_rate=Decimal("0.15")),
    ]

    result = calculate_reconciliation(
        transactions=transactions,
        tiers=standard_tiers,
        default_vat_rate=Decimal("0.20"),
        collector_party=CollectorParty.BAYI
    )

    assert result.total_transactions == 3
    assert result.total_turnover_excl_vat == Decimal("800000.00")
    assert result.standard_turnover_excl_vat == Decimal("600000.00")
    assert result.standard_bayi_share_excl_vat == Decimal("180000.00")
    assert result.override_transactions_count == 1
    assert result.override_turnover_excl_vat == Decimal("200000.00")
    assert result.override_bayi_share_excl_vat == Decimal("200000.00") * Decimal("0.15")
    assert result.override_bayi_share_excl_vat == Decimal("30000.00")
    
    assert result.bayi_share_excl_vat == Decimal("210000.00")
    assert result.franchisor_share_excl_vat == Decimal("590000.00")
    assert result.bayi_share_excl_vat + result.franchisor_share_excl_vat == result.total_turnover_excl_vat

    # Department breakdown must equal total turnover
    dept_total = sum(d.total_turnover_excl_vat for d in result.department_breakdown)
    assert dept_total == result.total_turnover_excl_vat

    # Invoicing: Collector is BAYI -> Franchisor invoices Bayi for Franchisor share (590k + %20 KDV)
    assert result.invoice_summary.collector_party == CollectorParty.BAYI
    assert result.invoice_summary.issuer == "Franchisor (Merkez)"
    assert result.invoice_summary.recipient == "Bayi"
    assert result.invoice_summary.amount_excl_vat == Decimal("590000.00")
    assert result.invoice_summary.vat_amount == Decimal("118000.00")
    assert result.invoice_summary.total_amount_incl_vat == Decimal("708000.00")


def test_override_only_transactions(standard_tiers):
    """
    Scenario where all transactions have a fixed category override.
    """
    txs = [
        TransactionDTO(department_id=1, department_name="Kaplama", amount_excl_vat=Decimal("100000.00"), general_override_rate=Decimal("0.15")),
        TransactionDTO(department_id=1, department_name="Kaplama", amount_excl_vat=Decimal("50000.00"), general_override_rate=Decimal("0.10")),
    ]

    res = calculate_reconciliation(
        transactions=txs,
        tiers=standard_tiers,
        default_vat_rate=Decimal("0.20"),
        collector_party=CollectorParty.FRANCHISOR
    )

    assert res.total_turnover_excl_vat == Decimal("150000.00")
    assert res.standard_turnover_excl_vat == Decimal("0.00")
    assert res.standard_bayi_share_excl_vat == Decimal("0.00")
    # 100k * 0.15 = 15k, 50k * 0.10 = 5k -> Total = 20k
    assert res.bayi_share_excl_vat == Decimal("20000.00")
    assert res.franchisor_share_excl_vat == Decimal("130000.00")

    # Invoicing: Collector is FRANCHISOR -> Bayi invoices Franchisor for Bayi share (20k + %20 KDV)
    assert res.invoice_summary.issuer == "Bayi"
    assert res.invoice_summary.recipient == "Franchisor (Merkez)"
    assert res.invoice_summary.amount_excl_vat == Decimal("20000.00")
    assert res.invoice_summary.vat_amount == Decimal("4000.00")
    assert res.invoice_summary.total_amount_incl_vat == Decimal("24000.00")
