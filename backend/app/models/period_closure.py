from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.app.core.database import Base

class PeriodClosure(Base):
    __tablename__ = "period_closures"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    
    status = Column(String(30), default="CLOSED", nullable=False)  # CLOSED, REOPENED, CLOSURE_REQUESTED
    closed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    closed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    reconciliation_snapshot = Column(JSON, nullable=True)
    bonus_snapshot = Column(JSON, nullable=True)
    
    calculation_engine_version = Column(String(100), nullable=True)
    input_hash = Column(String(64), nullable=True)
    result_hash = Column(String(64), nullable=True)
    
    reopened_at = Column(DateTime, nullable=True)
    reopened_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reopen_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    branch = relationship("Branch")
    closed_by = relationship("User", foreign_keys=[closed_by_user_id])
    reopened_by = relationship("User", foreign_keys=[reopened_by_user_id])
