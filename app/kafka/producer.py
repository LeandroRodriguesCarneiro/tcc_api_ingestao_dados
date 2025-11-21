import json
from pathlib import Path
from confluent_kafka import Producer

from ..settings import Settings
from ..loggin import logger

class KafkaProducer:
    """Classe responsável por enviar mensagens JSON para o Kafka."""

    def __init__(self, broker_url: str = None):
        self.broker_url = broker_url or Settings.KAFKA_BOOTSTRAP_SERVERS
        self.producer = Producer({'bootstrap.servers': self.broker_url})
        logger.info(f"🚀 KafkaProducer conectado em {self.broker_url}")

    def _delivery_report(self, err, msg):
        if err:
            logger.error(f'❌ Erro ao entregar mensagem: {err}')
        else:
            logger.info(f'✅ Mensagem entregue em {msg.topic()} [{msg.partition()}]')

    def send(self, topic: str, value: dict):
        """Envia apenas mensagens JSON para o Kafka."""
        if not isinstance(value, dict):
            raise TypeError(f"Tipo de dado não suportado: {type(value)}. Use dict apenas.")

        try:
            data = json.dumps(value).encode('utf-8')
            logger.info(f"📤 Enviando mensagem JSON ({len(data)} bytes) para o tópico '{topic}'")
            self.producer.produce(topic, value=data, callback=self._delivery_report)
            self.producer.flush()
        except Exception as e:
            logger.error(f"⚠️ Erro ao enviar mensagem JSON para o Kafka: {e}")