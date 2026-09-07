from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_roles, get_active_branch_id
from backend.app.models.user import User
from backend.app.models.branch import Branch
from backend.app.models.period_closure import PeriodClosure
from backend.app.models.notification import Notification
from backend.app.schemas.period_closure import (
    PeriodClosureRequest,
    PeriodClosureCreate,
    PeriodClosureReopen,
    PeriodClosureStatusOut,
    PeriodClosureOut,
    InvoiceDataExportOut
)
from backend.app.api.reconciliation import build_reconciliation_data
from backend.app.api.bonus import build_period_bonus_data

router = APIRouter(prefix="/period-closures", tags=["Dönem Kapama"])

@router.get("/status", response_model=PeriodClosureStatusOut)
def get_period_closure_status(
    year: int = Query(..., description="Yıl"),
    month: int = Query(..., description="Ay (1-12)"),
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    closure = db.query(PeriodClosure).filter(
        PeriodClosure.branch_id == branch_id,
        PeriodClosure.year == year,
        PeriodClosure.month == month,
        PeriodClosure.status == "CLOSED",
        PeriodClosure.reopened_at.is_(None)
    ).order_by(PeriodClosure.id.desc()).first()

    if closure:
        closed_by_name = (
            closure.closed_by.full_name or closure.closed_by.username
            if closure.closed_by else "Franchisor Admin"
        )
        return PeriodClosureStatusOut(
            year=year,
            month=month,
            is_closed=True,
            status=closure.status,
            closure_id=closure.id,
            closed_at=closure.closed_at,
            closed_by_name=closed_by_name,
            reopen_reason=None
        )

    # Check if there is a pending closure request
    requested = db.query(PeriodClosure).filter(
        PeriodClosure.branch_id == branch_id,
        PeriodClosure.year == year,
        PeriodClosure.month == month,
        PeriodClosure.status == "CLOSURE_REQUESTED",
        PeriodClosure.reopened_at.is_(None)
    ).order_by(PeriodClosure.id.desc()).first()

    if requested:
        return PeriodClosureStatusOut(
            year=year,
            month=month,
            is_closed=False,
            status="CLOSURE_REQUESTED",
            closure_id=requested.id,
            closed_at=None,
            closed_by_name=None,
            reopen_reason=None
        )

    # Check if last record was reopened
    last_record = db.query(PeriodClosure).filter(
        PeriodClosure.branch_id == branch_id,
        PeriodClosure.year == year,
        PeriodClosure.month == month
    ).order_by(PeriodClosure.id.desc()).first()

    if last_record and last_record.status == "REOPENED":
        return PeriodClosureStatusOut(
            year=year,
            month=month,
            is_closed=False,
            status="REOPENED",
            closure_id=last_record.id,
            closed_at=last_record.closed_at,
            closed_by_name=last_record.closed_by.full_name if last_record.closed_by else None,
            reopen_reason=last_record.reopen_reason
        )

    return PeriodClosureStatusOut(
        year=year,
        month=month,
        is_closed=False,
        status="OPEN",
        closure_id=None,
        closed_at=None,
        closed_by_name=None,
        reopen_reason=None
    )

@router.get("", response_model=List[PeriodClosureOut])
def list_period_closures(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(PeriodClosure).filter(PeriodClosure.branch_id == branch_id)
    if year is not None:
        query = query.filter(PeriodClosure.year == year)
    if month is not None:
        query = query.filter(PeriodClosure.month == month)
    if status_filter is not None:
        query = query.filter(PeriodClosure.status == status_filter)

    return query.order_by(PeriodClosure.id.desc()).all()

@router.post("/request", response_model=PeriodClosureOut, status_code=status.HTTP_201_CREATED)
def request_period_closure(
    body: PeriodClosureRequest,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN", "BAYI_ADMIN")),
    db: Session = Depends(get_db)
):
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Bayi bulunamadı.")

    # Check if already closed
    existing_closed = db.query(PeriodClosure).filter(
        PeriodClosure.branch_id == branch_id,
        PeriodClosure.year == body.year,
        PeriodClosure.month == body.month,
        PeriodClosure.status == "CLOSED",
        PeriodClosure.reopened_at.is_(None)
    ).first()
    if existing_closed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{body.year}-{body.month:02d} dönemi zaten kapatılmış."
        )

    # Check if already requested
    existing_req = db.query(PeriodClosure).filter(
        PeriodClosure.branch_id == branch_id,
        PeriodClosure.year == body.year,
        PeriodClosure.month == body.month,
        PeriodClosure.status == "CLOSURE_REQUESTED",
        PeriodClosure.reopened_at.is_(None)
    ).first()
    if existing_req:
        return existing_req

    closure_req = PeriodClosure(
        branch_id=branch_id,
        year=body.year,
        month=body.month,
        status="CLOSURE_REQUESTED",
        closed_by_user_id=current_user.id
    )
    db.add(closure_req)

    # In-app notification for Franchisor Admins
    notification = Notification(
        branch_id=branch_id,
        type="PERIOD_CLOSURE_REQUESTED",
        title=f"Dönem Kapatma Talebi: {branch.name} ({body.year}-{body.month:02d})",
        message=f"{current_user.full_name or current_user.username} tarafından {branch.name} için {body.year}-{body.month:02d} dönemi mutabakat kapama onayı talep edildi.",
        payload={"branch_id": branch_id, "year": body.year, "month": body.month, "requester_id": current_user.id},
        channel="in-app"
    )
    db.add(notification)

    db.commit()
    db.refresh(closure_req)
    return closure_req

@router.post("", response_model=PeriodClosureOut, status_code=status.HTTP_201_CREATED)
def close_period(
    body: PeriodClosureCreate,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN")),
    db: Session = Depends(get_db)
):
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Bayi bulunamadı.")

    # Check if currently closed
    existing_closed = db.query(PeriodClosure).filter(
        PeriodClosure.branch_id == branch_id,
        PeriodClosure.year == body.year,
        PeriodClosure.month == body.month,
        PeriodClosure.status == "CLOSED",
        PeriodClosure.reopened_at.is_(None)
    ).first()
    if existing_closed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{body.year}-{body.month:02d} dönemi zaten kapatılmıştır."
        )

    # 1. Compute full reconciliation snapshot
    rec_data = build_reconciliation_data(
        branch_id=branch_id,
        year=body.year,
        month=body.month,
        collector_party=None,
        vat_rate=None,
        db=db
    )
    rec_snapshot = rec_data.model_dump(mode="json")

    # 2. Compute full bonus snapshot
    bonus_data = build_period_bonus_data(
        branch_id=branch_id,
        year=body.year,
        month=body.month,
        db=db
    )
    bonus_snapshot = bonus_data.model_dump(mode="json")

    # 3. Create frozen PeriodClosure
    closure = PeriodClosure(
        branch_id=branch_id,
        year=body.year,
        month=body.month,
        status="CLOSED",
        closed_at=datetime.now(timezone.utc),
        closed_by_user_id=current_user.id,
        reconciliation_snapshot=rec_snapshot,
        bonus_snapshot=bonus_snapshot
    )
    db.add(closure)

    # 4. In-app notification for branch users
    notification = Notification(
        branch_id=branch_id,
        type="PERIOD_CLOSED",
        title=f"{body.year}-{body.month:02d} Dönemi Kapatıldı",
        message=f"{branch.name} için {body.year}-{body.month:02d} dönemi mutabakat ve prim raporları dondurularak resmen kapatıldı.",
        payload={"branch_id": branch_id, "year": body.year, "month": body.month, "closed_by": current_user.full_name or current_user.username},
        channel="in-app"
    )
    db.add(notification)

    # Also clean up any pending CLOSURE_REQUESTED record
    pending_req = db.query(PeriodClosure).filter(
        PeriodClosure.branch_id == branch_id,
        PeriodClosure.year == body.year,
        PeriodClosure.month == body.month,
        PeriodClosure.status == "CLOSURE_REQUESTED"
    ).all()
    for req in pending_req:
        db.delete(req)

    db.commit()
    db.refresh(closure)
    return closure

