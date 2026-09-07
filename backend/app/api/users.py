from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import (
    get_current_user,
    require_roles,
    get_password_hash
)
from backend.app.models.user import User
from backend.app.models.branch import Branch
from backend.app.schemas.user import UserCreate, UserUpdate, UserOut

router = APIRouter(prefix="/users", tags=["Kullanıcı Yönetimi (RBAC)"])

VALID_ROLES = ["FRANCHISOR_ADMIN", "BAYI_ADMIN", "VIEWER"]

@router.get("", response_model=List[UserOut])
def list_users(
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN")),
    db: Session = Depends(get_db)
):
    """Sistemdeki tüm kullanıcıları listeler (Franchisor Admin only)."""
    query = db.query(User)
    if current_user.franchisor_id:
        query = query.filter(User.franchisor_id == current_user.franchisor_id)
    return query.order_by(User.id.asc()).all()

@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN")),
    db: Session = Depends(get_db)
):
    """Yeni kullanıcı oluşturur (Franchisor Admin only)."""
    if user_in.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Geçersiz rol. Geçerli roller: {', '.join(VALID_ROLES)}"
        )

    # Check username uniqueness
    existing = db.query(User).filter(User.username == user_in.username.strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{user_in.username}' kullanıcı adı zaten kullanımda."
        )

    # Check branch if BAYI_ADMIN or assigned
    if user_in.branch_id:
        branch = db.query(Branch).filter(Branch.id == user_in.branch_id).first()
        if not branch:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Belirtilen bayi bulunamadı."
            )

    new_user = User(
        username=user_in.username.strip(),
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name.strip() if user_in.full_name else None,
        role=user_in.role,
        franchisor_id=current_user.franchisor_id,
        branch_id=user_in.branch_id,
        is_active=user_in.is_active
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN")),
    db: Session = Depends(get_db)
):
    """Kullanıcı bilgilerini günceller (Franchisor Admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı.")

    if user_in.role is not None:
        if user_in.role not in VALID_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Geçersiz rol. Geçerli roller: {', '.join(VALID_ROLES)}"
            )
        user.role = user_in.role

    if user_in.branch_id is not None:
        branch = db.query(Branch).filter(Branch.id == user_in.branch_id).first()
        if not branch:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Belirtilen bayi bulunamadı.")
        user.branch_id = user_in.branch_id

    if user_in.full_name is not None:
        user.full_name = user_in.full_name.strip()

    if user_in.password:
        user.hashed_password = get_password_hash(user_in.password)

    if user_in.is_active is not None:
        # Don't allow user to deactivate themselves
        if user.id == current_user.id and not user_in.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kendi hesabınızı pasife alamazsınız.")
        user.is_active = user_in.is_active

    db.commit()
    db.refresh(user)
    return user

@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN")),
    db: Session = Depends(get_db)
):
    """Kullanıcıyı pasife alır (Franchisor Admin only)."""
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kendi hesabınızı silemezsiniz.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı.")

    user.is_active = False
    db.commit()
    return {"detail": "Kullanıcı başarıyla pasife alındı."}
