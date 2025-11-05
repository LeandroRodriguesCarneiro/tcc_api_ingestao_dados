from sqlalchemy import Column, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
import uuid

Base = declarative_base()

class TaskManagerModel(Base):
    __tablename__ = "task_manager"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    document_name = Column(Text, nullable=False)
    document_path = Column(Text, nullable=False)
    document_status = Column(Text, default="pending", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