@router.post("/{closure_id}/reopen", response_model=PeriodClosureOut)
def reopen_period(
    closure_id: int,
    body: PeriodClosureReopen,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN")),
    db: Session = Depends(get_db)
):
    closure = db.query(PeriodClosure).filter(
        PeriodClosure.id == closure_id,
        PeriodClosure.branch_id == branch_id
    ).first()
    if not closure:
        raise HTTPException(status_code=404, detail="Dönem kapama kaydı bulunamadı.")

    if closure.status != "CLOSED" or closure.reopened_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Yalnızca şu anda kapalı olan dönemler yeniden açılabilir."
        )

    closure.status = "REOPENED"
    closure.reopened_at = datetime.now(timezone.utc)
    closure.reopened_by_user_id = current_user.id
    closure.reopen_reason = body.reopen_reason.strip()

    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    branch_name = branch.name if branch else "Bayi"

    # Notification
    notification = Notification(
        branch_id=branch_id,
        type="PERIOD_REOPENED",
        title=f"{closure.year}-{closure.month:02d} Dönemi Yeniden Açıldı",
        message=f"{branch_name} için {closure.year}-{closure.month:02d} dönemi şu gerekçeyle yeniden açıldı: {closure.reopen_reason}",
        payload={"branch_id": branch_id, "year": closure.year, "month": closure.month, "reopened_by": current_user.full_name or current_user.username, "reopen_reason": closure.reopen_reason},
        channel="in-app"
    )
    db.add(notification)

    db.commit()
    db.refresh(closure)
    return closure

