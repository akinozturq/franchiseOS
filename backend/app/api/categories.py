from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_roles, get_active_branch_id
from backend.app.models.user import User
from backend.app.models.transaction_category import TransactionCategory
from backend.app.models.transaction import Transaction
from backend.app.schemas.category import (
    TransactionCategoryCreate,
    TransactionCategoryUpdate,
    TransactionCategoryOut
)

router = APIRouter(prefix="/categories", tags=["İşlem Kategorileri ve İstisnalar"])

from datetime import date
from sqlalchemy import or_
from backend.app.models.rule_change_log import RuleChangeLog
from backend.app.schemas.rule_change_log import RuleChangeLogOut

@router.get("", response_model=List[TransactionCategoryOut])
def list_categories(
    target_date: date = None,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bayiye ait işlem kategorilerini ve aktif komisyon/prim istisna oranlarını listeler."""
    query = db.query(TransactionCategory).filter(TransactionCategory.branch_id == branch_id)
    if target_date:
        query = query.filter(
            TransactionCategory.effective_from <= target_date,
            or_(TransactionCategory.effective_to == None, TransactionCategory.effective_to > target_date)
        )
    else:
        query = query.filter(TransactionCategory.effective_to == None)
    return query.order_by(TransactionCategory.name.asc()).all()

@router.get("/history", response_model=List[RuleChangeLogOut])
def get_category_history(
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Kategori istisna oranları değişiklik geçmişini listeler."""
    return db.query(RuleChangeLog).filter(
        RuleChangeLog.branch_id == branch_id,
        RuleChangeLog.rule_type == "CATEGORY_OVERRIDE"
    ).order_by(RuleChangeLog.created_at.desc()).all()

@router.get("/all-rule-history", response_model=List[RuleChangeLogOut])
def get_all_rule_history(
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bayiye ait tüm kuralların (komisyon dilimleri, rol primleri, kategoriler) birleşik değişiklik geçmişini listeler."""
    return db.query(RuleChangeLog).filter(
        RuleChangeLog.branch_id == branch_id
    ).order_by(RuleChangeLog.created_at.desc()).all()

@router.post("", response_model=TransactionCategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    cat_in: TransactionCategoryCreate,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN")),
    db: Session = Depends(get_db)
):
    """Yeni bir işlem kategorisi oluşturur (Franchisor Admin only)."""
    existing = db.query(TransactionCategory).filter(
        TransactionCategory.branch_id == branch_id,
        TransactionCategory.effective_to == None,
        func.lower(TransactionCategory.name) == cat_in.name.strip().lower()
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{cat_in.name}' adında aktif bir kategori zaten mevcut."
        )

    today = date.today()
    cat = TransactionCategory(
        branch_id=branch_id,
        name=cat_in.name.strip(),
        general_override_rate=cat_in.general_override_rate,
        bonus_override_rate=cat_in.bonus_override_rate,
        is_active=cat_in.is_active,
        effective_from=today,
        effective_to=None,
        created_by_user_id=current_user.id
    )
    db.add(cat)
    db.flush()

    log = RuleChangeLog(
        branch_id=branch_id,
        user_id=current_user.id,
        rule_type="CATEGORY_OVERRIDE",
        entity_id=cat.id,
        action="CREATE",
        effective_from=today,
        description=f"Yeni kategori oluşturuldu: {cat.name} (Genel İstisna: %{(cat.general_override_rate or 0)*100:.1f}, Prim İstisna: %{(cat.bonus_override_rate or 0)*100:.1f})",
        old_values=None,
        new_values={
            "name": cat.name,
            "general_override_rate": str(cat.general_override_rate) if cat.general_override_rate is not None else None,
            "bonus_override_rate": str(cat.bonus_override_rate) if cat.bonus_override_rate is not None else None
        }
    )
    db.add(log)
    db.commit()
    db.refresh(cat)
    return cat

@router.get("/{category_id}", response_model=TransactionCategoryOut)
def get_category(
    category_id: int,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cat = db.query(TransactionCategory).filter(
        TransactionCategory.branch_id == branch_id,
        TransactionCategory.id == category_id
    ).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kategori bulunamadı.")
    return cat

@router.put("/{category_id}", response_model=TransactionCategoryOut)
def update_category(
    category_id: int,
    cat_in: TransactionCategoryUpdate,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN")),
    db: Session = Depends(get_db)
):
    cat = db.query(TransactionCategory).filter(
        TransactionCategory.branch_id == branch_id,
        TransactionCategory.id == category_id
    ).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kategori bulunamadı.")

    # If an older version ID was supplied, resolve to the currently active version of this category
    if cat.effective_to is not None:
        active_ver = db.query(TransactionCategory).filter(
            TransactionCategory.branch_id == branch_id,
            TransactionCategory.name == cat.name,
            TransactionCategory.effective_to == None
        ).first()
        if active_ver:
            cat = active_ver

    old_cat = cat
    today = date.today()
    old_values = {
        "name": old_cat.name,
        "general_override_rate": str(old_cat.general_override_rate) if old_cat.general_override_rate is not None else None,
        "bonus_override_rate": str(old_cat.bonus_override_rate) if old_cat.bonus_override_rate is not None else None,
        "is_active": old_cat.is_active
    }

    new_name = cat_in.name.strip() if cat_in.name is not None else old_cat.name
    new_general = cat_in.general_override_rate if "general_override_rate" in cat_in.model_fields_set else old_cat.general_override_rate
    new_bonus = cat_in.bonus_override_rate if "bonus_override_rate" in cat_in.model_fields_set else old_cat.bonus_override_rate
    new_active = cat_in.is_active if cat_in.is_active is not None else old_cat.is_active

    # Check if override rates actually changed
    rates_changed = (new_general != old_cat.general_override_rate) or (new_bonus != old_cat.bonus_override_rate)

    if rates_changed:
        # Versioning: close old row and insert new row
        old_cat.effective_to = today

        new_cat = TransactionCategory(
            branch_id=branch_id,
            name=new_name,
            general_override_rate=new_general,
            bonus_override_rate=new_bonus,
            is_active=new_active,
            effective_from=today,
            effective_to=None,
            created_by_user_id=current_user.id
        )
        db.add(new_cat)
        db.flush()
        target_cat = new_cat
    else:
        old_cat.name = new_name
        old_cat.is_active = new_active
        target_cat = old_cat

    log = RuleChangeLog(
        branch_id=branch_id,
        user_id=current_user.id,
        rule_type="CATEGORY_OVERRIDE",
        entity_id=target_cat.id,
        action="UPDATE",
        effective_from=today,
        description=f"Kategori istisnaları güncellendi: {new_name}",
        old_values=old_values,
        new_values={
            "name": new_name,
            "general_override_rate": str(new_general) if new_general is not None else None,
            "bonus_override_rate": str(new_bonus) if new_bonus is not None else None,
            "is_active": new_active
        }
    )
    db.add(log)
    db.commit()
    db.refresh(target_cat)
    return target_cat

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN")),
    db: Session = Depends(get_db)
):
    cat = db.query(TransactionCategory).filter(
        TransactionCategory.branch_id == branch_id,
        TransactionCategory.id == category_id
    ).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kategori bulunamadı.")

    # Resolve to active version if old ID passed
    if cat.effective_to is not None:
        active_ver = db.query(TransactionCategory).filter(
            TransactionCategory.branch_id == branch_id,
            TransactionCategory.name == cat.name,
            TransactionCategory.effective_to == None
        ).first()
        if active_ver:
            cat = active_ver
        else:
            return None

    # If no transactions attached to any version of this category name, delete cleanly
    all_vers = db.query(TransactionCategory).filter(
        TransactionCategory.branch_id == branch_id,
        TransactionCategory.name == cat.name
    ).all()
    has_tx = any(db.query(Transaction).filter(Transaction.category_id == v.id).count() > 0 for v in all_vers)
    if not has_tx:
        for v in all_vers:
            db.delete(v)
        db.commit()
        return None

    today = date.today()
    cat.effective_to = today
    cat.is_active = False

    log = RuleChangeLog(
        branch_id=branch_id,
        user_id=current_user.id,
        rule_type="CATEGORY_OVERRIDE",
        entity_id=cat.id,
        action="DELETE",
        effective_from=today,
        description=f"Kategori kapatıldı (arşivlendi): {cat.name}",
        old_values={"name": cat.name},
        new_values=None
    )
    db.add(log)
    db.commit()
    return None
