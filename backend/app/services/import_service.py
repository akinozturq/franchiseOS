import csv
import io
import uuid
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Any, Optional, Tuple
import openpyxl
from sqlalchemy.orm import Session

from backend.app.models.transaction import Transaction
from backend.app.models.department import Department
from backend.app.models.period_closure import PeriodClosure
from backend.app.schemas.import_schema import (
    UploadPreviewResponse,
    ImportResultResponse,
    ImportRowError
)

# In-memory storage for uploaded files before confirmation (keyed by UUID)
# In production or multi-worker, this can be Redis or temp file storage
UPLOAD_CACHE: Dict[str, Dict[str, Any]] = {}

SYSTEM_FIELDS = {
    "date": ["tarih", "islem tarihi", "işlem tarihi", "date"],
    "customer_name": ["musteri", "müşteri", "musteri adi", "müşteri adı", "cari", "cari adı", "customer"],
    "customer_tax_id": ["tc", "tckn", "vergi no", "vkn", "kimlik no", "tc kimlik no"],
    "department_name": ["departman", "bölüm", "servis/satış", "department"],
    "item_name": ["islem", "işlem", "islem adi", "işlem adı", "kategori", "hizmet", "ürün", "item"],
    "staff_name": ["personel", "danisman", "danışman", "usta", "calisan", "çalışan", "staff"],
    "amount_excl_vat": ["kdv haric", "kdv hariç", "matrah", "net tutar", "kdv haric tutar", "amount excl vat"],
    "vat_rate": ["kdv orani", "kdv oranı", "kdv %", "vat rate"],
    "amount_incl_vat": ["kdv dahil", "kdv dahil tutar", "toplam tutar", "brüt tutar", "amount incl vat"],
    "payment_method": ["tahsilat", "tahsilat sekli", "tahsilat şekli", "odeme", "ödeme yöntemi"],
    "invoice_status": ["fatura", "fatura durumu", "faturalandı mı", "invoice status"],
    "description": ["aciklama", "açıklama", "not", "notlar", "description"]
}

def guess_column_mapping(headers: List[str]) -> Dict[str, Optional[str]]:
    mapping: Dict[str, Optional[str]] = {}
    normalized_headers = {
        h.strip().lower()
        .replace("ı", "i")
        .replace("ğ", "g")
        .replace("ü", "u")
        .replace("ş", "s")
        .replace("ö", "o")
        .replace("ç", "c"): h
        for h in headers
    }
    
    for sys_field, keywords in SYSTEM_FIELDS.items():
        matched_header = None
        for kw in keywords:
            kw_norm = kw.replace("ı", "i").replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ö", "o").replace("ç", "c")
            for norm_h, orig_h in normalized_headers.items():
                if kw_norm == norm_h or kw_norm in norm_h:
                    matched_header = orig_h
                    break
            if matched_header:
                break
        mapping[sys_field] = matched_header
        
    return mapping

def parse_turkish_decimal(val: Any) -> Optional[Decimal]:
    if val is None:
        return None
    if isinstance(val, (int, float, Decimal)):
        return Decimal(str(val))
    s = str(val).strip().replace("TL", "").replace("₺", "").strip()
    if not s:
        return None
    # If contains both '.' and ',', e.g. "1.250,50"
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        # e.g. "1250,50"
        s = s.replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None

def parse_flexible_date(val: Any) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    s = str(val).strip().split(" ")[0].split("T")[0]
    formats = ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

