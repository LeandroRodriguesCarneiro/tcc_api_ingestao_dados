import time
from confluent_kafka.admin import AdminClient, NewTopic
from app.settings import Settings
from app.loggin import logger

def ensure_topics(max_retries: int = 5, retry_delay: int = 5):
    """
    Garante que todos os tópicos essenciais existam no cluster Kafka.
    Reexecuta em caso de falhas (Kafka ainda subindo).
    """
    for attempt in range(1, max_retries + 1):
        try:
            admin = AdminClient({"bootstrap.servers": Settings.KAFKA_BOOTSTRAP_SERVERS})
            cluster_metadata = admin.list_topics(timeout=10)
            existing_topics = set(cluster_metadata.topics.keys())

            new_topics = []
            for topic_name, conf in Settings.TOPICS.items():
                if topic_name in existing_topics:
                    continue

                num_partitions = conf.get("num_partitions", 1)
                replication_factor = conf.get("replication_factor", 1)
                config = conf.get("config", {})

                new_topics.append(
                    NewTopic(
                        topic=topic_name,
                        num_partitions=num_partitions,
                        replication_factor=replication_factor,
                        config=config
                    )
                )

            if not new_topics:
                logger.info("✅ Nenhum novo tópico para criar. Todos já existem.")
                return

            logger.info(f"🧩 Criando {len(new_topics)} novo(s) tópico(s)...")
            futures = admin.create_topics(new_topics)

            for topic, future in futures.items():
                try:
                    future.result()
                    logger.info(f"✅ Tópico criado: {topic}")
                except Exception as e:
                    # Se o erro indicar que o tópico já existe, só loga como aviso
                    if 'TopicAlreadyExistsError' in str(e):
                        logger.warning(f"⚠️ Tópico {topic} já existe.")
                    else:
                        logger.error(f"❌ Erro ao criar tópico {topic}: {e}")

            logger.info("🎯 Criação de tópicos finalizada.")
            return

        except Exception as e:
            logger.warning(f"⏳ Tentativa {attempt}/{max_retries} falhou: {e}")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                logger.error("❌ Não foi possível garantir os tópicos após múltiplas tentativas.")
                raise