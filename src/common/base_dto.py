from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class BaseDTO(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

class ErrorResponseDTO(BaseModel):
    message: str
    status: int
    raw_response: Optional[Dict[str, Any]] = None
    time: datetime = Field(default_factory=datetime.now)
