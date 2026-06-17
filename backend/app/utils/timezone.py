"""统一的时区处理工具。

本系统面向中文用户，全局统一使用东八区（Asia/Shanghai）本地时间。
SQLite 存的、后端读的、序列化给前端的全部是带时区的东八区时间，
避免 naive datetime 在前后端转换时出现 8 小时偏差。

注意：旧数据可能是 naive UTC，_ensure_local 会兜底按 UTC 解释再转东八区。
"""
from datetime import datetime, timezone, timedelta

# 东八区
CN_TZ = timezone(timedelta(hours=8))


def now() -> datetime:
    """当前东八区时间（带时区）。"""
    return datetime.now(CN_TZ)


def ensure_local(value: datetime | None) -> datetime | None:
    """把任意 datetime 规整为带时区的东八区时间。
    - None → None
    - naive（旧数据，视为 UTC）→ 加 UTC 后转东八区
    - 带时区 → 转东八区
    """
    if value is None:
        return None
    if value.tzinfo is None:
        # 旧数据无时区，按 UTC 解释（SQLite func.now() 默认存 UTC）
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(CN_TZ)


def isoformat(value: datetime | None) -> str:
    """序列化为带东八区时区的 ISO 字符串（前端可直接 new Date() 解释为本地时间）。
    None → 空字符串。
    """
    local = ensure_local(value)
    if local is None:
        return ""
    return local.isoformat()
