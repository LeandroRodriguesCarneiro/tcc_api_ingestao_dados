import chromadb
from chromadb.config import Settings

from ..settings import Settings as Env

class VectorDataBase:
    def __init__(self):
        settings = Settings(
            chroma_client_auth_provider=Env.VECTOR_DB_CREDENTIALS_PROVIDER,
            chroma_client_auth_credentials=Env.VECTOR_DB_CREDENTIALS,
            chroma_auth_token_transport_header=Env.VECTOR_DB_AUTH_TOKEN_TRANSPORT_HEADER
        )

        self.client = chromadb.HttpClient(
            host=Env.DB_VECTOR_HOST,
            port=Env.DB_VECTOR_PORT,
            ssl=False,
            settings=settings
        )

    def test_conection(self):
        print("Heartbeat:", self.client.heartbeat())
        print("Collections:", self.client.list_collections())


    def index_document(self):
        pass

    def delete_document(self):
        pass

    def semantic_search(self):
        pass