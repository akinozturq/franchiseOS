from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_roles, get_active_branch_id
from backend.app.models.user import User
from backend.app.models.employee import Employee
from backend.app.models.role import Role
from backend.app.models.department import Department
from backend.app.models.transaction import Transaction
from backend.app.schemas.employee import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeOut
)
from backend.app.schemas.transaction import TransactionOut

router = APIRouter(prefix="/employees", tags=["Personel Yönetimi"])

class AssignEmployeePayload(BaseModel):
    transaction_ids: List[int]
    employee_id: int

@router.get("", response_model=List[EmployeeOut])
def list_employees(
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bayiye ait tüm personelleri rol ve departman bilgileriyle listeler."""
    employees = db.query(Employee).filter(Employee.branch_id == branch_id).order_by(Employee.id.asc()).all()
    
    result = []
    for emp in employees:
        out = EmployeeOut(
            id=emp.id,
            branch_id=emp.branch_id,
            role_id=emp.role_id,
            department_id=emp.department_id,
            full_name=emp.full_name,
            is_active=emp.is_active,
            role_name=emp.role.name if emp.role else None,
            department_name=emp.department.name if emp.department else None,
            role=emp.role,
            created_at=emp.created_at,
            updated_at=emp.updated_at
        )
        result.append(out)
    return result

@router.post("", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(
    emp_in: EmployeeCreate,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN", "BAYI_ADMIN")),
    db: Session = Depends(get_db)
):
    """Yeni bir personel kaydı oluşturur."""
    role = db.query(Role).filter(Role.branch_id == branch_id, Role.id == emp_in.role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Geçersiz rol.")

    if emp_in.department_id:
        dept = db.query(Department).filter(Department.branch_id == branch_id, Department.id == emp_in.department_id).first()
        if not dept:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Geçersiz departman.")

    emp = Employee(
        branch_id=branch_id,
        role_id=emp_in.role_id,
        department_id=emp_in.department_id,
        full_name=emp_in.full_name.strip(),
        is_active=emp_in.is_active
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)

    return EmployeeOut(
        id=emp.id,
        branch_id=emp.branch_id,
        role_id=emp.role_id,
        department_id=emp.department_id,
        full_name=emp.full_name,
        is_active=emp.is_active,
        role_name=emp.role.name if emp.role else None,
        department_name=emp.department.name if emp.department else None,
        role=emp.role,
        created_at=emp.created_at,
        updated_at=emp.updated_at
    )

@router.get("/unassigned-transactions", response_model=List[TransactionOut])
def get_unassigned_transactions(
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Personel eşleşmesi yapılmamış (employee_id boş olan) işlem kayıtlarını listeler."""
    txs = db.query(Transaction).filter(
        Transaction.branch_id == branch_id,
        Transaction.employee_id.is_(None)
    ).order_by(Transaction.date.desc()).all()
    
    dept_map = {d.id: d.name for d in db.query(Department).filter(Department.branch_id == branch_id).all()}
    
    return [
        TransactionOut(
            id=t.id,
            branch_id=t.branch_id,
            department_id=t.department_id,
            department_name=dept_map.get(t.department_id, "Genel"),
            employee_id=t.employee_id,
            employee_name=None,
            category_id=t.category_id,
            category_name=t.category.name if t.category else None,
            date=t.date,
            customer_name=t.customer_name,
            customer_tax_id=t.customer_tax_id,
            item_name=t.item_name,
            staff_name=t.staff_name,
            amount_excl_vat=t.amount_excl_vat,
            vat_rate=t.vat_rate,
            amount_incl_vat=t.amount_incl_vat,
            payment_method=t.payment_method,
            invoice_status=t.invoice_status,
            description=t.description,
            created_at=t.created_at,
            updated_at=t.updated_at
        )
        for t in txs
    ]

@router.post("/assign-transactions")
def assign_transactions_to_employee(
    payload: AssignEmployeePayload,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN", "BAYI_ADMIN")),
    db: Session = Depends(get_db)
):
    """Seçilen işlemleri belirtilen personele bağlar."""
    emp = db.query(Employee).filter(Employee.branch_id == branch_id, Employee.id == payload.employee_id).first()
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personel bulunamadı.")

    txs = db.query(Transaction).filter(
        Transaction.branch_id == branch_id,
        Transaction.id.in_(payload.transaction_ids)
    ).all()

    for tx in txs:
        tx.employee_id = emp.id
        tx.staff_name = emp.full_name

    db.commit()
    return {"status": "success", "updated_count": len(txs)}

@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(
    employee_id: int,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    emp = db.query(Employee).filter(Employee.branch_id == branch_id, Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personel bulunamadı.")
    return EmployeeOut(
        id=emp.id,
        branch_id=emp.branch_id,
        role_id=emp.role_id,
        department_id=emp.department_id,
        full_name=emp.full_name,
        is_active=emp.is_active,
        role_name=emp.role.name if emp.role else None,
        department_name=emp.department.name if emp.department else None,
        role=emp.role,
        created_at=emp.created_at,
        updated_at=emp.updated_at
    )

@router.put("/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: int,
    emp_in: EmployeeUpdate,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN", "BAYI_ADMIN")),
    db: Session = Depends(get_db)
):
    emp = db.query(Employee).filter(Employee.branch_id == branch_id, Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personel bulunamadı.")

    if emp_in.role_id is not None:
        role = db.query(Role).filter(Role.branch_id == branch_id, Role.id == emp_in.role_id).first()
        if not role:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Geçersiz rol.")
        emp.role_id = emp_in.role_id

    if "department_id" in emp_in.model_fields_set:
        if emp_in.department_id is not None:
            dept = db.query(Department).filter(Department.branch_id == branch_id, Department.id == emp_in.department_id).first()
            if not dept:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Geçersiz departman.")
        emp.department_id = emp_in.department_id

    if emp_in.full_name is not None:
        emp.full_name = emp_in.full_name.strip()
    if emp_in.is_active is not None:
        emp.is_active = emp_in.is_active

    db.commit()
    db.refresh(emp)

    return EmployeeOut(
        id=emp.id,
        branch_id=emp.branch_id,
        role_id=emp.role_id,
        department_id=emp.department_id,
        full_name=emp.full_name,
        is_active=emp.is_active,
        role_name=emp.role.name if emp.role else None,
        department_name=emp.department.name if emp.department else None,
        role=emp.role,
        created_at=emp.created_at,
        updated_at=emp.updated_at
    )

@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: int,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN", "BAYI_ADMIN")),
    db: Session = Depends(get_db)
):
    emp = db.query(Employee).filter(Employee.branch_id == branch_id, Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personel bulunamadı.")

    tx_count = db.query(Transaction).filter(Transaction.employee_id == emp.id).count()
    if tx_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bu personele bağlı {tx_count} adet işlem kaydı var. Silmek yerine pasife alabilirsiniz."
        )

    db.delete(emp)
    db.commit()
    return None
