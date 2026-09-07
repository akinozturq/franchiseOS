from sqlalchemy import Column, Integer, String, Date, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.app.core.database import Base

class RuleChangeLog(Base):
    __tablename__ = "rule_change_logs"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    rule_type = Column(String(50), nullable=False)  # COMMISSION_TIER, ROLE_TIER, CATEGORY_OVERRIDE
    entity_id = Column(Integer, nullable=True)
    action = Column(String(50), nullable=False)     # CREATE, UPDATE, DELETE
    effective_from = Column(Date, nullable=False)
    description = Column(Text, nullable=True)
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    branch = relationship("Branch")
    user = relationship("User")
