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
    }