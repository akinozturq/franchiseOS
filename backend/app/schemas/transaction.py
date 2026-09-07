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
    def compute_amount_incl_vat(self):
        if self.amount_incl_vat is None:
            raw_incl = self.amount_excl_vat * (Decimal("1.00") + self.vat_rate)
            self.amount_incl_vat = raw_incl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
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
    def compute_amount_incl_vat(self):
        if self.amount_excl_vat is not None and self.vat_rate is not None and self.amount_incl_vat is None:
            raw_incl = self.amount_excl_vat * (Decimal("1.00") + self.vat_rate)
            self.amount_incl_vat = raw_incl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
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
    customer_tax_id: Optional[str] = None
    customer_tax_id_masked: Optional[str] = None
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

    @model_validator(mode="after")
    def set_masked_tax_id(self):
        if self.customer_tax_id:
            self.customer_tax_id_masked = mask_tax_id(self.customer_tax_id)
        return self
