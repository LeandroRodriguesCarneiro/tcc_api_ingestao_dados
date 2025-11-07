from ...kafka import KafkaConsumer
import json
from workers import PDFWorker, DOCXWorker, TXTWorker

class DocumentConsumer:
    def __init__(self, kafka_bootstrap_servers: str):
        self.consumer = KafkaConsumer(
            "document_ingestion",
            bootstrap_servers=kafka_bootstrap_servers,
            group_id="document_workers",
            auto_offset_reset="earliest"
        )

    def start(self):
        print("🚀 Worker iniciado e ouvindo Kafka...")
        for msg in self.consumer:
            data = json.loads(msg.value)
            mime = data["mime_type"]

            if mime == "application/pdf":
                PDFWorker().process(data)
            elif mime in ["application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
                DOCXWorker().process(data)
            elif mime.startswith("text/"):
                TXTWorker().process(data)
            else:
                print(f"⚠️ Tipo não suportado: {mime}")
