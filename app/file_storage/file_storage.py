from fastapi import UploadFile

import shutil
from pathlib import Path
import os
import tempfile
from PyPDF2 import PdfWriter
from ..loggin import logger

class FileStorage:
    def __init__(self):
        self.temp_dir = Path("/app/tmp")
        self.temp_dir.mkdir(exist_ok=True)

    def save_file(self, file: UploadFile) -> Path:
        logger.info(f"Salvando arquivo {file.filename}")
        file_dir = self.temp_dir / f"{file.filename.split('.')[0]}"
        file_dir.mkdir(parents=True, exist_ok=True)

        file_path = file_dir / file.filename

        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        logger.info(f"Arquivo {file.filename} salvo com sucesso")
        return file_path

    def write_splitter_pdf(self, writer: PdfWriter, out_path: Path):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_fd, tmp_name = tempfile.mkstemp(prefix="splitter_", suffix=".pdf", dir=str(out_path.parent))
        os.close(tmp_fd)
        try:
            with open(tmp_name, "wb") as f:
                writer.write(f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_name, str(out_path))
        except Exception as e:
            logger.error(f"Erro ao escrever arquivo PDF: {e}")
            raise
        finally:
            if os.path.exists(tmp_name):
                try:
                    os.remove(tmp_name)
                except Exception as e:
                    logger.error(f"Erro ao remover arquivo temporário {tmp_name}: {e}")
