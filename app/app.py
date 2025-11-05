from fastapi import FastAPI
from app.controllers import AuthController

tags_metadata = [
    {
        "name": "upload",
        "description": "Operação de inserir os documentos para o banco vetorial",
    },
]

app = FastAPI(
        title="Async File Processing RAG API",
        description="API para processamento de documentos para preparação para RAG",
        version="alpha 0.0",
        openapi_tags=tags_metadata      
              )
app.include_router(AuthController.router)