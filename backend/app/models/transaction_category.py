from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, date
from backend.app.core.database import Base

class TransactionCategory(Base):
    __tablename__ = "transaction_categories"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    
    name = Column(String(150), nullable=False)
    general_override_rate = Column(Numeric(5, 4), nullable=True)  # Franchisor-bayi genel kural istisna oranı (örn 0.15)
    bonus_override_rate = Column(Numeric(5, 4), nullable=True)    # Personel prim kuralı istisna oranı (örn 0.07)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Versioning columns
    effective_from = Column(Date, default=lambda: date(2026, 1, 1), nullable=False)
    effective_to = Column(Date, nullable=True)  # Null = currently active
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    branch = relationship("Branch")
    transactions = relationship("Transaction", back_populates="category")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
