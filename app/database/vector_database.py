import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any

from ..settings import Settings as Env

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

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

        self.collection = self.client.get_or_create_collection(
            "documents",
            embedding_function=None  # IMPORTANTE
        )

    def add_document(self, chunks_with_metadata: List[Dict[str, Any]]):
        ids = []
        documents = []
        metadatas = []

        for idx, chunk in enumerate(chunks_with_metadata):
            chunk_id = f"{chunk['document_id']}_{idx+1}"
            ids.append(chunk_id)
            documents.append(chunk["text"])
            meta = {k: v for k, v in chunk.items() if k != "text"}
            metadatas.append(meta)

        embeddings = model.encode(documents, convert_to_numpy=True).tolist()

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings
        )

    def delete_document(self, document_name: str):
        self.collection.delete(where={"document_name": {"$eq": document_name}})

    def semantic_search(self, query_text: str, n_results: int = 5) -> List[Dict[str, Any]]:
        query_embedding = model.encode([query_text]).tolist()

        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )

        matches = []
        for doc, meta, dist in zip(results['documents'][0], results['metadatas'][0], results['distances'][0]):
            matches.append({
                "document": doc,
                "metadata": meta,
                "distance": dist
            })
        return matches
