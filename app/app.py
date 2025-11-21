from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.api import v1_router
from app.database import Database
from app.loggin import logger, attach_db_handler

tags_metadata = [
    {
        "name": "upload",
        "description": "Operação de inserir os documentos para o banco vetorial",
    },
]

attach_db_handler(Database.get_instance().get_session)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await logger.start_db_handler()
    yield

app = FastAPI(
        title="Async File Processing RAG API",
        description="API para processamento de documentos para preparação para RAG",
        version="alpha 0.0",
        openapi_tags=tags_metadata      
              )

app.include_router(v1_router, prefix='/api/v1')