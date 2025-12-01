from typing import Generator
import magic
from fastapi import APIRouter, Form, HTTPException, UploadFile, File, Depends, Query
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ....settings import Settings
from ....services import IndexDocumentService, SecurityService
from ....database import Database
from ....loggin import logger

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

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
            methods=["GET"],
        )

        self.router.add_api_route(
            '/list_documents',
            self.list_documents,
            methods=['GET']
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
        access_token: str = Depends(oauth2_scheme),
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
        access_token: str = Depends(oauth2_scheme),
        document_id: str = Query(...),
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
        access_token: str = Depends(oauth2_scheme),
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
        document_id: str = Query(...),
        access_token: str = Depends(oauth2_scheme),
        db: Session = Depends(Database.get_db)
    ):
        self.validate_token(access_token)

        service = IndexDocumentService(db)
        service.delete_file(document_id)

        return JSONResponse(content={
            "status": "Documento deletado com sucesso",
            "document_id": document_id
        })

    async def list_documents(
        self,
        access_token: str = Depends(oauth2_scheme),
        db: Session = Depends(Database.get_db),
        page: int = Query(1, ge=1, description="Número da página (começando em 1)"),
        size: int = Query(10, ge=1, le=100, description="Tamanho da página")
    ):
        self.validate_token(access_token)

        service = IndexDocumentService(db)
        
        response_data = service.get_documents(page=page, size=size)

        return JSONResponse(content=response_data)