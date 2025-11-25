import asyncio
import uuid
import subprocess
from pathlib import Path

from .kafka_worker import KafkaWorker
from ...repositories import TaskManagerRepository
from ...models import TaskManagerModel
from ...database import Database
from ...loggin import logger
from ..producer import KafkaProducer
from ...file_storage import FileStorage

class DocxToPdfSplitterWorkerError(RuntimeError):
    pass

class DocxToPdfSplitterWorker(KafkaWorker):
    def __init__(self, *args,
                 storage_base: str = "/app/tmp",
                 output_topic: str = "document_ingestion.pdf_processing",
                 splitter_page_size: int = 10,
                 **kwargs):
        super().__init__(
            topic="document_ingestion.docx_processing",
            group_id="docx_to_pdf_split_group",
            *args,
            **kwargs
        )

        self.storage_base = Path(storage_base)
        self.storage_base.mkdir(parents=True, exist_ok=True)

        self.producer = KafkaProducer()
        self.output_topic = output_topic
        self.splitter_page_size = splitter_page_size
        self.file_storage = FileStorage()

    async def process_message(self, data: dict, session=None):
        document_id = data.get("document_id")
        document_path = data.get("document_path")
        if not document_id or not document_path:
            logger.error("❌ Mensagem inválida: faltando document_id ou document_path")
            return

        document_name = data.get("document_name", Path(document_path).stem)
        self.task_manager_repo = TaskManagerRepository(session)
        task = self.task_manager_repo.get_by_id(document_id)

        if not task:
            logger.error(f"❌ JobID {document_id} não encontrado")
            return

        logger.info(f"📄 Convertendo DOCX para PDF: {document_name} ({document_path})")

        try:
            document_name_stem = Path(document_path).stem
            
            out_dir = self.storage_base / document_name_stem
            out_dir.mkdir(parents=True, exist_ok=True)

            pdf_filename = f"{document_name_stem}.pdf"
            pdf_path = out_dir / pdf_filename

            cmd = [
                "soffice",
                "--headless",
                "--convert-to", "pdf",
                "--outdir", str(out_dir),
                document_path
            ]
            subprocess.run(cmd, check=True)
            logger.info(f"✅ DOCX convertido para PDF: {pdf_path}")

        except Exception as e:
            logger.exception("❌ Erro na conversão ou divisão")
            self._update_task_status(task, "Error")
            raise DocxToPdfSplitterWorkerError(e)
        
        docx_to_delete = Path(document_path)
        try:
            docx_to_delete.unlink()
            logger.info(f"🗑️ Arquivo original DOCX removido: {docx_to_delete}")
        except FileNotFoundError:
            logger.warning(f"Arquivo DOCX já não existe: {docx_to_delete}")
        except Exception as e:
            logger.error(f"Erro ao apagar DOCX {docx_to_delete}: {e}")

        data["document_path"] = str(pdf_path.resolve())

        await asyncio.to_thread(self.producer.send, self.output_topic, data)
        logger.info(f"📦 Mensagem enviada com o PDF convertido: {pdf_path}")

        self._update_task_status(task, "ConvertedToPdf")

    def _update_task_status(self, task: TaskManagerModel, status: str):
        try:
            task.document_status = status
            merged = self.task_manager_repo.session.merge(task)
            self.task_manager_repo.update(merged)
        except Exception:
            logger.exception(f"Erro ao atualizar status da task para '{status}'")
            raise
