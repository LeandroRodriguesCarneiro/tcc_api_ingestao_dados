from fastapi import UploadFile

import shutil
from pathlib import Path

class FileStorage:
    def __init__(self):
        self.temp_dir = Path("/app/tmp")
        self.temp_dir.mkdir(exist_ok=True)

    def save_file(self, file: UploadFile) -> Path:
        file_path = self.temp_dir / f"{file.filename}"

        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        return file_path