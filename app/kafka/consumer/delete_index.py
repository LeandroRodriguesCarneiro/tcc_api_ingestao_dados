import asyncio
import uuid
from pathlib import Path
import os
import shutil
import re
from typing import Optional

from docling.document_converter import DocumentConverter, HTMLFormatOption
from docling.datamodel.base_models import InputFormat

from .kafka_worker import KafkaWorker
from ...repositories import TaskManagerRepository
from ...models import TaskManagerModel
from ...loggin import logger
from ...database import VectorDataBase
from ..producer import KafkaProducer

class DeleteIndexWorkerError(RuntimeError):
    pass

class DeleteIndexWorker(KafkaWorker):
    def __init__(self, *args, storage_base: str = "/app/tmp", output_topic: str = "document_ingestion.init",
                max_attempts_per_split: int = 3, splitter_size=10, **kwargs):
        super().__init__(
            topic="document_ingestion.deleted",
            group_id="docling_processing_group",
            *args,
            **kwargs
        )
        self.vector_db = VectorDataBase()
        self.output_topic = output_topic
        self.storage_base = Path(storage_base)
        self.max_attempts_per_split = max_attempts_per_split
        self.splitter_size = splitter_size
        self.producer = KafkaProducer()
        self.storage_base.mkdir(parents=True, exist_ok=True)

    async def process_message(self, data: dict, session=None):
        self.task_manager_repo = TaskManagerRepository(session)

        document_id = data.get("document_id")
        document_path = Path(data.get("document_path")) if data.get("document_path") else None
        document_name = data.get("document_name")
        operation_type = data.get("operation_type")
        mime_type = data.get("mime_type")

        task = self.task_manager_repo.get_by_id(document_id)

        logger.info(f"Processando DELETE/UPDATE document_id={document_id}, operation_type={operation_type}")

        if not document_id or not document_name or not task:
            logger.error("❌ Dados insuficientes ou task inexistente")
            return

        try:
            logger.info(f"🗑️ Removendo vetores do documento {document_name}")
            self.vector_db.delete_document(document_name)

            if operation_type == "delete":
                logger.info(f"📝 Documento {document_name} removido com sucesso (DELETE).")
                self._update_task_status(task, status="processed")
                return

            if operation_type == "update":
                logger.info(f"♻️ Atualizando documento {document_name}: reenviando para reindexação...")

                payload = {
                    "document_id": document_id,
                    "document_path": str(document_path),
                    "document_name": document_name,
                    "mime_type": mime_type,
                }

                self.producer.send(self.output_topic, payload)

                logger.info(f"📤 Documento reenviado para '{self.output_topic}'")

                self._update_task_status(task, status="processed")
                return

            logger.warning(f"⚠️ operation_type inválido: {operation_type}")
            self._update_task_status(task, status="error")

        except Exception as e:
            logger.exception(f"Erro processando documento {document_id}: {e}")
            if task:
                try:
                    self._update_task_status(task, status="error")
                except Exception:
                    logger.error("Falha ao marcar task como erro")
            raise DeleteIndexWorkerError(f"Falha no processamento do documento {document_id}") from e

    def _update_task_status(self, task: TaskManagerModel, status: str):
        try:
            task.document_status = status
            merged_task = self.task_manager_repo.session.merge(task)
            self.task_manager_repo.update(merged_task)
            logger.info(f"Task {task.id} status atualizado para {status}")
        except Exception:
            logger.exception(f"Erro ao atualizar status da task para '{status}'")
            raise
