from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.app.core.database import Base

class PeriodSetting(Base):
    __tablename__ = "period_settings"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    collector_party = Column(String(50), nullable=False, default="BAYI")  # "BAYI" or "FRANCHISOR"
    vat_rate = Column(Numeric(5, 4), nullable=False, default=0.20)
    is_locked = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("branch_id", "year", "month", name="uq_branch_period"),
    )

    branch = relationship("Branch")
