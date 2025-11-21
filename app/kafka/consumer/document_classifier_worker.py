import json
from .kafka_worker import KafkaWorker
from ...loggin import logger
from ...repositories import TaskManagerRepository
from ..producer import KafkaProducer


class DocumentClassifierWorker(KafkaWorker):
    def __init__(self):
        super().__init__(
            topic="document_ingestion.init",
            group_id="document_spliter_group"
        )
        self.producer = KafkaProducer()

    async def process_message(self, data: dict, session=None):
        logger.info("📥 Recebendo documento para split...")

        mime = data.get("mime_type")
        doc_name = data.get("document_name")
        job_id = data.get("document_id")

        repo = TaskManagerRepository(session)

        task = repo.get_by_id(job_id)
        if not task:
            logger.error(f"❌ JobID {job_id} não encontrado no banco!")
            return

        logger.info(
            f"🔍 MIME: {mime} | Documento: '{doc_name}' | JobID: {job_id}"
        )

        if mime == "application/pdf":
            topic = "document_ingestion.pdf_processing"
            new_status = "Splitter"

        elif mime in [
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ]:
            topic = "document_ingestion.docx_processing"
            new_status = "Splitter"

        elif mime.startswith("text/") or mime in [
            "text/markdown", 
            "application/x-markdown"
        ]:
            topic = "document_ingestion.text_processing"
            new_status = "Extracting"

        else:
            logger.warning(f"⚠️ Tipo de arquivo não suportado: {mime}")
            return

        logger.info(f"➡ Redirecionando documento para o tópico '{topic}'")

        try:
            logger.info(
                f"📤 Enviando '{doc_name}' para o tópico '{topic}'..."
            )

            self.producer.send(topic, data)

            logger.info(
                f"✅ Documento '{doc_name}' enviado com sucesso para '{topic}'"
            )

            logger.info(
                f"📝 Atualizando status do JobID {job_id} para {new_status}"
            )

            task.document_status = new_status
            repo.update(task)

        except Exception as e:
            logger.error(
                f"❌ Erro ao enviar documento ou atualizar status do Job {job_id}: {e}"
            )
            raise
