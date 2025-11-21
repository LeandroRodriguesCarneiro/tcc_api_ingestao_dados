from sqlalchemy import (
    Column, Integer, Text, DateTime, func
)

from .base_model import Base

class LogModel(Base):
    __tablename__ = "log"

    id = Column(Integer, primary_key=True)
    level = Column(Text)
    message = Column(Text)
    module = Column(Text)
    lineno = Column(Integer)
    operation = Column(Text)
    status = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())