from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from ..models import TaskManagerModel

class TaskManagerDTO(BaseModel):
    id: Optional[str] = None
    document_name: str
    document_path: str
    document_status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = {
        "from_attributes": True
    }

    def to_model(self) -> TaskManagerModel:
        return TaskManagerModel(**self.model_dump(exclude_unset=True))