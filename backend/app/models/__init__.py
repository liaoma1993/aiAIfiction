import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, func
from app.database import Base


def uuid_pk():
    return str(uuid.uuid4())


class BaseModel(Base):
    __abstract__ = True

    id = Column(String(36), primary_key=True, default=uuid_pk)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.id}>"
