from fastapi import APIRouter, Depends, HTTPException, Query
from decimal import Decimal
from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import extract, func

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_roles, get_active_branch_id
from backend.app.models.user import User
from backend.app.models.branch import Branch
from backend.app.models.transaction import Transaction
from backend.app.models.department import Department
from backend.app.schemas.dashboard import (
    FranchisorDashboardResponse,
    FranchisorDashboardTotals,
    BranchTurnoverSummary,
    BranchDashboardResponse,
    BranchDashboardSummary,
    MonthlyTrendItem,
    DepartmentBreakdownItem,
    TopEmployeeBonusItem
)
from backend.app.api.reconciliation import build_reconciliation_data
from backend.app.api.bonus import build_period_bonus_data

router = APIRouter(prefix="/dashboard", tags=["Dashboard & Analitik"])

@router.get("/franchisor", response_model=FranchisorDashboardResponse)
def get_franchisor_dashboard(
    year: int = Query(..., ge=2000, le=2100, description="Dönem Yılı"),
    month: int = Query(..., ge=1, le=12, description="Dönem Ayı"),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN")),
    db: Session = Depends(get_db)
):
    """
    Franchisor Admin için karşılaştırmalı bayi ciro ve komisyon dashboard'u.
    Tüm bayilerin seçilen dönemdeki performansını, merkez ve bayi paylarını sıralı listeler.
    """
    query = db.query(Branch)
    if current_user.franchisor_id:
        query = query.filter(Branch.franchisor_id == current_user.franchisor_id)
    branches_db = query.filter(Branch.is_active == True).order_by(Branch.name.asc()).all()

    branch_summaries: List[BranchTurnoverSummary] = []
    total_turnover = Decimal("0.00")
    total_franchisor_share = Decimal("0.00")
    total_bayi_share = Decimal("0.00")
    total_tx_count = 0

    for b in branches_db:
        rec = build_reconciliation_data(
            branch_id=b.id,
            year=year,
            month=month,
            collector_party=None,
            vat_rate=None,
            db=db
        )
        
        summary = BranchTurnoverSummary(
            branch_id=b.id,
            branch_name=b.name,
            total_turnover=rec.total_turnover_excl_vat,
            franchisor_share=rec.franchisor_share_excl_vat,
            bayi_share=rec.bayi_share_excl_vat,
            transaction_count=rec.total_transactions,
            collector_party=rec.invoice_summary.collector_party.value,
            invoice_direction=f"{rec.invoice_summary.issuer} ➔ {rec.invoice_summary.recipient}",
            invoice_net_payable=rec.invoice_summary.total_amount_incl_vat
        )
        branch_summaries.append(summary)

        total_turnover += rec.total_turnover_excl_vat
        total_franchisor_share += rec.franchisor_share_excl_vat
        total_bayi_share += rec.bayi_share_excl_vat
        total_tx_count += rec.total_transactions

    # Rank by turnover descending
    branch_summaries.sort(key=lambda s: s.total_turnover, reverse=True)

    totals = FranchisorDashboardTotals(
        total_branches=len(branches_db),
        active_branches=len(branches_db),
        total_turnover=total_turnover,
        total_franchisor_share=total_franchisor_share,
        total_bayi_share=total_bayi_share,
        total_transactions=total_tx_count
    )

    return FranchisorDashboardResponse(
        year=year,
        month=month,
        totals=totals,
        branches=branch_summaries
    )

@router.get("/branch", response_model=BranchDashboardResponse)
def get_branch_dashboard(
    year: int = Query(..., ge=2000, le=2100, description="Dönem Yılı"),
    month: int = Query(..., ge=1, le=12, description="Dönem Ayı"),
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Bayi bazlı dashboard:
    - Seçilen döneme ait özet KPI kartları
    - Son 6 aylık ciro ve komisyon trendi
    - Departman ciro kırılımı
    - En yüksek prim alan ilk 5 personel
    """
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Bayi bulunamadı.")

    # 1. Current Period Reconciliation
    current_rec = build_reconciliation_data(
        branch_id=branch_id,
        year=year,
        month=month,
        collector_party=None,
        vat_rate=None,
        db=db
    )

    # 2. Current Period Bonus Report
    bonus_rep = build_period_bonus_data(
        branch_id=branch_id,
        year=year,
        month=month,
        db=db
    )

    # Summary Card
    total_bonuses = bonus_rep.grand_total_bonus
    net_margin = current_rec.bayi_share_excl_vat - total_bonuses
    summary = BranchDashboardSummary(
        branch_id=branch.id,
        branch_name=branch.name,
        year=year,
        month=month,
        total_turnover=current_rec.total_turnover_excl_vat,
        franchisor_share=current_rec.franchisor_share_excl_vat,
        bayi_share=current_rec.bayi_share_excl_vat,
        total_bonuses=total_bonuses,
        net_bayi_margin=net_margin,
        transaction_count=current_rec.total_transactions,
        collector_party=current_rec.invoice_summary.collector_party.value
    )

    # 3. Monthly Trends (last 6 months ending at year, month)
    monthly_trends: List[MonthlyTrendItem] = []
    # Build list of (y, m) for last 6 months
    target_months = []
    curr_y, curr_m = year, month
    for _ in range(6):
        target_months.insert(0, (curr_y, curr_m))
        curr_m -= 1
        if curr_m == 0:
            curr_m = 12
            curr_y -= 1

    for y, m in target_months:
        if y == year and m == month:
            rec_m = current_rec
        else:
            rec_m = build_reconciliation_data(
                branch_id=branch_id,
                year=y,
                month=m,
                collector_party=None,
                vat_rate=None,
                db=db
            )
        monthly_trends.append(MonthlyTrendItem(
            period=f"{y}-{m:02d}",
            year=y,
            month=m,
            turnover=rec_m.total_turnover_excl_vat,
            franchisor_share=rec_m.franchisor_share_excl_vat,
            bayi_share=rec_m.bayi_share_excl_vat,
            transaction_count=rec_m.total_transactions
        ))

    # 4. Department Breakdown
    dept_breakdown: List[DepartmentBreakdownItem] = []
    for d in current_rec.department_breakdown:
        dept_breakdown.append(DepartmentBreakdownItem(
            department_id=d.department_id,
            department_name=d.department_name,
            turnover=d.total_turnover_excl_vat,
            transaction_count=d.transaction_count,
            percentage=round(d.percentage_of_total, 2)
        ))

    # 5. Top 5 Bonus Earners
    emp_bonus_sorted = sorted(bonus_rep.items, key=lambda e: e.total_bonus, reverse=True)
    top_5 = emp_bonus_sorted[:5]
    top_employees: List[TopEmployeeBonusItem] = []
    for idx, eb in enumerate(top_5, start=1):
        top_employees.append(TopEmployeeBonusItem(
            rank=idx,
            employee_id=eb.employee_id,
            employee_name=eb.employee_name,
            role_name=eb.role_name,
            department_name=eb.department_name,
            turnover=eb.total_turnover_excl_vat,
            bonus_amount=eb.total_bonus
        ))

    return BranchDashboardResponse(
        summary=summary,
        monthly_trends=monthly_trends,
        department_breakdown=dept_breakdown,
        top_bonus_employees=top_employees
    )
