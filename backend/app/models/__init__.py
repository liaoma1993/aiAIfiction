import uuid
from sqlalchemy import Column, String, DateTime
from app.database import Base
from app.utils.timezone import now as tz_now


def uuid_pk():
    return str(uuid.uuid4())


class BaseModel(Base):
    __abstract__ = True

    id = Column(String(36), primary_key=True, default=uuid_pk)
    # 用 Python 端默认值生成东八区时间，避免 SQLite func.now() 返回 UTC 导致前后端时区偏差
    created_at = Column(DateTime(timezone=True), default=tz_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=tz_now, onupdate=tz_now, nullable=False)

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.id}>"
