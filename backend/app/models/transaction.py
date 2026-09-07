from sqlalchemy import Column, Integer, String, Text, Numeric, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.app.core.database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)
    
    date = Column(Date, nullable=False, index=True)
    customer_name = Column(String(200), nullable=False)
    customer_tax_id = Column(String(50), nullable=True)  # Maskeli gösterim yapılacak
    item_name = Column(String(255), nullable=False)  # İşlem / Kategori adı
    staff_name = Column(String(150), nullable=True)  # İşlemi yapan personel (serbest metin)
    
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    category_id = Column(Integer, ForeignKey("transaction_categories.id"), nullable=True, index=True)
    
    amount_excl_vat = Column(Numeric(14, 2), nullable=False)  # KDV Hariç Tutar
    vat_rate = Column(Numeric(5, 4), nullable=False, default=0.20)  # KDV Oranı (örn 0.20)
    amount_incl_vat = Column(Numeric(14, 2), nullable=False)  # KDV Dahil Tutar
    
    payment_method = Column(String(100), nullable=True)  # Tahsilat şekli
    invoice_status = Column(String(50), nullable=True, default="Bekliyor")  # Faturalandı / Bekliyor
    description = Column(Text, nullable=True)  # Açıklama
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    branch = relationship("Branch", back_populates="transactions")
    department = relationship("Department", back_populates="transactions")
    employee = relationship("Employee", back_populates="transactions")
    category = relationship("TransactionCategory", back_populates="transactions")

    @property
    def customer_tax_id_masked(self):
        if not self.customer_tax_id:
            return None
        clean_id = str(self.customer_tax_id).strip()
        if len(clean_id) <= 4:
            return clean_id
        return "*" * (len(clean_id) - 4) + clean_id[-4:]

