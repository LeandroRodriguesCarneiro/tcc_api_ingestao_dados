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
from ...loggin import logger
from ..producer import KafkaProducer
from ...file_storage import FileStorage

class PDFSplitterWorkerError(RuntimeError):
    pass

class PDFSplitterWorker(KafkaWorker):
    def __init__(self, *args, storage_base: str = "/app/tmp", output_topic: str = "document_ingestion.text_processing",
                max_attempts_per_split: int = 3, splitter_size=10, **kwargs):
        super().__init__(
            topic="document_ingestion.pdf_processing",
            group_id="docling_processing_group",
            *args,
            **kwargs
        )

        self.storage_base = Path(storage_base)
        self.storage_base.mkdir(parents=True, exist_ok=True)

        self.producer = KafkaProducer()
        self.output_topic = output_topic
        self.max_attempts_per_split = int(max_attempts_per_split)
        self.splitter_size = splitter_size
        self.file_storage = FileStorage()

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.do_cell_matching = True
        pipeline_options.ocr_options.lang = ["pt"]

        self.doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

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
            logger.error(f"❌ JobID {document_id} não encontrado no banco!")
            return

        logger.info(f"📄 Iniciando extração com Docling: {document_name} ({document_path})")

        try:
            result = await asyncio.to_thread(self.doc_converter.convert, document_path)
            doc = result.document

            num_pages = doc.num_pages()
            n_groups = (num_pages + self.splitter_size - 1) // self.splitter_size
            logger.info(f"Documento convertido com {num_pages} páginas.")
            logger.info(f"Dividindo o documento em {n_groups} grupos de até {self.splitter_size} páginas.")

            doc_uuid = uuid.uuid4().hex
            out_dir = self.storage_base / f"{document_name.split('.')[0]}"
            out_dir.mkdir(parents=True, exist_ok=True)

            for group_idx in range(n_groups):
                start_page = group_idx * self.splitter_size
                end_page = min(start_page + self.splitter_size, num_pages)

                text = ''
                for i in range(start_page, end_page):
                    doc_page = doc.filter(page_nrs={i})
                    text += f"\n\n--- Pagina {i} ---\n\n"
                    text += doc_page.export_to_text()

                splitter_uuid = uuid.uuid4().hex
                splitter_filename = f"{document_name}_splitter_{group_idx + 1}_pages_{start_page + 1}_to_{end_page}.md"
                splitter_path = out_dir / splitter_filename

                try:
                    await asyncio.to_thread(self.file_storage.write_text_file, text, splitter_path)
                    logger.info(f"✅ Markdown salvo: {splitter_path}")
                except Exception as e:
                    logger.error(f"❌ Erro ao salvar markdown {splitter_filename}: {e}")
                    self._update_task_status(task, "Error")
                    raise PDFSplitterWorkerError(f"Erro ao salvar splitter {splitter_filename}: {e}")

                data["splitter_name"] = splitter_filename
                data["splitter_path"] = str(splitter_path.resolve())
                data["page_range"] = [start_page + 1, end_page]
                data["total_pages"] = num_pages
                data["document_uuid"] = splitter_uuid
                data["total_groups"] = n_groups
                data["partial_group"] = group_idx+1
                data["document_uuid"] = doc_uuid

                await asyncio.to_thread(self.producer.send, self.output_topic, data)
                logger.info(f"📦 splitter enviado: {splitter_filename}")

            self._update_task_status(task, "Extracting")
            logger.info(f"🟢 Documento {document_id} atualizado para Extracting")    

        except Exception:
            logger.exception(f"❌ Erro ao processar documento '{document_name}' com Docling")
            self._update_task_status(task, "Error")
            raise

    def _update_task_status(self, task: TaskManagerModel, status: str):
        try:
            task.document_status = status
            merged_task = self.task_manager_repo.session.merge(task)
            self.task_manager_repo.update(merged_task)
        except Exception:
            logger.exception(f"Erro ao atualizar status da task para '{status}'")
            raise