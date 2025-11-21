import logging
from .database_handler import DatabaseHandler

class Logger:
    """Logger unificado com console, arquivo e handler de banco opcional."""

    def __init__(self, nome_arquivo='app.log', nivel=logging.DEBUG):
        self.logger = logging.getLogger("LoggerUnificado")
        self.logger.setLevel(nivel)

        if not self.logger.handlers:
            # Formatação padrão
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

            # Console
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

            # Arquivo
            file_handler = logging.FileHandler(nome_arquivo)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        self.db_handler = None

    def attach_db_handler(self, session_factory, fallback_file='log_fallback.jsonl'):
        """Adiciona handler de banco de dados (chamar após DB inicializado)"""
        if self.db_handler is None:
            self.db_handler = DatabaseHandler(session_factory, fallback_file=fallback_file)
            self.logger.addHandler(self.db_handler)

    async def start_db_handler(self):
        """Inicia o worker assíncrono do handler de banco, se existir"""
        if self.db_handler is not None:
            await self.db_handler.start()

    # Métodos de conveniência
    def debug(self, msg, **kwargs):
        self.logger.debug(msg, extra=kwargs)

    def info(self, msg, **kwargs):
        self.logger.info(msg, extra=kwargs)

    def warning(self, msg, **kwargs):
        self.logger.warning(msg, extra=kwargs)

    def error(self, msg, **kwargs):
        self.logger.error(msg, extra=kwargs)

    def critical(self, msg, **kwargs):
        self.logger.critical(msg, extra=kwargs)

    def exception(self, msg, **kwargs):
        self.logger.exception(msg, extra=kwargs)