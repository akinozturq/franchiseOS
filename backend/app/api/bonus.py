from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import extract

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, get_active_branch_id
from backend.app.models.user import User
from backend.app.models.branch import Branch
from backend.app.models.employee import Employee
from backend.app.models.role import Role
from backend.app.models.transaction import Transaction
from backend.app.models.department import Department
from backend.app.schemas.bonus import PeriodBonusReportResponse
from backend.app.services.bonus_service import (
    EmployeeDTO,
    RoleTierDTO,
    BonusTransactionDTO,
    calculate_period_bonuses
)
from backend.app.services.export_service import generate_bonus_excel
from backend.app.services.pdf_service import generate_bonus_pdf

router = APIRouter(prefix="/bonus", tags=["Personel Prim Raporu"])

from datetime import date
import calendar
from sqlalchemy import or_
from backend.app.models.period_closure import PeriodClosure
from backend.app.models.role_commission_tier import RoleCommissionTier
from backend.app.models.transaction_category import TransactionCategory

def build_period_bonus_data(branch_id: int, year: int, month: int, db: Session) -> PeriodBonusReportResponse:
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Bayi bulunamadı.")
    period_str = f"{year}-{month:02d}"

    # 1. Check if period is officially closed -> return frozen snapshot!
    closure = db.query(PeriodClosure).filter(
        PeriodClosure.branch_id == branch.id,
        PeriodClosure.year == year,
        PeriodClosure.month == month,
        PeriodClosure.status == "CLOSED",
        PeriodClosure.reopened_at == None
    ).first()

    if closure and closure.bonus_snapshot:
        snapshot = dict(closure.bonus_snapshot)
        snapshot["is_closed"] = True
        snapshot["closed_at"] = closure.closed_at.isoformat() if closure.closed_at else None
        snapshot["closed_by_name"] = (
            closure.closed_by.full_name or closure.closed_by.username
            if closure.closed_by else "Franchisor Admin"
        )
        return PeriodBonusReportResponse(**snapshot)

    last_day = calendar.monthrange(year, month)[1]
    period_date = date(year, month, last_day)

    # 2. Fetch active employees
    employees_db = db.query(Employee).filter(
        Employee.branch_id == branch.id,
        Employee.is_active == True
    ).order_by(Employee.id.asc()).all()

    # 2. Preload role tiers for all roles in this branch to eliminate N+1 queries
    all_role_tiers = db.query(RoleCommissionTier).join(Role).filter(
        Role.branch_id == branch.id
    ).all()

    emp_dtos: List[EmployeeDTO] = []
    for emp in employees_db:
        role = emp.role
        tiers_dto = []
        if role:
            role_tiers_matched = [
                t for t in all_role_tiers
                if t.role_id == role.id and t.effective_from <= period_date and (t.effective_to is None or t.effective_to > period_date)
            ]
            if not role_tiers_matched:
                role_tiers_matched = [t for t in all_role_tiers if t.role_id == role.id]
            role_tiers_matched.sort(key=lambda t: t.min_amount)

            tiers_dto = [
                RoleTierDTO(
                    id=t.id,
                    min_amount=t.min_amount,
                    max_amount=t.max_amount,
                    rate=t.rate
                )
                for t in role_tiers_matched
            ]

        emp_dtos.append(EmployeeDTO(
            id=emp.id,
            full_name=emp.full_name,
            role_id=role.id if role else 0,
            role_name=role.name if role else "Atanmamış",
            turnover_source=role.turnover_source if role else "kendi_islemleri",
            department_id=emp.department_id,
            department_name=emp.department.name if emp.department else None,
            is_active=emp.is_active,
            commission_tiers=tiers_dto
        ))

    # 3. Fetch all transactions for this month and year
    txs_db = db.query(Transaction).filter(
        Transaction.branch_id == branch.id,
        extract("year", Transaction.date) == year,
        extract("month", Transaction.date) == month
    ).all()

    dept_map = {d.id: d.name for d in db.query(Department).filter(Department.branch_id == branch.id).all()}

    # Preload all category rules for this branch to eliminate N+1 queries
    all_cat_rules = db.query(TransactionCategory).filter(
        TransactionCategory.branch_id == branch.id
    ).all()

    def get_bonus_override_for_date(cat_name: Optional[str], tx_date: date) -> Optional[Decimal]:
        if not cat_name:
            return None
        for cr in all_cat_rules:
            if cr.name == cat_name and cr.effective_from <= tx_date and (cr.effective_to is None or cr.effective_to > tx_date):
                return cr.bonus_override_rate
        return None

    tx_dtos: List[BonusTransactionDTO] = []
    for tx in txs_db:
        cat_name = tx.category.name if tx.category else None
        override_rate = get_bonus_override_for_date(cat_name, tx.date)
        if override_rate is None and tx.category:
            override_rate = tx.category.bonus_override_rate

        tx_dtos.append(BonusTransactionDTO(
            id=tx.id,
            employee_id=tx.employee_id,
            employee_name=tx.employee.full_name if tx.employee else tx.staff_name,
            department_id=tx.department_id,
            department_name=dept_map.get(tx.department_id, "Genel"),
            category_id=tx.category_id,
            category_name=cat_name,
            bonus_override_rate=override_rate,
            amount_excl_vat=tx.amount_excl_vat
        ))

    # 4. Calculate bonuses
    result = calculate_period_bonuses(
        period=period_str,
        employees=emp_dtos,
        all_period_transactions=tx_dtos
    )

    resp_dict = result.model_dump()
    resp_dict["is_closed"] = False
    resp_dict["closed_at"] = None
    resp_dict["closed_by_name"] = None
    return PeriodBonusReportResponse.model_validate(resp_dict)

