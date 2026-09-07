from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_roles, get_active_branch_id
from backend.app.models.user import User
from backend.app.models.role import Role
from backend.app.models.role_commission_tier import RoleCommissionTier
from backend.app.schemas.role import (
    RoleCreate,
    RoleUpdate,
    RoleOut,
    RoleCommissionTierCreate,
    RoleCommissionTierOut
)

router = APIRouter(prefix="/roles", tags=["Personel Rolleri ve Prim Dilimleri"])

from datetime import date
from sqlalchemy import or_
from backend.app.models.rule_change_log import RuleChangeLog
from backend.app.schemas.rule_change_log import RuleChangeLogOut

@router.get("", response_model=List[RoleOut])
def list_roles(
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bayiye ait tüm rolleri ve aktif kademeli prim kurallarını listeler."""
    roles = db.query(Role).filter(Role.branch_id == branch_id).order_by(Role.id.asc()).all()
    for r in roles:
        active_tiers = [t for t in r.commission_tiers if t.effective_to is None]
        active_tiers.sort(key=lambda t: t.min_amount)
        r.commission_tiers = active_tiers
    return roles

@router.get("/{role_id}/history", response_model=List[RuleChangeLogOut])
def get_role_history(
    role_id: int,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rol ve prim kademeleri değişiklik geçmişini listeler."""
    return db.query(RuleChangeLog).filter(
        RuleChangeLog.branch_id == branch_id,
        RuleChangeLog.rule_type == "ROLE_TIER",
        RuleChangeLog.entity_id == role_id
    ).order_by(RuleChangeLog.created_at.desc()).all()

@router.post("", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
def create_role(
    role_in: RoleCreate,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN")),
    db: Session = Depends(get_db)
):
    """Yeni bir personel rolü oluşturur (Franchisor Admin only)."""
    existing = db.query(Role).filter(
        Role.branch_id == branch_id,
        Role.name == role_in.name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{role_in.name}' adında bir rol zaten mevcut."
        )

    today = date.today()
    role = Role(
        branch_id=branch_id,
        name=role_in.name,
        turnover_source=role_in.turnover_source,
        is_active=role_in.is_active
    )
    db.add(role)
    db.flush()

    if role_in.tiers:
        for t in role_in.tiers:
            tier = RoleCommissionTier(
                role_id=role.id,
                min_amount=t.min_amount,
                max_amount=t.max_amount,
                rate=t.rate,
                effective_from=today,
                effective_to=None,
                created_by_user_id=current_user.id
            )
            db.add(tier)

    log = RuleChangeLog(
        branch_id=branch_id,
        user_id=current_user.id,
        rule_type="ROLE_TIER",
        entity_id=role.id,
        action="CREATE",
        effective_from=today,
        description=f"Yeni rol oluşturuldu: {role.name} ({role.turnover_source})",
        old_values=None,
        new_values={"name": role.name, "turnover_source": role.turnover_source}
    )
    db.add(log)
    db.commit()
    db.refresh(role)

    active_tiers = [t for t in role.commission_tiers if t.effective_to is None]
    active_tiers.sort(key=lambda t: t.min_amount)
    role.commission_tiers = active_tiers
    return role

@router.get("/{role_id}", response_model=RoleOut)
def get_role(
    role_id: int,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    role = db.query(Role).filter(Role.branch_id == branch_id, Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol bulunamadı.")
    active_tiers = [t for t in role.commission_tiers if t.effective_to is None]
    active_tiers.sort(key=lambda t: t.min_amount)
    role.commission_tiers = active_tiers
    return role

@router.put("/{role_id}", response_model=RoleOut)
def update_role(
    role_id: int,
    role_in: RoleUpdate,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN")),
    db: Session = Depends(get_db)
):
    role = db.query(Role).filter(Role.branch_id == branch_id, Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol bulunamadı.")

    today = date.today()
    old_values = {"name": role.name, "turnover_source": role.turnover_source, "is_active": role.is_active}

    if role_in.name is not None:
        role.name = role_in.name
    if role_in.turnover_source is not None:
        role.turnover_source = role_in.turnover_source
    if role_in.is_active is not None:
        role.is_active = role_in.is_active

    if role_in.tiers is not None:
        # Versioning: archive old active tiers with effective_to = today
        active_tiers = db.query(RoleCommissionTier).filter(
            RoleCommissionTier.role_id == role.id,
            RoleCommissionTier.effective_to == None
        ).all()
        for ot in active_tiers:
            ot.effective_to = today

        # Add new versions
        for t in role_in.tiers:
            tier = RoleCommissionTier(
                role_id=role.id,
                min_amount=t.min_amount,
                max_amount=t.max_amount,
                rate=t.rate,
                effective_from=today,
                effective_to=None,
                created_by_user_id=current_user.id
            )
            db.add(tier)

    log = RuleChangeLog(
        branch_id=branch_id,
        user_id=current_user.id,
        rule_type="ROLE_TIER",
        entity_id=role.id,
        action="UPDATE",
        effective_from=today,
        description=f"Rol güncellendi: {role.name}",
        old_values=old_values,
        new_values={"name": role.name, "turnover_source": role.turnover_source, "is_active": role.is_active}
    )
    db.add(log)
    db.commit()
    db.refresh(role)
    active_tiers = [t for t in role.commission_tiers if t.effective_to is None]
    active_tiers.sort(key=lambda t: t.min_amount)
    role.commission_tiers = active_tiers
    return role

@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: int,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN")),
    db: Session = Depends(get_db)
):
    role = db.query(Role).filter(Role.branch_id == branch_id, Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol bulunamadı.")
    
    if role.employees:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bu role bağlı {len(role.employees)} adet personel var. Önce personellerin rolünü değiştirin."
        )

    today = date.today()
    log = RuleChangeLog(
        branch_id=branch_id,
        user_id=current_user.id,
        rule_type="ROLE_TIER",
        entity_id=role.id,
        action="DELETE",
        effective_from=today,
        description=f"Rol silindi: {role.name}",
        old_values={"name": role.name},
        new_values=None
    )
    db.add(log)
    db.delete(role)
    db.commit()
    return None

@router.post("/{role_id}/tiers", response_model=RoleCommissionTierOut, status_code=status.HTTP_201_CREATED)
def add_tier_to_role(
    role_id: int,
    tier_in: RoleCommissionTierCreate,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN")),
    db: Session = Depends(get_db)
):
    role = db.query(Role).filter(Role.branch_id == branch_id, Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol bulunamadı.")

    today = date.today()
    tier = RoleCommissionTier(
        role_id=role.id,
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
        rule_type="ROLE_TIER",
        entity_id=role.id,
        action="ADD_TIER",
        effective_from=today,
        description=f"Role kademe eklendi: {role.name} ({tier.min_amount}-{tier.max_amount or 'Sonsuz'}, %{tier.rate*100:.1f})",
        old_values=None,
        new_values={"rate": str(tier.rate), "min_amount": str(tier.min_amount), "max_amount": str(tier.max_amount) if tier.max_amount else None}
    )
    db.add(log)
    db.commit()
    db.refresh(tier)
    return tier

@router.delete("/{role_id}/tiers/{tier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role_tier(
    role_id: int,
    tier_id: int,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN")),
    db: Session = Depends(get_db)
):
    role = db.query(Role).filter(Role.branch_id == branch_id, Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol bulunamadı.")

    tier = db.query(RoleCommissionTier).filter(
        RoleCommissionTier.id == tier_id,
        RoleCommissionTier.role_id == role_id,
        RoleCommissionTier.effective_to == None
    ).first()
    if not tier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aktif kademe bulunamadı.")

    today = date.today()
    tier.effective_to = today

    log = RuleChangeLog(
        branch_id=branch_id,
        user_id=current_user.id,
        rule_type="ROLE_TIER",
        entity_id=role.id,
        action="DELETE_TIER",
        effective_from=today,
        description=f"Rol kademesi sonlandırıldı: {role.name} ({tier.min_amount}-{tier.max_amount or 'Sonsuz'})",
        old_values={"rate": str(tier.rate), "min_amount": str(tier.min_amount)},
        new_values=None
    )
    db.add(log)
    db.commit()
    return None
