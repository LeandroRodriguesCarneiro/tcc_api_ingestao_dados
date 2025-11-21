import asyncio
import uuid
from pathlib import Path
from typing import List

from PyPDF2 import PdfReader, PdfWriter

from .kafka_worker import KafkaWorker
from ...repositories import TaskManagerRepository
from ...models import TaskManagerModel
from ...database import Database
from ...loggin import logger
from ..producer import KafkaProducer
from ...file_storage import FileStorage

class PDFSplitterError(RuntimeError):
    pass

class PDFSplitterWorker(KafkaWorker):
    def __init__(self, *args, storage_base: str = "/app/tmp", output_topic: str = "document_ingestion.extracting",
                 max_attempts_per_split: int = 3, splitter_size=10, **kwargs):
        super().__init__(
            topic="document_ingestion.pdf_processing",
            group_id="pdf_processing_group",
            *args,
            **kwargs
        )

        self.storage_base = Path(storage_base)
        self.storage_base.mkdir(parents=True, exist_ok=True)

        self.task_manager_repo = TaskManagerRepository(next(Database.get_db()))
        self.producer = KafkaProducer()
        self.output_topic = output_topic
        self.max_attempts_per_split = int(max_attempts_per_split)
        self.splitter_size = splitter_size
        self.file_storage = FileStorage()

    async def process_message(self, data: dict, session=None):
        document_id = data.get("document_id")
        pdf_path = data.get("document_path")
        if not document_id or not pdf_path:
            logger.error("❌ Mensagem inválida: faltando document_id ou document_path")
            return

        document_name = data.get("document_name", Path(pdf_path).stem)
        repo = TaskManagerRepository(session) if session is not None else self.task_manager_repo
        task = repo.get_by_id(document_id)

        if not task:
            logger.error(f"❌ JobID {document_id} não encontrado no banco!")
            return

        logger.info(f"📄 Iniciando processamento do PDF: {document_name} ({pdf_path})")

        try:
            reader = PdfReader(str(pdf_path))
            pages = list(reader.pages)
        except Exception as e:
            logger.error(f"❌ Erro ao abrir PDF '{pdf_path}': {e}")
            self._update_task_status(task, "Error")
            return

        total_pages = len(pages)
        logger.info(f"📑 Total de páginas: {total_pages}. Splitter size: {self.splitter_size}")

        doc_uuid = uuid.uuid4().hex
        out_dir = self.storage_base / f"{document_name.split('.')[0]}"
        out_dir.mkdir(parents=True, exist_ok=True)

        generated_paths: List[Path] = []

        try:
            for start in range(0, total_pages, self.splitter_size):
                end = min(start + self.splitter_size, total_pages)
                splitter_filename = f"{document_name}_{start+1}_{end}.pdf"
                splitter_path = out_dir / splitter_filename

                success = False
                last_exc = None

                for attempt in range(1, self.max_attempts_per_split + 1):
                    try:
                        await asyncio.to_thread(self._write_splitter_atomic, pages, start, end, splitter_path)
                        validate_reader = PdfReader(str(splitter_path))
                        actual_pages = len(list(validate_reader.pages))
                        if actual_pages != (end - start):
                            raise PDFSplitterError(f"Validação falhou: esperava {end - start}, obteve {actual_pages}")

                        success = True
                        break
                    except Exception as exc:
                        last_exc = exc
                        logger.warning(f"🔁 Tentativa {attempt}/{self.max_attempts_per_split} falhou para {splitter_filename}: {exc}")
                        if splitter_path.exists():
                            try:
                                splitter_path.unlink()
                            except Exception:
                                logger.debug("Não foi possível remover arquivo parcial.")

                if not success:
                    logger.error(f"❌ Falha permanente ao gerar splitter {splitter_filename}: {last_exc}")
                    for p in generated_paths:
                        try:
                            p.unlink()
                        except Exception:
                            pass
                    self._update_task_status(task, "Error")
                    raise PDFSplitterError(f"Falha ao gerar splitter {splitter_filename}: {last_exc}")

                generated_paths.append(splitter_path)

                data["splitter_name"] = splitter_filename
                data["splitter_path"] = str(splitter_path.resolve())
                data["page_range"] = [start + 1, end]
                data["total_pages"] = total_pages
                data["document_uuid"] = doc_uuid

                await asyncio.to_thread(self.producer.send, self.output_topic, data)
                logger.info(f"📦 Splitter enviado: páginas {start+1}-{end} -> {splitter_filename}")

            self._update_task_status(task, "Extracting")
            logger.info(f"🟢 Documento {document_id} atualizado para Extracting")

            return [str(p.resolve()) for p in generated_paths]

        except Exception:
            logger.exception(f"❌ Erro ao processar PDF '{document_name}'")
            self._update_task_status(task, "Error")
            raise

    def _write_splitter_atomic(self, pages: List, start: int, end: int, out_path: Path):
        writer = PdfWriter()
        for i in range(start, end):
            writer.add_page(pages[i])

        self.file_storage.write_splitter_pdf(writer, out_path)

    def _update_task_status(self, task: TaskManagerModel, status: str):
        """
        Atualiza o status da task diretamente.
        """
        try:
            task.document_status = status
            merged_task = self.task_manager_repo.session.merge(task)
            self.task_manager_repo.update(merged_task)
        except Exception:
            logger.exception(f"Erro ao atualizar status da task para '{status}'")
            raise
