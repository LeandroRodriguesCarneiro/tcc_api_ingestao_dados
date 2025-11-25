import asyncio
import uuid
from pathlib import Path
from typing import List, Optional

from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, HTMLFormatOption
from docling.datamodel.base_models import InputFormat

from html_to_markdown import convert_to_markdown  

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
    def __init__(
        self,
        *args,
        storage_base: str = "/app/tmp",
        max_attempts_per_split: int = 3,
        splitter_size: int = 10,
        **kwargs
    ):
        super().__init__(
            topic="document_ingestion.text_processing",
            group_id="docling_processing_group",
            *args,
            **kwargs
        )
        self.vector_db = VectorDataBase()
        self.storage_base = Path(storage_base)
        self.max_attempts_per_split = max_attempts_per_split
        self.splitter_size = splitter_size

        self.storage_base.mkdir(parents=True, exist_ok=True)

    async def process_message(self, data: dict, session=None):
        self.task_manager_repo = TaskManagerRepository(session)

        document_id = data.get("document_id")
        document_path = data.get("document_path")
        document_name = data.get("document_name")
        splitter_path = data.get("splitter_path")
        page_start, page_end = data.get("page_range", (None, None))
        mime_type = data.get("mime_type")

        logger.info(f"Processando documento_id={document_id}, path={document_path}, mime_type={mime_type}")

        try:
            if mime_type == "text/html":
                converter = DocumentConverter(
                allowed_formats=[InputFormat.HTML],
                format_options={InputFormat.HTML: HTMLFormatOption()}
                )

                result = converter.convert(document_path)

                docling_document = result.document
                markdown = docling_document.export_to_markdown()

                out_dir = self.storage_base / f"{document_name.split('.')[0]}"
                out_dir.mkdir(parents=True, exist_ok=True)

                path_md = out_dir / f"{document_name.split('.')[0]}.md"  
                path_md.write_text(markdown, encoding="utf-8")
                document_path = path_md

            self.vector_db.test_conection()

            for key, value in data.items():
                logger.info(f"  {key} = {value}")

            task = self.task_manager_repo.get_by_id(document_id)
            if task:
                self._update_task_status(task, status="processed")
            else:
                logger.warning(f"Task para document_id {document_id} não encontrada")

        except Exception as e:
            logger.exception(f"Erro processando documento {document_id}: {e}")
            task = self.task_manager_repo.get_by_id(document_id)
            if task:
                try:
                    self._update_task_status(task, status="error")
                except Exception:
                    logger.error("Falha ao marcar task como erro")
            raise IndexWorkerError(f"Falha no processamento do documento {document_id}") from e

    def _update_task_status(self, task: TaskManagerModel, status: str):
        try:
            task.document_status = status
            merged_task = self.task_manager_repo.session.merge(task)
            self.task_manager_repo.update(merged_task)
            logger.info(f"Task {task.id} status atualizado para {status}")
        except Exception:
            logger.exception(f"Erro ao atualizar status da task para '{status}'")
            raise

