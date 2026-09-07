from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_roles
from backend.app.models.user import User
from backend.app.models.branch import Branch
from backend.app.schemas.branch import BranchCreate, BranchUpdate, BranchOut

router = APIRouter(prefix="/branches", tags=["Bayi Yönetimi (Multi-Tenant)"])

@router.get("", response_model=List[BranchOut])
def list_branches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Franchisor Admin: Franchisor bünyesindeki tüm bayileri listeler.
    Bayi Admin & Viewer: Sadece bağlı olduğu bayiyi listeler.
    """
    if current_user.role == "FRANCHISOR_ADMIN":
        query = db.query(Branch)
        if current_user.franchisor_id:
            query = query.filter(Branch.franchisor_id == current_user.franchisor_id)
        return query.order_by(Branch.id.asc()).all()
    else:
        if not current_user.branch_id:
            return []
        return db.query(Branch).filter(Branch.id == current_user.branch_id).all()

@router.post("", response_model=BranchOut, status_code=status.HTTP_201_CREATED)
def create_branch(
    branch_in: BranchCreate,
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN")),
    db: Session = Depends(get_db)
):
    """Yeni bir bayi oluşturur (Franchisor Admin only)."""
    branch = Branch(
        franchisor_id=current_user.franchisor_id,
        name=branch_in.name.strip(),
        tax_id=branch_in.tax_id,
        tax_office=branch_in.tax_office,
        address=branch_in.address,
        phone=branch_in.phone,
        email=branch_in.email,
        is_active=branch_in.is_active
    )
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return branch

@router.get("/{branch_id}", response_model=BranchOut)
def get_branch(
    branch_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bayi detayını görüntüler."""
    if current_user.role != "FRANCHISOR_ADMIN" and current_user.branch_id != branch_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Farklı bir bayinin detayına erişim yetkiniz yoktur."
        )

    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bayi bulunamadı.")
    return branch

@router.put("/{branch_id}", response_model=BranchOut)
def update_branch(
    branch_id: int,
    branch_in: BranchUpdate,
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN")),
    db: Session = Depends(get_db)
):
    """Bayi bilgilerini günceller (Franchisor Admin only)."""
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bayi bulunamadı.")

    if branch_in.name is not None:
        branch.name = branch_in.name.strip()
    if branch_in.tax_id is not None:
        branch.tax_id = branch_in.tax_id
    if branch_in.tax_office is not None:
        branch.tax_office = branch_in.tax_office
    if branch_in.address is not None:
        branch.address = branch_in.address
    if branch_in.phone is not None:
        branch.phone = branch_in.phone
    if branch_in.email is not None:
        branch.email = branch_in.email
    if branch_in.is_active is not None:
        branch.is_active = branch_in.is_active

    db.commit()
    db.refresh(branch)
    return branch
