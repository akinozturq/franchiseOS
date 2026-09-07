from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import extract

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_roles, get_active_branch_id
from backend.app.models.user import User
from backend.app.models.branch import Branch
from backend.app.models.department import Department
from backend.app.models.transaction import Transaction
from backend.app.models.commission_tier import CommissionTier
from backend.app.models.period_setting import PeriodSetting
from backend.app.models.period_closure import PeriodClosure
from backend.app.schemas.reconciliation import (
    ReconciliationResponse,
    PeriodSettingUpdate,
    PeriodSettingOut
)
from backend.app.services.commission_service import (
    CollectorParty,
    TierDTO,
    TransactionDTO,
    calculate_reconciliation
)
from backend.app.services.export_service import generate_reconciliation_excel
from backend.app.services.pdf_service import generate_reconciliation_pdf

router = APIRouter(prefix="/reconciliation", tags=["Mutabakat ve Komisyon"])

def get_or_create_period_setting(
    branch_id: int,
    year: int,
    month: int,
    collector_party: Optional[CollectorParty],
    vat_rate: Optional[Decimal],
    db: Session
) -> PeriodSetting:
    """
    Dönemin tahsilatçı ve KDV ayarlarını veritabanında kalıcı (audit-proof) olarak saklar.
    Sonraki açılışlarda veya başka bir kullanıcı baktığında aynı ayar gelir.
    """
    setting = db.query(PeriodSetting).filter(
        PeriodSetting.branch_id == branch_id,
        PeriodSetting.year == year,
        PeriodSetting.month == month
    ).first()

    if not setting:
        party_val = collector_party.value if collector_party else "BAYI"
        v_rate = vat_rate if vat_rate is not None else Decimal("0.20")
        setting = PeriodSetting(
            branch_id=branch_id,
            year=year,
            month=month,
            collector_party=party_val,
            vat_rate=v_rate,
            is_locked=False
        )
        db.add(setting)
        db.commit()
        db.refresh(setting)
    else:
        changed = False
        if collector_party is not None and setting.collector_party != collector_party.value:
            setting.collector_party = collector_party.value
            changed = True
        if vat_rate is not None and setting.vat_rate != vat_rate:
            setting.vat_rate = vat_rate
            changed = True
        if changed:
            db.commit()
            db.refresh(setting)

    return setting

from datetime import date
import calendar
from sqlalchemy import or_
from backend.app.models.period_closure import PeriodClosure
from backend.app.models.transaction_category import TransactionCategory

