from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime

def mask_tax_id(tax_id: Optional[str]) -> Optional[str]:
    if not tax_id:
        return tax_id
    clean_id = str(tax_id).strip()
    if len(clean_id) <= 4:
        return clean_id
    return "*" * (len(clean_id) - 4) + clean_id[-4:]

class TransactionBase(BaseModel):
    date: date
    department_id: int
    customer_name: str
    customer_tax_id: Optional[str] = None
    item_name: str
    staff_name: Optional[str] = None
    employee_id: Optional[int] = None
    category_id: Optional[int] = None
    amount_excl_vat: Decimal = Field(..., ge=0, description="KDV Hariç Tutar")
    vat_rate: Decimal = Field(default=Decimal("0.20"), ge=0, le=1, description="KDV Oranı (örn 0.20)")
    amount_incl_vat: Optional[Decimal] = Field(default=None, description="KDV Dahil Tutar")
    payment_method: Optional[str] = "Kredi Kartı"
    invoice_status: Optional[str] = "Bekliyor"
    description: Optional[str] = None

    @model_validator(mode="after")
    def compute_and_validate_amount_incl_vat(self):
        calculated_incl = (self.amount_excl_vat * (Decimal("1.00") + self.vat_rate)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if self.amount_incl_vat is None:
            self.amount_incl_vat = calculated_incl
        else:
            # Finansal Bütünlük: KDV dahil tutar hariç tutar + KDV ile tutarlı olmalıdır (0.02 TL tolerans)
            if abs(self.amount_incl_vat - calculated_incl) > Decimal("0.02"):
                raise ValueError(
                    f"KDV Dahil Tutar ({self.amount_incl_vat}) ile KDV Hariç Tutar ({self.amount_excl_vat}) ve %{int(self.vat_rate * 100)} KDV tutarsız. Beklenen: {calculated_incl}"
                )
        return self

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    date: Optional[date] = None
    department_id: Optional[int] = None
    customer_name: Optional[str] = None
    customer_tax_id: Optional[str] = None
    item_name: Optional[str] = None
    staff_name: Optional[str] = None
    employee_id: Optional[int] = None
    category_id: Optional[int] = None
    amount_excl_vat: Optional[Decimal] = None
    vat_rate: Optional[Decimal] = None
    amount_incl_vat: Optional[Decimal] = None
    payment_method: Optional[str] = None
    invoice_status: Optional[str] = None
    description: Optional[str] = None

    @model_validator(mode="after")
    def compute_and_validate_amount_incl_vat(self):
        if self.amount_excl_vat is not None and self.vat_rate is not None:
            calculated_incl = (self.amount_excl_vat * (Decimal("1.00") + self.vat_rate)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if self.amount_incl_vat is None:
                self.amount_incl_vat = calculated_incl
            else:
                if abs(self.amount_incl_vat - calculated_incl) > Decimal("0.02"):
                    raise ValueError(
                        f"KDV Dahil Tutar ({self.amount_incl_vat}) ile KDV Hariç Tutar ({self.amount_excl_vat}) ve %{int(self.vat_rate * 100)} KDV tutarsız. Beklenen: {calculated_incl}"
                    )
        return self

class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    branch_id: int
    department_id: int
    department_name: Optional[str] = None
    employee_id: Optional[int] = None
    employee_name: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    date: date
    customer_name: str
    customer_tax_id_masked: Optional[str] = None  # KVKK Veri Minimizasyonu: Ham TCKN/VKN API'de döndürülmez
    item_name: str
    staff_name: Optional[str] = None
    amount_excl_vat: Decimal
    vat_rate: Decimal
    amount_incl_vat: Decimal
    payment_method: Optional[str] = None
    invoice_status: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
