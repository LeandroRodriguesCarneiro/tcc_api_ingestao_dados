import logging
from .logger import Logger

logger = Logger(nivel=logging.INFO)

def attach_db_handler(session_factory=None, fallback_file='log_fallback.jsonl'):
    """
    Anexa o handler do banco de dados ao logger global.
    Deve ser chamado após o banco estar inicializado.
    """
    if session_factory:
        logger.attach_db_handler(session_factory, fallback_file=fallback_file)