from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class UploadPreviewResponse(BaseModel):
    file_id: str
    file_name: str
    file_headers: List[str]
    suggested_mapping: Dict[str, Optional[str]]
    preview_rows: List[Dict[str, Any]]
    total_rows: int

class ImportExecuteRequest(BaseModel):
    file_id: str
    column_mapping: Dict[str, str]  # system_field -> file_column_name
    default_department_id: Optional[int] = None

class ImportRowError(BaseModel):
    row_index: int
    raw_data: Dict[str, Any]
    error_message: str

class ImportResultResponse(BaseModel):
    total_rows: int
    successful_count: int
    failed_count: int
    errors: List[ImportRowError]
