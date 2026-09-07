from pydantic import BaseModel, ConfigDict
from typing import Optional, Any, Dict
from datetime import datetime, date

class RuleChangeLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    branch_id: int
    user_id: Optional[int] = None
    rule_type: str
    entity_id: Optional[int] = None
    action: str
    effective_from: date
    description: Optional[str] = None
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    created_at: datetime
