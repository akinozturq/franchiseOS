from sqlalchemy import Column, Integer, Numeric, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, date
from backend.app.core.database import Base

class CommissionTier(Base):
    __tablename__ = "commission_tiers"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    
    min_amount = Column(Numeric(14, 2), nullable=False)  # Alt sınır (TL)
    max_amount = Column(Numeric(14, 2), nullable=True)   # Üst sınır (TL, null = sonsuz)
    rate = Column(Numeric(5, 4), nullable=False)         # Oran (örn: 0.30 -> %30)
    
    # Versioning columns
    effective_from = Column(Date, default=lambda: date(2026, 1, 1), nullable=False)
    effective_to = Column(Date, nullable=True)  # Null = currently active
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    branch = relationship("Branch", back_populates="commission_tiers")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