def build_reconciliation_data(
    branch_id: int,
    year: int,
    month: int,
    collector_party: Optional[CollectorParty],
    vat_rate: Optional[Decimal],
    db: Session
) -> ReconciliationResponse:
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Bayi bulunamadı.")

    # 1. Check if period is officially closed -> return frozen snapshot!
    closure = db.query(PeriodClosure).filter(
        PeriodClosure.branch_id == branch.id,
        PeriodClosure.year == year,
        PeriodClosure.month == month,
        PeriodClosure.status == "CLOSED",
        PeriodClosure.reopened_at == None
    ).first()

    if closure and closure.reconciliation_snapshot:
        snapshot = dict(closure.reconciliation_snapshot)
        snapshot["is_closed"] = True
        snapshot["closed_at"] = closure.closed_at.isoformat() if closure.closed_at else None
        snapshot["closed_by_name"] = (
            closure.closed_by.full_name or closure.closed_by.username
            if closure.closed_by else "Franchisor Admin"
        )
        return ReconciliationResponse(**snapshot)
    
    # 2. Fetch or create persistent period setting
    setting = get_or_create_period_setting(
        branch_id=branch.id,
        year=year,
        month=month,
        collector_party=collector_party,
        vat_rate=vat_rate,
        db=db
    )
    
    effective_collector_party = CollectorParty(setting.collector_party)
    effective_vat_rate = setting.vat_rate
    
    # 3. Fetch transactions for period
    transactions = db.query(Transaction).filter(
        Transaction.branch_id == branch.id,
        extract("year", Transaction.date) == year,
        extract("month", Transaction.date) == month
    ).all()
    
    # 4. Fetch departments map
    dept_map = {d.id: d.name for d in db.query(Department).filter(Department.branch_id == branch.id).all()}
    
    # 5. Convert transactions to DTOs (using rule valid at tx.date)
    tx_dtos = []
    for tx in transactions:
        override_rate = tx.category.general_override_rate if tx.category else None
        cat_name = tx.category.name if tx.category else None
        if tx.category:
            cat_rule = db.query(TransactionCategory).filter(
                TransactionCategory.branch_id == branch.id,
                TransactionCategory.name == tx.category.name,
                TransactionCategory.effective_from <= tx.date,
                or_(
                    TransactionCategory.effective_to == None,
                    TransactionCategory.effective_to > tx.date
                )
            ).first()
            if cat_rule:
                override_rate = cat_rule.general_override_rate

        tx_dtos.append(
            TransactionDTO(
                id=tx.id,
                department_id=tx.department_id,
                department_name=dept_map.get(tx.department_id, "Genel"),
                category_id=tx.category_id,
                category_name=cat_name,
                general_override_rate=override_rate,
                amount_excl_vat=tx.amount_excl_vat,
                vat_rate=tx.vat_rate,
                amount_incl_vat=tx.amount_incl_vat
            )
        )
    
    # 6. Fetch commission tiers effective for period
    last_day = calendar.monthrange(year, month)[1]
    period_date = date(year, month, last_day)

    tiers_db = db.query(CommissionTier).filter(
        CommissionTier.branch_id == branch.id,
        CommissionTier.effective_from <= period_date,
        or_(
            CommissionTier.effective_to == None,
            CommissionTier.effective_to > period_date
        )
    ).order_by(CommissionTier.min_amount.asc()).all()

    if not tiers_db:
        tiers_db = db.query(CommissionTier).filter(
            CommissionTier.branch_id == branch.id
        ).order_by(CommissionTier.min_amount.asc()).all()
    
    tier_dtos = [
        TierDTO(
            id=t.id,
            min_amount=t.min_amount,
            max_amount=t.max_amount,
            rate=t.rate
        )
        for t in tiers_db
    ]
    
    # 7. Calculate
    calc_res = calculate_reconciliation(
        transactions=tx_dtos,
        tiers=tier_dtos,
        default_vat_rate=effective_vat_rate,
        collector_party=effective_collector_party
    )
    
    return ReconciliationResponse(
        year=year,
        month=month,
        branch_name=branch.name,
        total_transactions=calc_res.total_transactions,
        total_turnover_excl_vat=calc_res.total_turnover_excl_vat,
        override_transactions_count=calc_res.override_transactions_count,
        override_turnover_excl_vat=calc_res.override_turnover_excl_vat,
        override_bayi_share_excl_vat=calc_res.override_bayi_share_excl_vat,
        standard_turnover_excl_vat=calc_res.standard_turnover_excl_vat,
        standard_bayi_share_excl_vat=calc_res.standard_bayi_share_excl_vat,
        applied_tier=calc_res.applied_tier,
        applied_rate_percentage=calc_res.applied_rate_percentage,
        rate_explanation=calc_res.rate_explanation,
        bayi_share_rate=calc_res.bayi_share_rate,
        bayi_share_excl_vat=calc_res.bayi_share_excl_vat,
        franchisor_share_rate=calc_res.franchisor_share_rate,
        franchisor_share_excl_vat=calc_res.franchisor_share_excl_vat,
        invoice_summary=calc_res.invoice_summary,
        department_breakdown=calc_res.department_breakdown,
        is_setting_persisted=True,
        is_locked=setting.is_locked,
        is_closed=False,
        closed_at=None,
        closed_by_name=None
    )

