from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel

COMMISSION_ENGINE_VERSION = "1.0.0"

class CollectorParty(str, Enum):
    BAYI = "BAYI"
    FRANCHISOR = "FRANCHISOR"

class TierDTO(BaseModel):
    id: Optional[int] = None
    min_amount: Decimal
    max_amount: Optional[Decimal] = None  # None means infinity
    rate: Decimal  # e.g. Decimal("0.30") for 30% Bayi share

class TransactionDTO(BaseModel):
    id: Optional[int] = None
    department_id: int
    department_name: Optional[str] = "Genel"
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    general_override_rate: Optional[Decimal] = None  # Sabit istisna oranı (örn 0.15)
    amount_excl_vat: Decimal
    vat_rate: Decimal = Decimal("0.20")
    amount_incl_vat: Optional[Decimal] = None

class DepartmentSummary(BaseModel):
    department_id: int
    department_name: str
    transaction_count: int
    total_turnover_excl_vat: Decimal
    percentage_of_total: Decimal

class InvoiceSummary(BaseModel):
    collector_party: CollectorParty
    issuer: str  # Tahsilat etmeyen taraf faturayı keser
    recipient: str  # Tahsilatı yapan taraf faturayı alır
    description: str
    amount_excl_vat: Decimal
    vat_rate: Decimal
    vat_amount: Decimal
    total_amount_incl_vat: Decimal

class ReconciliationResult(BaseModel):
    total_transactions: int
    total_turnover_excl_vat: Decimal
    
    # Category Overrides breakdown
    override_transactions_count: int = 0
    override_turnover_excl_vat: Decimal = Decimal("0.00")
    override_bayi_share_excl_vat: Decimal = Decimal("0.00")
    standard_turnover_excl_vat: Decimal = Decimal("0.00")
    standard_bayi_share_excl_vat: Decimal = Decimal("0.00")
    
    # Applied Tier
    applied_tier: Optional[TierDTO] = None
    applied_rate_percentage: Decimal
    rate_explanation: str
    
    # Revenue Shares
    bayi_share_rate: Decimal
    bayi_share_excl_vat: Decimal
    franchisor_share_rate: Decimal
    franchisor_share_excl_vat: Decimal
    
    # Invoice Details
    invoice_summary: InvoiceSummary
    
    # Department breakdown
    department_breakdown: List[DepartmentSummary]



def quantize_money(amount: Decimal) -> Decimal:
    """Round to 2 decimal places using standard half-up rounding."""
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def find_applicable_tier(total_turnover: Decimal, tiers: List[TierDTO]) -> Optional[TierDTO]:
    """
    Finds the applicable commission tier based on the total turnover.
    Tiers are evaluated such that total_turnover falls within [min_amount, max_amount].
    If max_amount is None, the tier acts as min_amount to infinity.
    
    Convention:
    min_amount <= total_turnover <= max_amount (when max_amount is defined)
    min_amount <= total_turnover (when max_amount is None)
    
    If tiers are contiguous (e.g. 0-750.000, 750.000,01-sonsuz):
    - 750.000,00 -> falls into 0-750.000
    - 750.000,01 -> falls into 750.000,01+
    """
    if not tiers:
        return None

    # Sort tiers by min_amount ascending
    sorted_tiers = sorted(tiers, key=lambda t: t.min_amount)

    for tier in sorted_tiers:
        if tier.max_amount is not None:
            if tier.min_amount <= total_turnover <= tier.max_amount:
                return tier
        else:
            if tier.min_amount <= total_turnover:
                return tier

    # If turnover exceeds the highest tier which had a max_amount specified,
    # or falls outside, return the highest tier or None
    return sorted_tiers[-1] if total_turnover >= sorted_tiers[-1].min_amount else None


