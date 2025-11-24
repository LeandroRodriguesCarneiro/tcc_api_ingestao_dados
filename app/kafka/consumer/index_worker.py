import asyncio
import uuid
from pathlib import Path
from typing import List

from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat

from .kafka_worker import KafkaWorker
from ...repositories import TaskManagerRepository
from ...models import TaskManagerModel
from ...database import Database
from ...loggin import logger
from ..producer import KafkaProducer
from ...file_storage import FileStorage
from ...database import VectorDataBase
class IndexWorkerError(RuntimeError):
    pass

class IndexWorker(KafkaWorker):
    def __init__(self, *args, storage_base: str = "/app/tmp",
                 max_attempts_per_split: int = 3, splitter_size=10, **kwargs):
        super().__init__(
            topic="document_ingestion.text_processing",
            group_id="docling_processing_group",
            *args,
            **kwargs
        )
        self.vector_db = VectorDataBase()

    async def process_message(self, data: dict, session=None):
        document_id = data.get("document_id")
        document_path = data.get("document_path")

        self.vector_db.test_conection()

        for key, value in data.items():
            print(key, value)

    def _update_task_status(self, task: TaskManagerModel, status: str):
        try:
            task.document_status = status
            merged_task = self.task_manager_repo.session.merge(task)
            self.task_manager_repo.update(merged_task)
        except Exception:
            logger.exception(f"Erro ao atualizar status da task para '{status}'")
            raise