def load_file_content(filename: str, content: bytes) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Parses uploaded CSV or Excel bytes into (headers, rows)."""
    filename_lower = filename.lower()
    
    if filename_lower.endswith(".xlsx") or filename_lower.endswith(".xls"):
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        ws = wb.active
        all_rows = list(ws.iter_rows(values_only=True))
        if not all_rows:
            return [], []
        headers = [str(col).strip() if col is not None else f"Kolon_{idx+1}" for idx, col in enumerate(all_rows[0])]
        rows = []
        for r in all_rows[1:]:
            if all(v is None or str(v).strip() == "" for v in r):
                continue
            row_dict = {headers[i]: r[i] for i in range(min(len(headers), len(r)))}
            rows.append(row_dict)
        return headers, rows
    else:
        # CSV parsing with delimiter and encoding autodetection
        text = None
        for enc in ["utf-8-sig", "utf-8", "cp1254", "iso-8859-9", "latin1"]:
            try:
                text = content.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            text = content.decode("utf-8", errors="replace")
            
        delimiter = ";" if text.count(";") > text.count(",") else ","
        f = io.StringIO(text)
        reader = csv.DictReader(f, delimiter=delimiter)
        headers = [h.strip() for h in (reader.fieldnames or [])]
        rows = [row for row in reader if any(v.strip() for v in row.values() if v)]
        return headers, rows

def process_upload_preview(filename: str, content: bytes) -> UploadPreviewResponse:
    headers, rows = load_file_content(filename, content)
    file_id = str(uuid.uuid4())
    suggested = guess_column_mapping(headers)
    
    UPLOAD_CACHE[file_id] = {
        "filename": filename,
        "headers": headers,
        "rows": rows,
        "created_at": datetime.utcnow()
    }
    
    preview_rows = rows[:5]
    return UploadPreviewResponse(
        file_id=file_id,
        file_name=filename,
        file_headers=headers,
        suggested_mapping=suggested,
        preview_rows=preview_rows,
        total_rows=len(rows)
    )

def execute_import(
    file_id: str,
    column_mapping: Dict[str, str],
    default_department_id: Optional[int],
    branch_id: int,
    db: Session
) -> ImportResultResponse:
    if file_id not in UPLOAD_CACHE:
        raise ValueError("Yüklenen dosya oturumu bulunamadı veya süresi doldu. Lütfen dosyayı tekrar yükleyin.")
        
    cached = UPLOAD_CACHE[file_id]
    rows = cached["rows"]
    
    # Load all departments for this branch for name lookup
    all_depts = db.query(Department).filter(Department.branch_id == branch_id).all()
    dept_by_name = {d.name.strip().lower(): d.id for d in all_depts}
    
    if not all_depts:
        # Create a default department if none exists
        default_dept = Department(branch_id=branch_id, name="Genel")
        db.add(default_dept)
        db.commit()
        db.refresh(default_dept)
        all_depts.append(default_dept)
        dept_by_name["genel"] = default_dept.id
        fallback_dept_id = default_dept.id
    else:
        fallback_dept_id = default_department_id or all_depts[0].id

    closed_periods = {
        (pc.year, pc.month)
        for pc in db.query(PeriodClosure.year, PeriodClosure.month).filter(
            PeriodClosure.branch_id == branch_id,
            PeriodClosure.status == "CLOSED",
            PeriodClosure.reopened_at.is_(None)
        ).all()
    }

    successful_count = 0
    errors: List[ImportRowError] = []
    
    for idx, row in enumerate(rows, start=1):
        try:
            # 1. Date
            date_col = column_mapping.get("date")
            raw_date = row.get(date_col) if date_col else None
            parsed_date = parse_flexible_date(raw_date)
            if not parsed_date:
                errors.append(ImportRowError(
                    row_index=idx,
                    raw_data=row,
                    error_message=f"Geçersiz veya eksik tarih: '{raw_date}'"
                ))
                continue
                
            if (parsed_date.year, parsed_date.month) in closed_periods:
                errors.append(ImportRowError(
                    row_index=idx,
                    raw_data=row,
                    error_message=f"{parsed_date.year}-{parsed_date.month:02d} dönemi kapatılmıştır. Kapalı döneme ait işlem içeri aktarılamaz."
                ))
                continue
                
            # 2. Customer Name
            cust_col = column_mapping.get("customer_name")
            customer_name = str(row.get(cust_col, "")).strip() if cust_col else ""
            if not customer_name:
                errors.append(ImportRowError(
                    row_index=idx,
                    raw_data=row,
                    error_message="Müşteri adı alanı boş bırakılamaz."
                ))
                continue
                
            # 3. Item Name
            item_col = column_mapping.get("item_name")
            item_name = str(row.get(item_col, "")).strip() if item_col else "Genel Hizmet"
            if not item_name:
                item_name = "Genel Hizmet"

            # 4. Amounts
            amt_excl_col = column_mapping.get("amount_excl_vat")
            raw_excl = row.get(amt_excl_col) if amt_excl_col else None
            amount_excl_vat = parse_turkish_decimal(raw_excl)
            
            amt_incl_col = column_mapping.get("amount_incl_vat")
            raw_incl = row.get(amt_incl_col) if amt_incl_col else None
            amount_incl_vat = parse_turkish_decimal(raw_incl)
            
            vat_col = column_mapping.get("vat_rate")
            raw_vat = row.get(vat_col) if vat_col else None
            vat_rate = parse_turkish_decimal(raw_vat) or Decimal("0.20")
            if vat_rate > 1:  # if user entered 20 instead of 0.20
                vat_rate = vat_rate / Decimal("100")
                
            if amount_excl_vat is None and amount_incl_vat is not None:
                amount_excl_vat = (amount_incl_vat / (Decimal("1.00") + vat_rate)).quantize(Decimal("0.01"))
            elif amount_excl_vat is not None and amount_incl_vat is None:
                amount_incl_vat = (amount_excl_vat * (Decimal("1.00") + vat_rate)).quantize(Decimal("0.01"))
            elif amount_excl_vat is None and amount_incl_vat is None:
                errors.append(ImportRowError(
                    row_index=idx,
                    raw_data=row,
                    error_message="KDV hariç veya dahil tutar belirtilmelidir."
                ))
                continue
                
            # 5. Department resolution
            dept_col = column_mapping.get("department_name")
            raw_dept = str(row.get(dept_col, "")).strip().lower() if dept_col else ""
            department_id = dept_by_name.get(raw_dept, fallback_dept_id)
            
            # 6. Other optional fields
            tax_col = column_mapping.get("customer_tax_id")
            customer_tax_id = str(row.get(tax_col, "")).strip() if tax_col else None
            
            staff_col = column_mapping.get("staff_name")
            staff_name = str(row.get(staff_col, "")).strip() if staff_col else None
            
            pay_col = column_mapping.get("payment_method")
            payment_method = str(row.get(pay_col, "")).strip() if pay_col else "Kredi Kartı"
            
            inv_col = column_mapping.get("invoice_status")
            invoice_status = str(row.get(inv_col, "")).strip() if inv_col else "Faturalandı"
            
            desc_col = column_mapping.get("description")
            description = str(row.get(desc_col, "")).strip() if desc_col else None
            
            # Create Transaction model
            new_tx = Transaction(
                branch_id=branch_id,
                department_id=department_id,
                date=parsed_date,
                customer_name=customer_name,
                customer_tax_id=customer_tax_id,
                item_name=item_name,
                staff_name=staff_name,
                amount_excl_vat=amount_excl_vat,
                vat_rate=vat_rate,
                amount_incl_vat=amount_incl_vat,
                payment_method=payment_method,
                invoice_status=invoice_status,
                description=description
            )
            db.add(new_tx)
            successful_count += 1
            
        except Exception as ex:
            errors.append(ImportRowError(
                row_index=idx,
                raw_data=row,
                error_message=f"Satır işlenirken beklenmeyen hata: {str(ex)}"
            ))
            
    db.commit()
    # Remove from cache after import
    UPLOAD_CACHE.pop(file_id, None)
    
    return ImportResultResponse(
        total_rows=len(rows),
        successful_count=successful_count,
        failed_count=len(errors),
        errors=errors
    )