def calculate_reconciliation(
    transactions: List[TransactionDTO],
    tiers: List[TierDTO],
    default_vat_rate: Decimal = Decimal("0.20"),
    collector_party: CollectorParty = CollectorParty.BAYI
) -> ReconciliationResult:
    """
    Calculates monthly period reconciliation according to Faz 1 & Faz 2 specifications:
    - Kategori İstisnası Mantığı:
      1. Kategori bazlı genel istisna oranı tanımlı olan işlemler sabit oranıyla hesaplanır.
      2. Kalan standart işlemlerin toplam cirosu tek bir dilime düşer ve tüm standart tutara o dilim oranı uygulanır.
      3. İkisinin toplamı toplam hakedişi verir.
    - Franchisor Share = Total Turnover - Bayi Share (0 kuruş fark garantisi).
    - Department breakdown totals must match total turnover exactly.
    - Fatura Yönü: "tahsilat eden değil, tahsilat etmeyen taraf kendi payını faturalar".
    """
    total_transactions = len(transactions)
    
    # Separate into category override transactions and standard transactions
    override_txs = [t for t in transactions if t.general_override_rate is not None]
    standard_txs = [t for t in transactions if t.general_override_rate is None]
    
    override_turnover = sum((quantize_money(t.amount_excl_vat) for t in override_txs), Decimal("0.00"))
    standard_turnover = sum((quantize_money(t.amount_excl_vat) for t in standard_txs), Decimal("0.00"))
    total_turnover = override_turnover + standard_turnover
    
    # 1. Override Bayi Share
    override_bayi_share = sum(
        (quantize_money(t.amount_excl_vat * t.general_override_rate) for t in override_txs),
        Decimal("0.00")
    )
    
    # 2. Standard Bayi Share (using tiered commission on standard turnover)
    applicable_tier = find_applicable_tier(standard_turnover, tiers)
    if applicable_tier:
        standard_rate = applicable_tier.rate
        standard_bayi_share = quantize_money(standard_turnover * standard_rate)
        tier_text = (
            f"Kategori istisnası olmayan standart ciro ({standard_turnover:,.2f} TL) "
            f"[{applicable_tier.min_amount:,.2f} TL - "
            f"{f'{applicable_tier.max_amount:,.2f} TL' if applicable_tier.max_amount is not None else 'Sonsuz'}] "
            f"dilimine düşmektedir (%{standard_rate * 100:.2f})."
        )
    else:
        standard_rate = Decimal("0.00")
        standard_bayi_share = Decimal("0.00")
        tier_text = f"Standart ciro ({standard_turnover:,.2f} TL) için geçerli dilim bulunamadı."

    if override_txs:
        rate_explanation = (
            f"{tier_text} Ayrıca {len(override_txs)} adet işlemde ({override_turnover:,.2f} TL) "
            f"kategori bazlı özel sabit oran uygulanmıştır."
        )
    else:
        rate_explanation = tier_text

    # 3. Combined Revenue Shares
    bayi_share = override_bayi_share + standard_bayi_share
    franchisor_share = total_turnover - bayi_share
    
    effective_bayi_rate = (bayi_share / total_turnover).quantize(Decimal("0.0001")) if total_turnover > Decimal("0.00") else Decimal("0.0000")
    effective_franchisor_rate = Decimal("1.0000") - effective_bayi_rate

    
    # 4. Department Breakdown
    dept_map: Dict[int, Dict[str, Any]] = {}
    for t in transactions:
        dept_id = t.department_id
        dept_name = t.department_name or f"Departman {dept_id}"
        if dept_id not in dept_map:
            dept_map[dept_id] = {
                "name": dept_name,
                "count": 0,
                "turnover": Decimal("0.00")
            }
        dept_map[dept_id]["count"] += 1
        dept_map[dept_id]["turnover"] += quantize_money(t.amount_excl_vat)
        
    department_breakdown: List[DepartmentSummary] = []
    for dept_id, data in dept_map.items():
        dept_turnover = data["turnover"]
        pct = (
            quantize_money((dept_turnover / total_turnover) * Decimal("100.00"))
            if total_turnover > Decimal("0.00")
            else Decimal("0.00")
        )
        department_breakdown.append(DepartmentSummary(
            department_id=dept_id,
            department_name=data["name"],
            transaction_count=data["count"],
            total_turnover_excl_vat=dept_turnover,
            percentage_of_total=pct
        ))
        
    # Sort departments by turnover descending
    department_breakdown.sort(key=lambda d: d.total_turnover_excl_vat, reverse=True)

    # 5. Invoicing: "tahsilat eden değil, tahsilat etmeyen taraf kendi payını faturalar"
    if collector_party == CollectorParty.BAYI:
        # Tahsilat Bayi'de -> Franchisor (tahsilat etmeyen taraf) kendi payını Bayi'ye fatura eder.
        invoice_issuer = "Franchisor (Merkez)"
        invoice_recipient = "Bayi"
        invoice_desc = "Dönemlik Franchise / İsim Hakkı & Ciro Payı Faturası"
        inv_excl_vat = franchisor_share
    else:
        # Tahsilat Franchisor'da -> Bayi (tahsilat etmeyen taraf) kendi payını Franchisor'a fatura eder.
        invoice_issuer = "Bayi"
        invoice_recipient = "Franchisor (Merkez)"
        invoice_desc = "Dönemlik Bayi Hakediş Faturası"
        inv_excl_vat = bayi_share

    inv_vat = quantize_money(inv_excl_vat * default_vat_rate)
    inv_incl_vat = inv_excl_vat + inv_vat
    
    invoice_summary = InvoiceSummary(
        collector_party=collector_party,
        issuer=invoice_issuer,
        recipient=invoice_recipient,
        description=invoice_desc,
        amount_excl_vat=inv_excl_vat,
        vat_rate=default_vat_rate,
        vat_amount=inv_vat,
        total_amount_incl_vat=inv_incl_vat
    )

    return ReconciliationResult(
        total_transactions=total_transactions,
        total_turnover_excl_vat=total_turnover,
        override_transactions_count=len(override_txs),
        override_turnover_excl_vat=override_turnover,
        override_bayi_share_excl_vat=override_bayi_share,
        standard_turnover_excl_vat=standard_turnover,
        standard_bayi_share_excl_vat=standard_bayi_share,
        applied_tier=applicable_tier,
        applied_rate_percentage=(effective_bayi_rate * Decimal("100")).quantize(Decimal("0.01")),
        rate_explanation=rate_explanation,
        bayi_share_rate=effective_bayi_rate,
        bayi_share_excl_vat=bayi_share,
        franchisor_share_rate=effective_franchisor_rate,
        franchisor_share_excl_vat=franchisor_share,
        invoice_summary=invoice_summary,
        department_breakdown=department_breakdown
    )

