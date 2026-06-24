from datetime import datetime, timedelta, timezone
from jose import jwt
import bcrypt
from app.config import get_settings

# 直接使用 bcrypt，避免 passlib 1.7.4 与 bcrypt 4.x 在 Python 3.13 上的兼容问题
_BCRYPT_MAX = 72  # bcrypt 单次最多处理 72 字节


def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:_BCRYPT_MAX]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        pw = plain.encode("utf-8")[:_BCRYPT_MAX]
        return bcrypt.checkpw(pw, hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: str) -> str:
    settings = get_settings()
    # 用带时区的 UTC 时间（utcnow 已废弃），python-jose 会正确转为 exp timestamp
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
