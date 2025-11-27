from typing import Generator
import magic
from fastapi import APIRouter, Form, HTTPException, UploadFile, File, Depends
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
        )

        self.router.add_api_route(
            "/consult_document",
            self.consult_document,
            methods=["POST"],
        )

        self.router.add_api_route(
            "/update_document",
            self.update_document,
            methods=["PUT"],
        )

        self.router.add_api_route(
            "/delete_document",
            self.delete_document,
            methods=["DELETE"],
        )

    def validate_token(self, access_token: str):
        if not access_token:
            raise HTTPException(status_code=401, detail="Usuário não autenticado")

        security = SecurityService()
        try:
            security.validate_access_token(access_token)
        except Exception:
            raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    def detect_mime(self, file: UploadFile):
        header = file.file.read(4096)
        file.file.seek(0)

        mime = magic.from_buffer(header, mime=True) or ""

        if mime not in Settings.MIME_TYPES_PERMITIDOS:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de arquivo não permitido ou não reconhecido: {mime}"
            )
        return mime

    async def ingest_document(
        self,
        file: UploadFile = File(...),
        access_token: str = Form(...),
        db: Session = Depends(Database.get_db)
    ):
        self.validate_token(access_token)

        mime = self.detect_mime(file)

        service = IndexDocumentService(db)
        result = service.save_file(file, mime)

        return JSONResponse(content={
            "status": "Processamento do documento iniciado",
            "document_id": result["document_id"],
            "document_name": result["document_name"],
        })

    async def consult_document(
        self,
        access_token: str = Form(...),
        document_id: str = Form(...),
        db: Session = Depends(Database.get_db)
    ):
        self.validate_token(access_token)

        service = IndexDocumentService(db)
        result = service.consult_file(document_id)

        return JSONResponse(content=jsonable_encoder(result))

    async def update_document(
        self,
        document_id: str = Form(...),
        file: UploadFile = File(...),
        access_token: str = Form(...),
        db: Session = Depends(Database.get_db)
    ):
        self.validate_token(access_token)

        mime = self.detect_mime(file)

        service = IndexDocumentService(db)
        result = service.update_file(document_id, file, mime)

        return JSONResponse(content={
            "status": "Documento atualizado com sucesso",
            "document_id": result["document_id"],
            "document_name": result["document_name"]
        })

    async def delete_document(
        self,
        document_id: str = Form(...),
        access_token: str = Form(...),
        db: Session = Depends(Database.get_db)
    ):
        self.validate_token(access_token)

        service = IndexDocumentService(db)
        service.delete_file(document_id)

        return JSONResponse(content={
            "status": "Documento deletado com sucesso",
            "document_id": document_id
        })
