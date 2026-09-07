from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime, timezone, date
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_roles, get_active_branch_id
from backend.app.models.user import User
from backend.app.models.branch import Branch
from backend.app.models.period_closure import PeriodClosure
from backend.app.models.notification import Notification
from backend.app.schemas.notification import NotificationOut

router = APIRouter(prefix="/notifications", tags=["Bildirimler"])

@router.get("", response_model=List[NotificationOut])
def list_notifications(
    unread_only: bool = Query(False, description="Sadece okunmamış bildirimler"),
    limit: int = Query(50, ge=1, le=100),
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Notification)

    if current_user.role == "FRANCHISOR_ADMIN":
        # Franchisor admin can see all notifications or notifications for this branch
        query = query.filter(
            or_(
                Notification.branch_id == branch_id,
                Notification.branch_id.is_(None),
                Notification.user_id == current_user.id
            )
        )
    else:
        # Branch users see branch notifications and user-specific notifications
        query = query.filter(
            or_(
                Notification.branch_id == branch_id,
                Notification.user_id == current_user.id
            )
        )

    if unread_only:
        query = query.filter(Notification.is_read == False)

    return query.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit).all()

@router.get("/unread-count")
def get_unread_count(
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Notification).filter(Notification.is_read == False)

    if current_user.role == "FRANCHISOR_ADMIN":
        query = query.filter(
            or_(
                Notification.branch_id == branch_id,
                Notification.branch_id.is_(None),
                Notification.user_id == current_user.id
            )
        )
    else:
        query = query.filter(
            or_(
                Notification.branch_id == branch_id,
                Notification.user_id == current_user.id
            )
        )

    count = query.count()
    return {"unread_count": count}

@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_as_read(
    notification_id: int,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Bildirim bulunamadı.")

    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif

@router.post("/mark-all-read")
def mark_all_as_read(
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Notification).filter(Notification.is_read == False)
    if current_user.role == "FRANCHISOR_ADMIN":
        query = query.filter(
            or_(
                Notification.branch_id == branch_id,
                Notification.branch_id.is_(None),
                Notification.user_id == current_user.id
            )
        )
    else:
        query = query.filter(
            or_(
                Notification.branch_id == branch_id,
                Notification.user_id == current_user.id
            )
        )

    updated_count = query.update({Notification.is_read: True}, synchronize_session=False)
    db.commit()
    return {"detail": f"{updated_count} bildirim okundu olarak işaretlendi."}

@router.post("/check-closure-reminders")
def check_closure_reminders(
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN")),
    db: Session = Depends(get_db)
):
    """
    Kapatılmamış önceki dönemler için otomatik hatırlatma bildirimleri üretir.
    """
    today = date.today()
    # Check previous month
    prev_month = today.month - 1 if today.month > 1 else 12
    prev_year = today.year if today.month > 1 else today.year - 1

    branches = db.query(Branch).filter(Branch.is_active == True).all()
    created_count = 0

    for b in branches:
        closed = db.query(PeriodClosure).filter(
            PeriodClosure.branch_id == b.id,
            PeriodClosure.year == prev_year,
            PeriodClosure.month == prev_month,
            PeriodClosure.status == "CLOSED",
            PeriodClosure.reopened_at.is_(None)
        ).first()

        if not closed:
            # Check if reminder already sent recently
            existing_notifs = db.query(Notification).filter(
                Notification.branch_id == b.id,
                Notification.type == "PERIOD_CLOSURE_REMINDER"
            ).all()

            already_sent = any(
                (n.payload or {}).get("year") == prev_year and (n.payload or {}).get("month") == prev_month
                for n in existing_notifs
            )

            if not already_sent:
                notif = Notification(
                    branch_id=b.id,
                    type="PERIOD_CLOSURE_REMINDER",
                    title=f"Dönem Kapatma Hatırlatması: {prev_year}-{prev_month:02d}",
                    message=f"{b.name} için {prev_year}-{prev_month:02d} dönemi henüz kapatılmamıştır. Lütfen mutabakat ve prim raporlarını inceleyip kapatınız.",
                    payload={"branch_id": b.id, "year": prev_year, "month": prev_month},
                    channel="in-app"
                )
                db.add(notif)
                created_count += 1

    db.commit()
    return {"created_reminders_count": created_count}
