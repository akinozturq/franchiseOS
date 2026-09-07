from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import extract, or_

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_roles, get_active_branch_id
from datetime import date
from backend.app.models.period_closure import PeriodClosure
from backend.app.models.user import User
from backend.app.models.department import Department
from backend.app.models.transaction import Transaction
from backend.app.models.employee import Employee
from backend.app.models.transaction_category import TransactionCategory
from backend.app.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionOut
)
from backend.app.schemas.import_schema import (
    UploadPreviewResponse,
    ImportExecuteRequest,
    ImportResultResponse
)
from backend.app.services.import_service import process_upload_preview, execute_import

router = APIRouter(prefix="/transactions", tags=["İşlem Kayıtları"])

@router.get("", response_model=List[TransactionOut])
def list_transactions(
    year: Optional[int] = Query(None, description="Yıl filtresi"),
    month: Optional[int] = Query(None, description="Ay filtresi (1-12)"),
    department_id: Optional[int] = Query(None, description="Departman ID"),
    employee_id: Optional[int] = Query(None, description="Personel ID"),
    category_id: Optional[int] = Query(None, description="Kategori ID"),
    search: Optional[str] = Query(None, description="Müşteri, personel veya işlem adı ara"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Transaction).filter(Transaction.branch_id == branch_id)

    if year:
        query = query.filter(extract("year", Transaction.date) == year)
    if month:
        query = query.filter(extract("month", Transaction.date) == month)
    if department_id:
        query = query.filter(Transaction.department_id == department_id)
    if employee_id:
        query = query.filter(Transaction.employee_id == employee_id)
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Transaction.customer_name.ilike(s),
                Transaction.item_name.ilike(s),
                Transaction.staff_name.ilike(s),
                Transaction.customer_tax_id.ilike(s)
            )
        )

    transactions = query.order_by(Transaction.date.desc(), Transaction.id.desc()).offset(skip).limit(limit).all()
    
    dept_map = {d.id: d.name for d in db.query(Department).filter(Department.branch_id == branch_id).all()}
    results = []
    for tx in transactions:
        tx_out = TransactionOut.model_validate(tx)
        tx_out.department_name = dept_map.get(tx.department_id, "Genel")
        tx_out.employee_name = tx.employee.full_name if tx.employee else tx.staff_name
        tx_out.category_name = tx.category.name if tx.category else tx.item_name
        results.append(tx_out)
    return results

def assert_period_is_open(db: Session, branch_id: int, tx_date: date):
    closed = db.query(PeriodClosure).filter(
        PeriodClosure.branch_id == branch_id,
        PeriodClosure.year == tx_date.year,
        PeriodClosure.month == tx_date.month,
        PeriodClosure.status == "CLOSED",
        PeriodClosure.reopened_at.is_(None)
    ).first()
    if closed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{tx_date.year}-{tx_date.month:02d} dönemi kapatılmıştır (Kayıt No: #{closed.id}). Kapalı dönemlere ait işlemler eklenemez, güncellenemez veya silinemez."
        )

