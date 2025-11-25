import logging
from .database_handler import DatabaseHandler

class Logger:
    _instance = None  # 👈 Singleton

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
        return cls._instance

    def __init__(self, nome_arquivo='app.log', nivel=logging.DEBUG):
        if hasattr(self, "_initialized") and self._initialized:
            return

        self.logger = logging.getLogger("LoggerUnificado")
        self.logger.setLevel(nivel)
        self.logger.propagate = False  # ESSENCIAL

        self._disable_docling_logs()

        if not self.logger.handlers:
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

            file_handler = logging.FileHandler(nome_arquivo)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        self.db_handler = None
        self._initialized = True

    def _disable_docling_logs(self):
        docling_loggers = [
            "docling", "docling.accelerator", "docling.converter",
            "docling.pdf", "docling.pipeline",
        ]
        for name in docling_loggers:
            log = logging.getLogger(name)
            log.propagate = False
            log.disabled = True
            log.handlers.clear()
            log.setLevel(logging.CRITICAL)
            
    def attach_db_handler(self, session_factory, fallback_file='log_fallback.jsonl'):
        if self.db_handler is None:
            self.db_handler = DatabaseHandler(session_factory, fallback_file=fallback_file)
            self.logger.addHandler(self.db_handler)

    # Delegadores
    def debug(self, msg, **k): self.logger.debug(msg, extra=k)
    def info(self, msg, **k): self.logger.info(msg, extra=k)
    def warning(self, msg, **k): self.logger.warning(msg, extra=k)
    def error(self, msg, **k): self.logger.error(msg, extra=k)
    def critical(self, msg, **k): self.logger.critical(msg, extra=k)
    def exception(self, msg, **k): self.logger.exception(msg, extra=k)
