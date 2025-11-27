import json

from sqlalchemy.orm import Session

from fastapi import UploadFile

from ..kafka import KafkaProducer
from ..models import TaskManagerModel
from ..dtos import TaskManagerDTO
from ..repositories import TaskManagerRepository
from ..file_storage import FileStorage

from ..database import Database

database = Database()

class IndexDocumentService:
    def __init__(self, db: Session):
        self.db = db
        self._init_repositories()
        self.producer = KafkaProducer()

    def _init_repositories(self) -> None:
        self.task_manager = TaskManagerRepository(self.db)
    
    def save_file(self, file: UploadFile, mime_type):
        file_storage = FileStorage()
        file_path = file_storage.save_file(file)

        task_manager_dto = TaskManagerDTO(
            document_name=file.filename.upper(),
            document_path=str(file_path),
            document_status='Started'
        )

        model_instance = self.task_manager.add(task_manager_dto.to_model())

        message = {
            "document_id": str(model_instance.id),
            "document_name": file.filename.upper(),
            "document_path": str(file_path),
            "mime_type": mime_type
        }

        self.producer.send("document_ingestion.init", message)
        return message
    
    def consult_file(self, file_id):
        model_instance = self.task_manager.get_by_id(file_id)
        task_dto = TaskManagerDTO.model_validate(model_instance, from_attributes=True)

        message = {
            "document_id": str(model_instance.id),
            "document_name": task_dto.document_name,
            "document_satus": task_dto.document_status,
            "created_at": task_dto.created_at,
            "updated_at": task_dto.updated_at
        }

        return message
    
    def delete_file(self, document_id: str):
        model_instance = self.task_manager.get_by_id(document_id)
        if not model_instance:
            raise ValueError("Documento não encontrado.")

        message = {
            "document_id": str(document_id),
            "document_name": model_instance.document_name,
            "document_path": model_instance.document_path,
            "operation_type": "delete"
        }

        self.producer.send("document_ingestion.deleted", message)

        return {"status": "deleted", "document_id": document_id}

    def update_file(self, document_id: str, file: UploadFile, mime_type):
        model_instance = self.task_manager.get_by_id(document_id)
        if not model_instance:
            raise ValueError("Documento não encontrado.")

        file_storage = FileStorage()
        new_file_path = file_storage.save_file(file)

        model_instance.document_name = file.filename.upper()
        model_instance.document_path = str(new_file_path)
        model_instance.document_status = "Updating"

        updated_model = self.task_manager.update(model_instance)

        delete_message = {
            "document_id": str(updated_model.id),
            "document_name": updated_model.document_name,
            "document_path": updated_model.document_path,
            "mime_type": mime_type,
            "operation_type": "update"
        }

        self.producer.send("document_ingestion.deleted", delete_message)

        return delete_message