@router.get("", response_model=PeriodBonusReportResponse)
def get_bonus_report(
    year: int = Query(..., ge=2000, le=2100, description="Dönem Yılı (örn. 2026)"),
    month: int = Query(..., ge=1, le=12, description="Dönem Ayı (1-12)"),
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Seçilen dönem için personel prim ve hak ediş raporunu hesaplar.
    Her personelin rolüne, ciro kaynağına, kademeli dilimlerine ve istisnalı kategorilere göre
    ayrıntılı prim kırılımını ve genel toplamı sunar.
    """
    return build_period_bonus_data(branch_id, year, month, db)

@router.get("/export")
def export_bonus_report_excel(
    year: int = Query(..., ge=2000, le=2100, description="Dönem Yılı (örn. 2026)"),
    month: int = Query(..., ge=1, le=12, description="Dönem Ayı (1-12)"),
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Personel prim raporunu ekranla birebir eşleşen Excel (.xlsx) tablosu olarak dışa aktarır.
    """
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    branch_name = branch.name if branch else "Bayi"
    report = build_period_bonus_data(branch_id, year, month, db)
    excel_stream = generate_bonus_excel(report, branch_name=branch_name)
    filename = f"Personel_Prim_Raporu_{year}_{month:02d}.xlsx"

    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/export-pdf")
def export_bonus_pdf_endpoint(
    year: int = Query(..., ge=2000, le=2100, description="Dönem Yılı (örn. 2026)"),
    month: int = Query(..., ge=1, le=12, description="Dönem Ayı (1-12)"),
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Personel prim raporunu resmi PDF belgesi olarak indirir.
    Kapalı dönem için dondurulmuş snapshot verisinden, açık dönem için canlı hesaplamadan üretilir.
    """
    report = build_period_bonus_data(branch_id, year, month, db)
    data = report.model_dump(mode="json")
    
    pdf_stream = generate_bonus_pdf(data)
    filename = f"Personel_Prim_Raporu_{year}_{month:02d}.pdf"

    return StreamingResponse(
        pdf_stream,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
