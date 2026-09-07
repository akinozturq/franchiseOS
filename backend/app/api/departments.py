from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_roles, get_active_branch_id
from backend.app.models.user import User
from backend.app.models.department import Department
from backend.app.models.transaction import Transaction
from backend.app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentOut

router = APIRouter(prefix="/departments", tags=["Departmanlar"])

@router.get("", response_model=List[DepartmentOut])
def list_departments(
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(Department).filter(
        Department.branch_id == branch_id,
        Department.is_active == True
    ).order_by(Department.id).all()

@router.post("", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
def create_department(
    dept_in: DepartmentCreate,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN", "BAYI_ADMIN")),
    db: Session = Depends(get_db)
):
    existing = db.query(Department).filter(
        Department.branch_id == branch_id,
        Department.name == dept_in.name.strip()
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bu isimde bir departman zaten mevcut.")
        
    dept = Department(
        branch_id=branch_id,
        name=dept_in.name.strip(),
        is_active=dept_in.is_active
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept

@router.put("/{dept_id}", response_model=DepartmentOut)
def update_department(
    dept_id: int,
    dept_in: DepartmentUpdate,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN", "BAYI_ADMIN")),
    db: Session = Depends(get_db)
):
    dept = db.query(Department).filter(
        Department.id == dept_id,
        Department.branch_id == branch_id
    ).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Departman bulunamadı.")
        
    if dept_in.name is not None:
        dept.name = dept_in.name.strip()
    if dept_in.is_active is not None:
        dept.is_active = dept_in.is_active
        
    db.commit()
    db.refresh(dept)
    return dept

@router.delete("/{dept_id}")
def delete_department(
    dept_id: int,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN", "BAYI_ADMIN")),
    db: Session = Depends(get_db)
):
    dept = db.query(Department).filter(
        Department.id == dept_id,
        Department.branch_id == branch_id
    ).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Departman bulunamadı.")
        
    tx_count = db.query(Transaction).filter(Transaction.department_id == dept_id).count()
    if tx_count > 0:
        dept.is_active = False
        db.commit()
        return {"detail": f"Departmana bağlı {tx_count} işlem olduğundan pasife alındı."}
    
    db.delete(dept)
    db.commit()
    return {"detail": "Departman başarıyla silindi."}
