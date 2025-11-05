import json

from sqlalchemy.orm import Session

from fastapi import UploadFile

from ..kafka import KafkaProducer
from ..models import TaskManagerModel
from ..dtos import TaskManagerDTO
from ..repositories import TaskManagerRepository
from ..file_storage import FileStorage

class IndexDocumentService:
    def __init__(self, db: Session):
        self.db = db
        self._init_repositories()
        self.producer = KafkaProducer()

    def _init_repositories(self) -> None:
        self.task_manager = TaskManagerRepository(self.db)
    
    def save_file(self, file: UploadFile):
        file_storage = FileStorage()
        file_path = file_storage.save_file(file)

        task_manager_dto = TaskManagerDTO(
            document_name=file.filename,
            document_path=file_path,
            document_status='Started'
        )
        self.task_manager.add(task_manager_dto.to_model())
        self.db.commit()

        model_instance = self.task_manager.add(task_manager_dto.to_model())
        message = {
            "document_id": model_instance.id,
            "document_name": file.filename,
            "document_path": file_path,
            "mime_type": file.content_type
        }

        self.producer.send("document_ingestion.init", json.dumps(message).encode("utf-8"))
        return message
    
    def consult_file(self, file_id):
        model_instance = self.task_manager.get_by_id(file_id)
        task_dto = TaskManagerDTO.model_validate(model_instance, from_attributes=True)

        message = {
            "document_id": model_instance.id,
            "document_name": task_dto.document_name,
            "document_satus": task_dto.document_status,
            "created_at": task_dto.created_at,
            "updated_at": task_dto.updated_at
        }

        return message
