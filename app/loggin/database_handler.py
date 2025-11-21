import logging
import json
import threading
import time
from sqlalchemy.exc import SQLAlchemyError
from ..models import LogModel
from ..repositories import LogRepository

class DatabaseHandler(logging.Handler):
    """Handler síncrono com fallback e flush automático."""

    def __init__(self, session_factory, fallback_file='log_fallback.jsonl', flush_interval=60):
        super().__init__()
        self.session_factory = session_factory
        self.fallback_file = fallback_file
        self.flush_interval = flush_interval
        self._stop_event = threading.Event()
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()

    def emit(self, record: logging.LogRecord):
        try:
            session = self.session_factory()
            repo = LogRepository(session)
            log_entry = LogModel(
                level=record.levelname,
                message=record.getMessage(),
                module=record.module,
                lineno=record.lineno,
                operation=record.funcName,
                status=getattr(record, "status", 1)
            )
            repo.add(log_entry)
            session.close()
        except SQLAlchemyError as e:
            self._write_to_file(record)
            print(f"[DBLogHandler Fallback] Erro ao salvar log: {e}")

    def _write_to_file(self, record: logging.LogRecord):
        log_dict = {
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "lineno": record.lineno,
            "operation": record.funcName,
            "status": getattr(record, "status", 1),
        }
        with open(self.fallback_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_dict) + '\n')

    def flush_fallback_logs(self):
        try:
            with open(self.fallback_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if not lines:
                return

            remaining = []
            session = self.session_factory()
            repo = LogRepository(session)

            for line in lines:
                try:
                    log_dict = json.loads(line)
                    log_entry = LogModel(**log_dict)
                    repo.add(log_entry)
                except Exception:
                    remaining.append(line)

            session.close()

            with open(self.fallback_file, 'w', encoding='utf-8') as f:
                f.writelines(remaining)

        except FileNotFoundError:
            pass

    def _flush_loop(self):
        """Thread que roda o flush automático periodicamente."""
        while not self._stop_event.is_set():
            self.flush_fallback_logs()
            self._stop_event.wait(self.flush_interval)

    def close(self):
        self._stop_event.set()
        self._flush_thread.join()
        super().close()
