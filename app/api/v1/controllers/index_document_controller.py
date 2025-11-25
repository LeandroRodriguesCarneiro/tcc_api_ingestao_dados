from typing import Generator
import filetype
import magic
from fastapi import APIRouter, Body, HTTPException, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from ....settings import Settings
from ....services import IndexDocumentService, SecurityService
from ....database import Database
from ....loggin import logger

database = Database.get_instance()

class IndexDocumentController:
    def __init__(self):
        self.router = APIRouter()

        self.router.add_api_route(
            "/ingest_document",
            self.ingest_document,
            methods=["POST"],
            tags=["documents"]
        )
        self.router.add_api_route(
            "/consult_document",
            self.consult_document,
            methods=["POST"],
            tags=["documents"]
        )

    async def ingest_document(
        self,
        file: UploadFile = File(...),
        access_token: str = Body(...),
        db: Session = Depends(Database.get_db)
    ):
        if not access_token:
            raise HTTPException(status_code=401, detail="Usuário não autenticado")

        security = SecurityService()
        try:
            security.validate_access_token(access_token)
        except Exception:
            raise HTTPException(status_code=401, detail="Token inválido ou expirado")

        header = await file.read(4096)
        await file.seek(0)
        mime = magic.from_buffer(header, mime=True)

        logger.info(f'{mime} {file}')
        if mime not in Settings.MIME_TYPES_PERMITIDOS:
            raise HTTPException(
                status_code=400,
                detail="Tipo de arquivo não permitido ou não reconhecido."
            )

        service = IndexDocumentService(db)
        result = service.save_file(file, mime)

        return JSONResponse(content={
            "status": "Processamento do documento iniciado",
            "document_id": result["document_id"],
            "document_name": result["document_name"],
        })

    async def consult_document(
        self,
        access_token: str = Body(...),
        id: str = Body(...),
        db: Session = Depends(Database.get_db)
    ):
        if not access_token:
            raise HTTPException(status_code=401, detail="Usuário não autenticado")

        security = SecurityService()
        try:
            security.validate_access_token(access_token)
        except Exception:
            raise HTTPException(status_code=401, detail="Token inválido ou expirado")

        service = IndexDocumentService(db)
        result = service.consult_file(id)

        return JSONResponse(content=jsonable_encoder(result))
