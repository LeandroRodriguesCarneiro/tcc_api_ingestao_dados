import asyncio
import json
import random
from abc import ABC, abstractmethod
from confluent_kafka import Consumer, Producer, KafkaError

from ...settings import Settings
from ...loggin import logger
from ...database import Database

MAX_RETRIES = 5
RETRY_DELAY = 2

class KafkaWorker(ABC):
    def __init__(self, topic: str, group_id: str, dlq_topic: str = None):
        self.topic = topic
        self.group_id = group_id
        self.dlq_topic = dlq_topic
        self.producer = None
        self.consumer = None

    @abstractmethod
    async def process_message(self, data: dict, session=None):
        """Implementado por cada worker específico."""
        pass

    async def handle_message(self, msg, session):
        """Processa com retry + idempotência"""
        try:
            data = json.loads(msg.value().decode("utf-8"))
        except json.JSONDecodeError:
            logger.error("❌ Mensagem inválida")
            return None, False

        job_id = data.get("document_id")

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                await self.process_message(data, session)
                return job_id, True 

            except Exception as e:
                error_msg = str(e).lower()
                
                if any(skip_word in error_msg for skip_word in [
                    "arquivo não encontrado", "file not found", "não existe", "já processado",
                    "ausente/processado"
                ]):
                    logger.info(f"⚠️ Idempotente: {job_id} - {e}")
                    return job_id, True
                
                logger.error(f"❌ Tentativa {attempt}/{MAX_RETRIES}: {e}")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY * attempt + random.random())
                else:
                    logger.error(f"💥 {job_id} falhou definitivamente (sem DLQ)")
                    raise

        return job_id, False

    def _dlq_callback(self, err, msg):
        if err:
            logger.error(f"❌ Erro ao enviar para DLQ: {err}")

    async def _process_with_session(self, msg):
        """Processa mensagem de forma totalmente sequencial e determinística."""
        db = Database.get_instance()
        session = db.get_session()

        try:
            job_id, success = await self.handle_message(msg, session)

            if success:
                session.commit()
                self.consumer.commit(msg)
                logger.info(f"✅ Job {job_id} processado e commitado.")
            else:
                session.rollback()
                logger.error(f"💥 Job {job_id} falhou após retries, enviando para DLQ.")

                if self.dlq_topic and self.producer:
                    self.producer.produce(
                        self.dlq_topic,
                        msg.value(),
                        callback=self._dlq_callback
                    )
                    self.producer.flush()

        except Exception as e:
            session.rollback()
            logger.error(f"💥 Erro inesperado no processamento: {e}")

        finally:
            session.close()

    async def start(self):
        logger.info(f"🚀 Iniciando worker determinístico para o tópico '{self.topic}'")

        self.consumer = Consumer({
            "bootstrap.servers": Settings.KAFKA_BOOTSTRAP_SERVERS,
            "group.id": self.group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            "max.poll.interval.ms": 900000,
        })

        if self.dlq_topic:
            self.producer = Producer({
                "bootstrap.servers": Settings.KAFKA_BOOTSTRAP_SERVERS
            })

        try:
            self.consumer.subscribe([self.topic])

            while True:
                msg = self.consumer.poll(1.0)

                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() != KafkaError._PARTITION_EOF:
                        logger.error(f"Kafka error: {msg.error()}")
                    continue

                await self._process_with_session(msg)

        except KeyboardInterrupt:
            logger.info("🛑 Worker interrompido manualmente.")

        finally:
            logger.info("👋 Encerrando consumer Kafka.")
            self.consumer.close()
