import pytest
from decimal import Decimal
from backend.app.services.commission_service import (
    CollectorParty,
    TierDTO,
    TransactionDTO,
    calculate_reconciliation,
    find_applicable_tier,
    quantize_money
)

@pytest.fixture
def sample_tiers():
    """
    Standard tiers from Prompt:
    0 - 750,000.00 TL -> %30
    750,000.01+ TL    -> %35
    """
    return [
        TierDTO(id=1, min_amount=Decimal("0.00"), max_amount=Decimal("750000.00"), rate=Decimal("0.30")),
        TierDTO(id=2, min_amount=Decimal("750000.01"), max_amount=None, rate=Decimal("0.35")),
    ]

def test_prompt_scenario_800k(sample_tiers):
    """
    Prompt Test: 800,000 TL ciro girildiğinde, 0-750.000 için %30 ve 750.001+ için %35 kuralı tanımlıysa:
    Tüm tutara %35 uygulanır (800.000 * 0.35 = 280.000 Bayi, 520.000 Franchisor).
    """
    transactions = [
        TransactionDTO(department_id=1, department_name="Satış", amount_excl_vat=Decimal("500000.00")),
        TransactionDTO(department_id=2, department_name="Servis", amount_excl_vat=Decimal("300000.00")),
    ]
    
    result = calculate_reconciliation(transactions, sample_tiers, default_vat_rate=Decimal("0.20"))
    
    assert result.total_turnover_excl_vat == Decimal("800000.00")
    assert result.applied_tier is not None
    assert result.applied_tier.id == 2
    assert result.bayi_share_rate == Decimal("0.35")
    assert result.franchisor_share_rate == Decimal("0.65")
    
    # 800.000 * 0.35 = 280.000 TL
    assert result.bayi_share_excl_vat == Decimal("280000.00")
    # 800.000 * 0.65 = 520.000 TL
    assert result.franchisor_share_excl_vat == Decimal("520000.00")
    assert result.bayi_share_excl_vat + result.franchisor_share_excl_vat == Decimal("800000.00")
    
    # Invoice summary: Franchisor invoices Bayi for Franchisor share + 20% VAT
    inv = result.invoice_summary
    assert inv.amount_excl_vat == Decimal("520000.00")
    assert inv.vat_rate == Decimal("0.20")
    assert inv.vat_amount == Decimal("104000.00")
    assert inv.total_amount_incl_vat == Decimal("624000.00")

def test_boundary_exact_750k(sample_tiers):
    """
    Boundary Test: Exactly 750,000.00 TL should fall into Tier 1 (30%).
    """
    transactions = [
        TransactionDTO(department_id=1, department_name="Satış", amount_excl_vat=Decimal("750000.00"))
    ]
    result = calculate_reconciliation(transactions, sample_tiers)
    
    assert result.total_turnover_excl_vat == Decimal("750000.00")
    assert result.applied_tier.id == 1
    assert result.bayi_share_rate == Decimal("0.30")
    assert result.bayi_share_excl_vat == Decimal("225000.00")
    assert result.franchisor_share_excl_vat == Decimal("525000.00")

def test_boundary_just_below_750k(sample_tiers):
    """
    Boundary Test: 749,999.99 TL should fall into Tier 1 (30%).
    """
    transactions = [
        TransactionDTO(department_id=1, department_name="Satış", amount_excl_vat=Decimal("749999.99"))
    ]
    result = calculate_reconciliation(transactions, sample_tiers)
    
    assert result.applied_tier.id == 1
    assert result.bayi_share_rate == Decimal("0.30")
    # 749999.99 * 0.30 = 224999.997 -> 225000.00
    assert result.bayi_share_excl_vat == Decimal("225000.00")
    assert result.franchisor_share_excl_vat == Decimal("524999.99")
    assert result.bayi_share_excl_vat + result.franchisor_share_excl_vat == Decimal("749999.99")

def test_boundary_just_above_750k(sample_tiers):
    """
    Boundary Test: 750,000.01 TL should fall into Tier 2 (35%).
    """
    transactions = [
        TransactionDTO(department_id=1, department_name="Satış", amount_excl_vat=Decimal("750000.01"))
    ]
    result = calculate_reconciliation(transactions, sample_tiers)
    
    assert result.applied_tier.id == 2
    assert result.bayi_share_rate == Decimal("0.35")
    # 750000.01 * 0.35 = 262500.0035 -> 262500.00
    assert result.bayi_share_excl_vat == Decimal("262500.00")
    assert result.franchisor_share_excl_vat == Decimal("487500.01")
    assert result.bayi_share_excl_vat + result.franchisor_share_excl_vat == Decimal("750000.01")