@router.get("", response_model=ReconciliationResponse)
def get_reconciliation_report(
    year: int = Query(..., ge=2000, le=2100, description="Dönem Yılı (örn. 2026)"),
    month: int = Query(..., ge=1, le=12, description="Dönem Ayı (1-12)"),
    collector_party: Optional[CollectorParty] = Query(None, description="Tahsilatı yapan taraf (BAYI veya FRANCHISOR)"),
    vat_rate: Optional[Decimal] = Query(None, ge=0, le=1, description="KDV Oranı"),
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Seçilen ay ve yıl için dönem mutabakat raporunu ve fatura kesim özetini üretir.
    Tahsilat yapan taraf veritabanında kalıcı olarak saklanır.
    """
    return build_reconciliation_data(
        branch_id=branch_id,
        year=year,
        month=month,
        collector_party=collector_party,
        vat_rate=vat_rate,
        db=db
    )

@router.put("/setting", response_model=PeriodSettingOut)
def update_period_setting(
    setting_in: PeriodSettingUpdate,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN", "BAYI_ADMIN")),
    db: Session = Depends(get_db)
):
    """
    Bir dönemin tahsilat yapan taraf ve KDV ayarını kalıcı olarak kaydeder veya kilitler.
    """
    # 1. Kapatılmış dönem kontrolü
    closed_period = db.query(PeriodClosure).filter(
        PeriodClosure.branch_id == branch_id,
        PeriodClosure.year == setting_in.year,
        PeriodClosure.month == setting_in.month,
        PeriodClosure.status == "CLOSED"
    ).first()
    if closed_period:
        raise HTTPException(
            status_code=400,
            detail=f"{setting_in.year}-{setting_in.month:02d} dönemi kapatılmış ve kilitlenmiştir. Kapatılmış dönemin mutabakat ayarları değiştirilemez."
        )

    setting = db.query(PeriodSetting).filter(
        PeriodSetting.branch_id == branch_id,
        PeriodSetting.year == setting_in.year,
        PeriodSetting.month == setting_in.month
    ).first()

    # 2. Mevcut kilit kontrolü
    if setting and setting.is_locked:
        # Kilitliyken ve kilidi kaldırma talebi yokken ayar değiştirilemez
        if setting_in.is_locked is not False:
            if (
                setting.collector_party != setting_in.collector_party.value or
                (setting_in.vat_rate is not None and setting.vat_rate != setting_in.vat_rate)
            ):
                raise HTTPException(
                    status_code=400,
                    detail=f"{setting_in.year}-{setting_in.month:02d} dönemi mutabakat ayarları kilitlidir. Değişiklik yapmak için önce kilidi kaldırınız."
                )

    if not setting:
        setting = PeriodSetting(
            branch_id=branch_id,
            year=setting_in.year,
            month=setting_in.month,
            collector_party=setting_in.collector_party.value,
            vat_rate=setting_in.vat_rate or Decimal("0.20"),
            is_locked=setting_in.is_locked or False
        )
        db.add(setting)
    else:
        setting.collector_party = setting_in.collector_party.value
        if setting_in.vat_rate is not None:
            setting.vat_rate = setting_in.vat_rate
        if setting_in.is_locked is not None:
            setting.is_locked = setting_in.is_locked

    db.commit()
    db.refresh(setting)
    return setting

@router.get("/export")
def export_reconciliation_excel(
    year: int = Query(..., ge=2000, le=2100, description="Dönem Yılı"),
    month: int = Query(..., ge=1, le=12, description="Dönem Ayı (1-12)"),
    collector_party: Optional[CollectorParty] = Query(None, description="Tahsilatı yapan taraf"),
    vat_rate: Optional[Decimal] = Query(None, ge=0, le=1, description="KDV Oranı"),
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Dönem mutabakat raporunu ekranla birebir eşleşen formatlanmış Excel (.xlsx) dosyası olarak indirir.
    """
    report = build_reconciliation_data(
        branch_id=branch_id,
        year=year,
        month=month,
        collector_party=collector_party,
        vat_rate=vat_rate,
        db=db
    )
    
    excel_stream = generate_reconciliation_excel(report)
    filename = f"Mutabakat_Raporu_{year}_{month:02d}_{report.invoice_summary.collector_party.value}.xlsx"
    
    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/export-pdf")
def export_reconciliation_pdf_endpoint(
    year: int = Query(..., ge=2000, le=2100, description="Dönem Yılı"),
    month: int = Query(..., ge=1, le=12, description="Dönem Ayı (1-12)"),
    collector_party: Optional[CollectorParty] = Query(None, description="Tahsilatı yapan taraf"),
    vat_rate: Optional[Decimal] = Query(None, ge=0, le=1, description="KDV Oranı"),
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Dönem mutabakat raporunu resmi PDF belgesi olarak indirir.
    Kapalı dönem için dondurulmuş snapshot verisinden, açık dönem için canlı hesaplamadan üretilir.
    """
    report = build_reconciliation_data(
        branch_id=branch_id,
        year=year,
        month=month,
        collector_party=collector_party,
        vat_rate=vat_rate,
        db=db
    )
    
    data = report.model_dump(mode="json")
    data["period"] = f"{year}-{month:02d}"
    
    pdf_stream = generate_reconciliation_pdf(data)
    filename = f"Mutabakat_Raporu_{year}_{month:02d}.pdf"
    
    return StreamingResponse(
        pdf_stream,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
