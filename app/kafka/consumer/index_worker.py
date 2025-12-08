import asyncio
from pathlib import Path
import os
import shutil
import re
import magic

from docling.document_converter import DocumentConverter, HTMLFormatOption
from docling.datamodel.base_models import InputFormat

from .kafka_worker import KafkaWorker
from ...repositories import TaskManagerRepository
from ...models import TaskManagerModel
from ...loggin import logger
from ...database import VectorDataBase
from ...chunking import chunk_by_sentences_with_overlap


class IndexWorkerError(RuntimeError):
    pass


def is_text_file(path: Path) -> bool:
    """🔐 PROTEGIDO CONTRA FileNotFoundError"""
    if not path.exists():
        logger.warning(f"📁 Arquivo já processado: {path}")
        return False
    
    try:
        mime = magic.from_file(str(path), mime=True)
        return mime.startswith("text/")
    except Exception as e:
        logger.warning(f"⚠️ MIME erro {path}: {e}")
        return False


def robust_read_text(path: Path) -> str:
    """Lê um arquivo tentando múltiplas codificações."""
    encodings = [
        "utf-8",
        "utf-16",
        "utf-16-le",
        "utf-16-be",
        "latin1"
    ]

    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except Exception:
            continue

    raise UnicodeDecodeError(
        "decoder",
        b"",
        0,
        1,
        f"Falha ao decodificar arquivo {path} com qualquer encoding"
    )


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
        document_path = Path(data.get("document_path")) if data.get("document_path") else None
        document_name = data.get("document_name")
        splitter_path = Path(data.get("splitter_path")) if data.get("splitter_path") else None
        total_groups = data.get("total_groups")
        partial_group = data.get("partial_group")

        page_start, page_end = data.get("page_range", (None, None))
        mime_type = data.get("mime_type")
        task = self.task_manager_repo.get_by_id(document_id)

        logger.info(f"Processando documento_id={document_id}, path={document_path}, mime_type={mime_type}")

        if not document_id or not document_path or not task:
            logger.error("❌ Dados insuficientes para processar mensagem ou tarefa não encontrada")
            return

        if task and task.document_status == "processed":
            logger.info(f"✅ SKIP: {document_id} já COMPLETO")
            return

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

            path_to_read = splitter_path if splitter_path else document_path

            if not is_text_file(path_to_read):
                logger.info(f"⏭️ Arquivo ausente/processado: {path_to_read}")
                if task and total_groups and partial_group:
                    task.document_status = f"partial_{partial_group}/{total_groups}"
                    self._update_task_status(task, task.document_status)
                return

            text = robust_read_text(path_to_read)

            pattern = r"\n\n--- Pagina (\d+) ---\n\n"
            chunks_with_metadata = []

            if re.search(pattern, text):
                splits = re.split(pattern, text)

                pages_with_numbers = []
                initial_text = splits[0].strip()
                start_index = 1 if not initial_text else 0
                for i in range(start_index, len(splits), 2):
                    page_number = int(splits[i])
                    page_text = splits[i + 1].strip()
                    pages_with_numbers.append((page_number, page_text))

                for page_number, page_text in pages_with_numbers:
                    page_chunks = chunk_by_sentences_with_overlap(page_text, 500, 50)
                    for chunk in page_chunks:
                        chunk_metadata = {
                            "text": chunk,
                            "document_id": document_id,
                            "document_name": document_name,
                            "page_number": page_number,
                            "page_range": f"{page_start}-{page_end}",
                            "splitter_path": str(path_to_read),
                        }
                        chunks_with_metadata.append(chunk_metadata)

            else:
                chunks = chunk_by_sentences_with_overlap(text, 500, 50)
                for idx, chunk in enumerate(chunks):
                    chunk_metadata = {
                        "text": chunk,
                        "document_id": document_id,
                        "document_name": document_name,
                        "chunk_index": idx + 1,
                    }
                    chunks_with_metadata.append(chunk_metadata)

            self.vector_db.add_document(chunks_with_metadata)

            new_status = "processed" if not total_groups else f"partial_{partial_group}/{total_groups}"
            if task:
                task.document_status = new_status
                self._update_task_status(task, new_status)

            should_delete = False
            if total_groups and partial_group:
                should_delete = partial_group == total_groups
            else:
                should_delete = True

            if should_delete:
                dir_to_delete = splitter_path.parent if splitter_path else document_path.parent
                if dir_to_delete.exists():
                    shutil.rmtree(dir_to_delete, ignore_errors=True)
                    logger.info(f"🗑️ [{partial_group}/{total_groups or 1}] Limpeza: {dir_to_delete}")

            logger.info(f"✅ [{partial_group}/{total_groups or 1}] {document_id} COMPLETO")

        except IndexWorkerError:
            raise
        except Exception as e:
            logger.exception(f"Erro {document_id}: {e}")
            if task:
                task.document_status = "error"
                self._update_task_status(task, "error")
            raise IndexWorkerError(str(e)) from e

    def _update_task_status(self, task: TaskManagerModel, status: str):
        try:
            task.document_status = status
            merged_task = self.task_manager_repo.session.merge(task)
            self.task_manager_repo.update(merged_task)
            logger.info(f"Task {task.id} status atualizado para {status}")
        except Exception:
            logger.exception(f"Erro ao atualizar status da task para '{status}'")
            raise