@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    tx_in: TransactionCreate,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN", "BAYI_ADMIN")),
    db: Session = Depends(get_db)
):
    assert_period_is_open(db, branch_id, tx_in.date)

    dept = db.query(Department).filter(
        Department.id == tx_in.department_id,
        Department.branch_id == branch_id
    ).first()
    if not dept:
        raise HTTPException(status_code=400, detail="Geçersiz departman ID.")

    emp_id = tx_in.employee_id
    staff_name = tx_in.staff_name.strip() if tx_in.staff_name else None
    if emp_id:
        emp = db.query(Employee).filter(Employee.branch_id == branch_id, Employee.id == emp_id).first()
        if emp:
            staff_name = emp.full_name
    elif staff_name:
        emp = db.query(Employee).filter(Employee.branch_id == branch_id, Employee.full_name.ilike(staff_name)).first()
        if emp:
            emp_id = emp.id

    cat_id = tx_in.category_id
    item_name = tx_in.item_name.strip()
    if cat_id:
        cat = db.query(TransactionCategory).filter(TransactionCategory.branch_id == branch_id, TransactionCategory.id == cat_id).first()
        if cat:
            item_name = cat.name
    elif item_name:
        cat = db.query(TransactionCategory).filter(TransactionCategory.branch_id == branch_id, TransactionCategory.name.ilike(item_name)).first()
        if cat:
            cat_id = cat.id

    tx = Transaction(
        branch_id=branch_id,
        department_id=tx_in.department_id,
        date=tx_in.date,
        customer_name=tx_in.customer_name.strip(),
        customer_tax_id=tx_in.customer_tax_id.strip() if tx_in.customer_tax_id else None,
        item_name=item_name,
        staff_name=staff_name,
        employee_id=emp_id,
        category_id=cat_id,
        amount_excl_vat=tx_in.amount_excl_vat,
        vat_rate=tx_in.vat_rate,
        amount_incl_vat=tx_in.amount_incl_vat,
        payment_method=tx_in.payment_method,
        invoice_status=tx_in.invoice_status,
        description=tx_in.description
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    
    out = TransactionOut.model_validate(tx)
    out.department_name = dept.name
    out.employee_name = tx.employee.full_name if tx.employee else tx.staff_name
    out.category_name = tx.category.name if tx.category else tx.item_name
    return out

@router.get("/{tx_id}", response_model=TransactionOut)
def get_transaction(
    tx_id: int,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tx = db.query(Transaction).filter(
        Transaction.id == tx_id,
        Transaction.branch_id == branch_id
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="İşlem kaydı bulunamadı.")
        
    dept = db.query(Department).filter(Department.id == tx.department_id).first()
    out = TransactionOut.model_validate(tx)
    out.department_name = dept.name if dept else "Genel"
    out.employee_name = tx.employee.full_name if tx.employee else tx.staff_name
    out.category_name = tx.category.name if tx.category else tx.item_name
    return out

@router.get("/{tx_id}/sensitive")
def get_transaction_sensitive_data(
    tx_id: int,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN", "BAYI_ADMIN")),
    db: Session = Depends(get_db)
):
    """
    KVKK Veri Minimizasyonu:
    Açık TCKN / VKN yalnızca yetkili yöneticiler (FRANCHISOR_ADMIN, BAYI_ADMIN)
    tarafından özel yetkiyle sorgulanabilir.
    """
    tx = db.query(Transaction).filter(
        Transaction.id == tx_id,
        Transaction.branch_id == branch_id
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="İşlem kaydı bulunamadı.")
    return {
        "id": tx.id,
        "customer_name": tx.customer_name,
        "customer_tax_id": tx.customer_tax_id,
        "customer_tax_id_masked": tx.customer_tax_id_masked
    }

@router.put("/{tx_id}", response_model=TransactionOut)
def update_transaction(
    tx_id: int,
    tx_in: TransactionUpdate,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN", "BAYI_ADMIN")),
    db: Session = Depends(get_db)
):
    tx = db.query(Transaction).filter(
        Transaction.id == tx_id,
        Transaction.branch_id == branch_id
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="İşlem kaydı bulunamadı.")

    assert_period_is_open(db, branch_id, tx.date)
    if tx_in.date is not None and (tx_in.date.year != tx.date.year or tx_in.date.month != tx.date.month):
        assert_period_is_open(db, branch_id, tx_in.date)

    if tx_in.department_id is not None:
        dept = db.query(Department).filter(
            Department.id == tx_in.department_id,
            Department.branch_id == branch_id
        ).first()
        if not dept:
            raise HTTPException(status_code=400, detail="Geçersiz departman ID.")
        tx.department_id = tx_in.department_id

    if tx_in.date is not None:
        tx.date = tx_in.date
    if tx_in.customer_name is not None:
        tx.customer_name = tx_in.customer_name.strip()
    if tx_in.customer_tax_id is not None:
        tx.customer_tax_id = tx_in.customer_tax_id.strip() if tx_in.customer_tax_id else None
    if tx_in.item_name is not None:
        tx.item_name = tx_in.item_name.strip()
    if tx_in.category_id is not None:
        tx.category_id = tx_in.category_id
        cat = db.query(TransactionCategory).filter(TransactionCategory.branch_id == branch_id, TransactionCategory.id == tx_in.category_id).first()
        if cat:
            tx.item_name = cat.name

    if tx_in.staff_name is not None:
        tx.staff_name = tx_in.staff_name.strip() if tx_in.staff_name else None
    if tx_in.employee_id is not None:
        tx.employee_id = tx_in.employee_id
        emp = db.query(Employee).filter(Employee.branch_id == branch_id, Employee.id == tx_in.employee_id).first()
        if emp:
            tx.staff_name = emp.full_name

    if tx_in.amount_excl_vat is not None:
        tx.amount_excl_vat = tx_in.amount_excl_vat
    if tx_in.vat_rate is not None:
        tx.vat_rate = tx_in.vat_rate
    if tx_in.amount_incl_vat is not None:
        tx.amount_incl_vat = tx_in.amount_incl_vat
    if tx_in.payment_method is not None:
        tx.payment_method = tx_in.payment_method
    if tx_in.invoice_status is not None:
        tx.invoice_status = tx_in.invoice_status
    if tx_in.description is not None:
        tx.description = tx_in.description

    db.commit()
    db.refresh(tx)
    
    dept = db.query(Department).filter(Department.id == tx.department_id).first()
    out = TransactionOut.model_validate(tx)
    out.department_name = dept.name if dept else "Genel"
    out.employee_name = tx.employee.full_name if tx.employee else tx.staff_name
    out.category_name = tx.category.name if tx.category else tx.item_name
    return out

@router.delete("/{tx_id}")
def delete_transaction(
    tx_id: int,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN", "BAYI_ADMIN")),
    db: Session = Depends(get_db)
):
    tx = db.query(Transaction).filter(
        Transaction.id == tx_id,
        Transaction.branch_id == branch_id
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="İşlem kaydı bulunamadı.")
        
    assert_period_is_open(db, branch_id, tx.date)

    db.delete(tx)
    db.commit()
    return {"detail": "İşlem kaydı başarıyla silindi."}

@router.post("/upload-preview", response_model=UploadPreviewResponse)
async def upload_file_preview(
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN", "BAYI_ADMIN"))
):
    """
    Kullanıcının yüklediği CSV veya XLSX dosyasını okur,
    kolon eşleştirme önerisi ve ilk 5 satır önizlemesi döndürür.
    """
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Boş dosya yüklendi.")
    try:
        preview = process_upload_preview(file.filename, contents)
        return preview
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Dosya okunamadı: {str(e)}")

@router.post("/import", response_model=ImportResultResponse)
def execute_file_import(
    req: ImportExecuteRequest,
    branch_id: int = Depends(get_active_branch_id),
    current_user: User = Depends(require_roles("FRANCHISOR_ADMIN", "BAYI_ADMIN")),
    db: Session = Depends(get_db)
):
    """
    Kullanıcının onayladığı sütun eşleştirmesi ile toplu içe aktarımı gerçekleştirir.
    Hatalı satırlar ayrı raporlanır, geçerli satırlar başarıyla kaydedilir.
    """
    try:
        result = execute_import(
            file_id=req.file_id,
            column_mapping=req.column_mapping,
            default_department_id=req.default_department_id,
            branch_id=branch_id,
            db=db
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"İçe aktarma sırasında hata oluştu: {str(ex)}")