@router.get("/{closure_id}/invoice-data", response_model=InvoiceDataExportOut)
def export_invoice_data(
    closure_id: int,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN", "BAYI_ADMIN")),
    db: Session = Depends(get_db)
):
    closure = db.query(PeriodClosure).filter(
        PeriodClosure.id == closure_id,
        PeriodClosure.branch_id == branch_id
    ).first()
    if not closure:
        raise HTTPException(status_code=404, detail="Dönem kapama kaydı bulunamadı.")

    if not closure.reconciliation_snapshot:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu kapama kaydına ait dondurulmuş mutabakat verisi bulunamadı."
        )

    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    snapshot = closure.reconciliation_snapshot
    inv_summary = snapshot.get("invoice_summary") or {}

    issuer_str = inv_summary.get("issuer", "Franchisor")
    recipient_str = inv_summary.get("recipient", "Bayi")
    inv_dir = f"{issuer_str} -> {recipient_str}"
    collector = inv_summary.get("collector_party") or snapshot.get("collector_party", "BAYI")

    # Franchisor static entity info
    franchisor_info = {
        "title": "Franchise Genel Merkez A.Ş.",
        "tax_office": "Büyük Mükellefler V.D.",
        "tax_id": "1234567890",
        "address": "Büyükdere Cad. No: 100, Levent, İstanbul"
    }

    # Branch entity info
    branch_info = {
        "title": branch.name if branch else "Bayi",
        "tax_office": branch.tax_office or "Vergi Dairesi",
        "tax_id": branch.tax_id or "1111111111",
        "address": branch.address or "Bayi Adresi",
        "code": f"BR-{branch.id}" if branch else "BR-1"
    }

    if "Franchisor" in issuer_str:
        issuer = franchisor_info
        recipient = branch_info
    else:
        issuer = branch_info
        recipient = franchisor_info

    net_amt = inv_summary.get("amount_excl_vat") or snapshot.get("reconciliation_amount_excl_vat", "0.00")
    vat_amt = inv_summary.get("vat_amount") or snapshot.get("reconciliation_vat_amount", "0.00")
    tot_amt = inv_summary.get("total_amount_incl_vat") or snapshot.get("reconciliation_amount_incl_vat", "0.00")
    v_rate = inv_summary.get("vat_rate") or snapshot.get("vat_rate", "0.20")

    line_items = [
        {
            "item_name": f"{closure.year}-{closure.month:02d} Dönemi Franchise Marka & Royalty Hizmet Bedeli",
            "quantity": 1,
            "unit": "Hizmet",
            "unit_price": str(net_amt),
            "amount_excl_vat": str(net_amt),
            "vat_rate": str(v_rate),
            "vat_amount": str(vat_amt),
            "amount_incl_vat": str(tot_amt)
        }
    ]

    closed_by_name = (
        closure.closed_by.full_name or closure.closed_by.username
        if closure.closed_by else "Franchisor Admin"
    )

    return InvoiceDataExportOut(
        document_id=f"EINV-{closure.year}{closure.month:02d}-BR{branch.id if branch else 1}-{closure.id}",
        issue_date=closure.closed_at.strftime("%Y-%m-%d"),
        period=f"{closure.year}-{closure.month:02d}",
        currency="TRY",
        invoice_direction=inv_dir,
        collector_party=collector,
        issuer=issuer,
        recipient=recipient,
        amount_excl_vat=str(net_amt),
        vat_rate=str(v_rate),
        vat_amount=str(vat_amt),
        total_amount_incl_vat=str(tot_amt),
        line_items=line_items,
        closure_audit={
            "closure_id": closure.id,
            "closed_at": closure.closed_at.isoformat(),
            "closed_by": closed_by_name,
            "status": closure.status
        }
    )
