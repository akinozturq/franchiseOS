from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.app.core.database import Base

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    
    name = Column(String(100), nullable=False)  # örn. "Satış Danışmanı", "Genel Müdür"
    turnover_source = Column(String(50), nullable=False, default="kendi_departmani")  # "kendi_departmani" | "tum_bayi"
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    branch = relationship("Branch")
    employees = relationship("Employee", back_populates="role")
    commission_tiers = relationship("RoleCommissionTier", back_populates="role", cascade="all, delete-orphan")
