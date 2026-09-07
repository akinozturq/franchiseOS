from pydantic import BaseModel, ConfigDict
from typing import Optional, Any, Dict
from datetime import datetime

class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    branch_id: Optional[int] = None
    user_id: Optional[int] = None
    type: str
    title: str
    message: str
    payload: Optional[Dict[str, Any]] = None
    channel: str
    is_read: bool
    created_at: datetime
    sent_at: Optional[datetime] = None
