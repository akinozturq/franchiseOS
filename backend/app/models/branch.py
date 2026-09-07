from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.app.core.database import Base

class Branch(Base):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True, index=True)
    franchisor_id = Column(Integer, ForeignKey("franchisors.id"), nullable=True, index=True)
    name = Column(String(200), nullable=False)
    tax_id = Column(String(50), nullable=True)
    tax_office = Column(String(100), nullable=True)
    address = Column(String(500), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    franchisor = relationship("Franchisor", back_populates="branches")
    departments = relationship("Department", back_populates="branch", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="branch", cascade="all, delete-orphan")
    commission_tiers = relationship("CommissionTier", back_populates="branch", cascade="all, delete-orphan")
    users = relationship("User", back_populates="branch")

