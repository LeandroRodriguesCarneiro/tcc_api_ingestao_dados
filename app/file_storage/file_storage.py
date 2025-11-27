from fastapi import UploadFile
import shutil
from pathlib import Path
import os
import tempfile
from ..loggin import logger


class FileStorage:
    def __init__(self):
        self.temp_dir = Path("/app/tmp")
        self.temp_dir.mkdir(exist_ok=True)

    def save_file(self, file: UploadFile) -> Path:
        file_name = file.filename.upper()
        logger.info(f"Salvando arquivo {file_name}")
        file_dir = self.temp_dir / f"{file_name.split('.')[0]}"
        file_dir.mkdir(parents=True, exist_ok=True)

        file_path = file_dir / file_name

        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        logger.info(f"Arquivo {file_name} salvo com sucesso")
        return file_path

    def write_text_file(self, content: str, out_path: Path):
        """
        Grava com segurança um arquivo de texto (ex: Markdown), usando arquivo temporário e replace.
        """
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_fd, tmp_name = tempfile.mkstemp(prefix="tmp_text_", suffix=".md", dir=str(out_path.parent))
        os.close(tmp_fd)
        try:
            with open(tmp_name, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_name, str(out_path))
            logger.info(f"Arquivo de texto salvo com sucesso: {out_path}")
        except Exception as e:
            logger.error(f"Erro ao escrever arquivo de texto {out_path}: {e}")
            raise
        finally:
            if os.path.exists(tmp_name):
                try:
                    os.remove(tmp_name)
                except Exception as e:
                    logger.error(f"Erro ao remover arquivo temporário {tmp_name}: {e}")