def test_department_breakdown_sum_matches_total(sample_tiers):
    """
    Requirement 7: Departman bazlı kırılımın toplamı genel ciro ile birebir eşleşmeli (yuvarlama hatası yok).
    """
    transactions = [
        TransactionDTO(department_id=1, department_name="Satış", amount_excl_vat=Decimal("123456.78")),
        TransactionDTO(department_id=2, department_name="Servis", amount_excl_vat=Decimal("234567.89")),
        TransactionDTO(department_id=3, department_name="Yedek Parça", amount_excl_vat=Decimal("345678.91")),
        TransactionDTO(department_id=1, department_name="Satış", amount_excl_vat=Decimal("98765.43")),
    ]
    result = calculate_reconciliation(transactions, sample_tiers)
    
    total_dept_turnover = sum((d.total_turnover_excl_vat for d in result.department_breakdown), Decimal("0.00"))
    assert total_dept_turnover == result.total_turnover_excl_vat
    assert total_dept_turnover == Decimal("802469.01")
    assert len(result.department_breakdown) == 3

def test_empty_transactions(sample_tiers):
    """
    Empty transaction list should result in 0.00 turnover without crashing.
    """
    result = calculate_reconciliation([], sample_tiers)
    assert result.total_transactions == 0
    assert result.total_turnover_excl_vat == Decimal("0.00")
    assert result.bayi_share_excl_vat == Decimal("0.00")
    assert result.franchisor_share_excl_vat == Decimal("0.00")
    assert len(result.department_breakdown) == 0

def test_invoicing_direction_when_bayi_collects(sample_tiers):
    """
    Kural: "tahsilat eden değil, tahsilat etmeyen taraf kendi payını faturalar"
    Tahsilat: BAYI
    Tahsilat etmeyen: FRANCHISOR
    Fatura: Franchisor (Merkez) -> Bayi'ye Franchisor Payı + KDV kadar fatura keser.
    """
    transactions = [
        TransactionDTO(department_id=1, department_name="Satış", amount_excl_vat=Decimal("1000000.00"))
    ]
    # Ciro 1.000.000 TL -> %35 Bayi (350.000 TL), %65 Franchisor (650.000 TL)
    result = calculate_reconciliation(
        transactions,
        sample_tiers,
        default_vat_rate=Decimal("0.20"),
        collector_party=CollectorParty.BAYI
    )
    inv = result.invoice_summary
    assert inv.collector_party == CollectorParty.BAYI
    assert inv.issuer == "Franchisor (Merkez)"
    assert inv.recipient == "Bayi"
    assert inv.amount_excl_vat == Decimal("650000.00")  # Franchisor payı
    assert inv.vat_rate == Decimal("0.20")
    assert inv.vat_amount == Decimal("130000.00")
    assert inv.total_amount_incl_vat == Decimal("780000.00")

def test_invoicing_direction_when_franchisor_collects(sample_tiers):
    """
    Kural: "tahsilat eden değil, tahsilat etmeyen taraf kendi payını faturalar"
    Tahsilat: FRANCHISOR
    Tahsilat etmeyen: BAYI
    Fatura: Bayi -> Franchisor (Merkez)'e Bayi Payı + KDV kadar hakediş faturası keser.
    """
    transactions = [
        TransactionDTO(department_id=1, department_name="Satış", amount_excl_vat=Decimal("1000000.00"))
    ]
    # Ciro 1.000.000 TL -> %35 Bayi (350.000 TL), %65 Franchisor (650.000 TL)
    result = calculate_reconciliation(
        transactions,
        sample_tiers,
        default_vat_rate=Decimal("0.20"),
        collector_party=CollectorParty.FRANCHISOR
    )
    inv = result.invoice_summary
    assert inv.collector_party == CollectorParty.FRANCHISOR
    assert inv.issuer == "Bayi"
    assert inv.recipient == "Franchisor (Merkez)"
    assert inv.amount_excl_vat == Decimal("350000.00")  # Bayi payı
    assert inv.vat_rate == Decimal("0.20")
    assert inv.vat_amount == Decimal("70000.00")
    assert inv.total_amount_incl_vat == Decimal("420000.00")

