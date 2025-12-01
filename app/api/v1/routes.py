from fastapi import APIRouter, status

from .controllers.index_document_controller import IndexDocumentController

router = APIRouter()

indec_document_controller= IndexDocumentController()

router.include_router(
    indec_document_controller.router,
    prefix='/Documents',
    tags=['V1', 'Documents']
    )

@router.get(
    '/health', 
    tags=['V1'],
    status_code=status.HTTP_200_OK,
    summary="Verificar se a API está online",
    description="Verificar se a API está online e operando",
    responses={
        200: {"description": "ok"}
    }
)
def health():
    return {"status": "ok"}