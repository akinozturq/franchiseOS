from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_roles, get_active_branch_id
from backend.app.models.user import User
from backend.app.models.commission_tier import CommissionTier
from backend.app.schemas.commission_tier import (
    CommissionTierCreate,
    CommissionTierUpdate,
    CommissionTierOut,
    CommissionTierBatch
)

router = APIRouter(prefix="/commission-tiers", tags=["Komisyon Dilimleri"])

from datetime import date
from sqlalchemy import or_
from backend.app.models.rule_change_log import RuleChangeLog
from backend.app.schemas.rule_change_log import RuleChangeLogOut

@router.get("", response_model=List[CommissionTierOut])
def list_tiers(
    target_date: date = None,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(CommissionTier).filter(CommissionTier.branch_id == branch_id)
    if target_date:
        query = query.filter(
            CommissionTier.effective_from <= target_date,
            or_(CommissionTier.effective_to == None, CommissionTier.effective_to > target_date)
        )
    else:
        query = query.filter(CommissionTier.effective_to == None)
    return query.order_by(CommissionTier.min_amount.asc()).all()

@router.get("/history", response_model=List[RuleChangeLogOut])
def get_tier_history(
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Komisyon dilimleri kural değişiklik geçmişini listeler."""
    return db.query(RuleChangeLog).filter(
        RuleChangeLog.branch_id == branch_id,
        RuleChangeLog.rule_type == "COMMISSION_TIER"
    ).order_by(RuleChangeLog.created_at.desc()).all()

@router.post("", response_model=CommissionTierOut, status_code=status.HTTP_201_CREATED)
def create_tier(
    tier_in: CommissionTierCreate,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN")),
    db: Session = Depends(get_db)
):
    if tier_in.max_amount is not None and tier_in.max_amount <= tier_in.min_amount:
        raise HTTPException(status_code=400, detail="Üst sınır, alt sınırdan büyük olmalıdır.")

    today = date.today()
    tier = CommissionTier(
        branch_id=branch_id,
        min_amount=tier_in.min_amount,
        max_amount=tier_in.max_amount,
        rate=tier_in.rate,
        effective_from=today,
        effective_to=None,
        created_by_user_id=current_user.id
    )
    db.add(tier)
    db.flush()

    log = RuleChangeLog(
        branch_id=branch_id,
        user_id=current_user.id,
        rule_type="COMMISSION_TIER",
        entity_id=tier.id,
        action="CREATE",
        effective_from=today,
        description=f"Yeni dilim oluşturuldu: {tier.min_amount} - {tier.max_amount or 'Sonsuz'} (%{tier.rate * 100:.1f})",
        old_values=None,
        new_values={
            "min_amount": str(tier.min_amount),
            "max_amount": str(tier.max_amount) if tier.max_amount else None,
            "rate": str(tier.rate)
        }
    )
    db.add(log)
    db.commit()
    db.refresh(tier)
    return tier

@router.put("/{tier_id}", response_model=CommissionTierOut)
def update_tier(
    tier_id: int,
    tier_in: CommissionTierUpdate,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN")),
    db: Session = Depends(get_db)
):
    old_tier = db.query(CommissionTier).filter(
        CommissionTier.id == tier_id,
        CommissionTier.branch_id == branch_id,
        CommissionTier.effective_to == None
    ).first()
    if not old_tier:
        raise HTTPException(status_code=404, detail="Aktif komisyon dilimi bulunamadı.")

    today = date.today()
    new_min = tier_in.min_amount if tier_in.min_amount is not None else old_tier.min_amount
    new_max = tier_in.max_amount if tier_in.max_amount is not None else old_tier.max_amount
    new_rate = tier_in.rate if tier_in.rate is not None else old_tier.rate

    if new_max is not None and new_max <= new_min:
        raise HTTPException(status_code=400, detail="Üst sınır, alt sınırdan büyük olmalıdır.")

    # 1. Close old tier version
    old_tier.effective_to = today

    # 2. Insert new tier version
    new_tier = CommissionTier(
        branch_id=branch_id,
        min_amount=new_min,
        max_amount=new_max,
        rate=new_rate,
        effective_from=today,
        effective_to=None,
        created_by_user_id=current_user.id
    )
    db.add(new_tier)
    db.flush()

    # 3. Log change
    log = RuleChangeLog(
        branch_id=branch_id,
        user_id=current_user.id,
        rule_type="COMMISSION_TIER",
        entity_id=new_tier.id,
        action="UPDATE",
        effective_from=today,
        description=f"Dilim güncellendi: {new_min} - {new_max or 'Sonsuz'} (%{new_rate * 100:.1f})",
        old_values={
            "min_amount": str(old_tier.min_amount),
            "max_amount": str(old_tier.max_amount) if old_tier.max_amount else None,
            "rate": str(old_tier.rate)
        },
        new_values={
            "min_amount": str(new_min),
            "max_amount": str(new_max) if new_max else None,
            "rate": str(new_rate)
        }
    )
    db.add(log)
    db.commit()
    db.refresh(new_tier)
    return new_tier

@router.delete("/{tier_id}")
def delete_tier(
    tier_id: int,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN")),
    db: Session = Depends(get_db)
):
    tier = db.query(CommissionTier).filter(
        CommissionTier.id == tier_id,
        CommissionTier.branch_id == branch_id,
        CommissionTier.effective_to == None
    ).first()
    if not tier:
        raise HTTPException(status_code=404, detail="Aktif komisyon dilimi bulunamadı.")

    today = date.today()
    tier.effective_to = today

    log = RuleChangeLog(
        branch_id=branch_id,
        user_id=current_user.id,
        rule_type="COMMISSION_TIER",
        entity_id=tier.id,
        action="DELETE",
        effective_from=today,
        description=f"Dilim sonlandırıldı: {tier.min_amount} - {tier.max_amount or 'Sonsuz'}",
        old_values={
            "min_amount": str(tier.min_amount),
            "max_amount": str(tier.max_amount) if tier.max_amount else None,
            "rate": str(tier.rate)
        },
        new_values=None
    )
    db.add(log)
    db.commit()
    return {"detail": "Komisyon dilimi başarıyla kapatıldı (arşivlendi)."}

@router.put("/batch/save", response_model=List[CommissionTierOut])
def batch_save_tiers(
    batch_in: CommissionTierBatch,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN")),
    db: Session = Depends(get_db)
):
    """Archives existing active commission tiers and creates new versions atomically."""
    if not batch_in.tiers:
        raise HTTPException(status_code=400, detail="En az bir dilim tanımlanmalıdır.")

    # Validate each tier
    for t in batch_in.tiers:
        if t.max_amount is not None and t.max_amount <= t.min_amount:
            raise HTTPException(
                status_code=400,
                detail=f"Üst sınır ({t.max_amount}), alt sınırdan ({t.min_amount}) büyük olmalıdır."
            )

    today = date.today()

    # 1. Close all currently active tiers for this branch
    existing_active = db.query(CommissionTier).filter(
        CommissionTier.branch_id == branch_id,
        CommissionTier.effective_to == None
    ).all()
    for ot in existing_active:
        ot.effective_to = today

    # 2. Insert new versions
    new_tiers = []
    for t in batch_in.tiers:
        tier = CommissionTier(
            branch_id=branch_id,
            min_amount=t.min_amount,
            max_amount=t.max_amount,
            rate=t.rate,
            effective_from=today,
            effective_to=None,
            created_by_user_id=current_user.id
        )
        db.add(tier)
        new_tiers.append(tier)

    # 3. Log batch change
    log = RuleChangeLog(
        branch_id=branch_id,
        user_id=current_user.id,
        rule_type="COMMISSION_TIER",
        entity_id=None,
        action="BATCH_UPDATE",
        effective_from=today,
        description=f"Tüm komisyon dilimleri toplu olarak güncellendi ({len(new_tiers)} dilim).",
        old_values={"tier_count": len(existing_active)},
        new_values={"tier_count": len(new_tiers)}
    )
    db.add(log)
    db.commit()

    for nt in new_tiers:
        db.refresh(nt)

    return sorted(new_tiers, key=lambda x: x.min_amount)
