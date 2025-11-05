from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine.url import make_url
from threading import Lock
from ..models import Base
from ..settings import Settings


class Database:
    _instance = None
    _lock = Lock()

    def __init__(self, override_url: str = None):
        if Database._instance is not None:
            raise Exception("Use Database.get_instance()")

        self.database_url = override_url or (
            f"postgresql://{Settings.DB_USER}:{Settings.DB_PSW}@"
            f"{Settings.DB_HOST}:{Settings.DB_PORT}/{Settings.DB_DATABASE}"
        )

        url_obj = make_url(self.database_url)
        backend = url_obj.get_backend_name()
        is_sqlite = backend == "sqlite"

        engine_args = {
            "echo": False, 
        }

        if not is_sqlite:
            engine_args.update({
                "pool_size": 5,
                "max_overflow": 0,
                "pool_timeout": 30,
                "pool_recycle": 1800,
            })
        else:
            if self.database_url == "sqlite:///:memory:":
                engine_args["connect_args"] = {"check_same_thread": False}

        self.engine = create_engine(self.database_url, **engine_args)

        Base.metadata.create_all(self.engine)

        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            autocommit=False,
            autoflush=False
        )

        Database._instance = self

    @staticmethod
    def get_instance(override_url: str = None):
        with Database._lock:
            if not Database._instance:
                Database(override_url)
        return Database._instance

    @staticmethod
    def reset_instance():
        Database._instance = None

    def get_session(self) -> Session:
        return self.session_factory()

    @staticmethod
    def get_db():
        """Gerador para frameworks como FastAPI"""
        db = Database.get_instance()
        session = db.get_session()
        try:
            yield session
        finally:
            session.close()