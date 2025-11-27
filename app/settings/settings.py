import os
from dotenv import load_dotenv

load_dotenv()

class Settings():
    DB_USER = os.getenv("DB_USER")
    DB_PSW = os.getenv("DB_PSW")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_DATABASE = os.getenv("DB_DATABASE")
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    URL_API_AUTH = os.getenv("URL_API_AUTH")
    
    VECTOR_DB_CREDENTIALS_PROVIDER = os.getenv("CHROMA_SERVER_AUTH_CREDENTIALS_PROVIDER")
    VECTOR_DB_CREDENTIALS = os.getenv("CHROMA_SERVER_AUTH_CREDENTIALS")
    VECTOR_DB_PROVIDER = os.getenv("CHROMA_SERVER_AUTH_PROVIDER")
    VECTOR_DB_AUTH_TOKEN_TRANSPORT_HEADER = os.getenv("CHROMA_AUTH_TOKEN_TRANSPORT_HEADER")
    DB_VECTOR_HOST = os.getenv("DB_VECTOR_HOST")
    DB_VECTOR_PORT = os.getenv("DB_VECTOR_PORT")

    MIME_TYPES_PERMITIDOS = [
        'application/pdf',
        'text/plain',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/html',
        'text/markdown',
        'text/x-markdown',
        'application/x-markdown'
    ]

    TOPICS = {
        "document_ingestion.init": {
            "num_partitions": 3,
            "replication_factor": 1,
            "config": {
                "retention.ms": "604800000",
                "cleanup.policy": "delete",
                "min.insync.replicas": "1"
            }
        },
        "document_ingestion.deleted": {
            "num_partitions": 3,
            "replication_factor": 1,
            "config": {
                "retention.ms": "604800000",
                "cleanup.policy": "delete",
                "min.insync.replicas": "1"
            }
        },
        "document_ingestion.pdf_processing": {
            "num_partitions": 3,
            "replication_factor": 1,
            "config": {
                "retention.ms": "604800000",
                "cleanup.policy": "delete",
                "min.insync.replicas": "1"
            }
        },
        "document_ingestion.docx_processing": {
            "num_partitions": 3,
            "replication_factor": 1,
            "config": {
                "retention.ms": "604800000",
                "cleanup.policy": "delete",
                "min.insync.replicas": "1"
            }
        },
        "document_ingestion.text_processing": {
            "num_partitions": 3,
            "replication_factor": 1,
            "config": {
                "retention.ms": "604800000",
                "cleanup.policy": "delete",
                "min.insync.replicas": "1"
            }
        },
    }