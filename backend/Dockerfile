# ============================================================
# AI Fiction - FastAPI 后端 Dockerfile
# 多阶段构建：开发阶段支持热重载，生产阶段优化镜像体积与安全性
# ============================================================

# ---------- 构建阶段：安装系统依赖 + Python 依赖 ----------
FROM python:3.12-slim AS build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv

# 将 venv 加入 PATH，后续所有 pip/uvicorn 命令自动使用虚拟环境
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# 安装编译依赖（asyncpg 需要 libpq-dev + build-essential）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python -m venv $VIRTUAL_ENV

# 安装 Python 依赖到虚拟环境
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用源代码
COPY . .

# ---------- 开发阶段 ----------
FROM build AS development

# 安装开发工具
RUN pip install --no-cache-dir debugpy watchdog

# 开发模式启动（支持热重载，启动前自动执行数据库迁移）
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]

# ---------- 生产运行阶段 ----------
FROM python:3.12-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv

ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app

# 仅安装运行时依赖（libpq-dev 是 asyncpg 的运行时依赖）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户，加强容器安全性
RUN groupadd -r aifiction -g 1000 && \
    useradd -r -g aifiction -u 1000 -d /app -s /sbin/nologin aifiction && \
    mkdir -p /app && \
    chown -R aifiction:aifiction /app

# 从构建阶段复制虚拟环境（避免生产阶段重复 pip install）
COPY --from=build /opt/venv /opt/venv

# 复制应用源代码
COPY --from=build --chown=aifiction:aifiction /app /app

# 为 ENTRYPOINT 脚本添加可执行权限
RUN chmod +x /app/docker-entrypoint.sh

# 切换到非 root 用户运行
USER aifiction

EXPOSE 8000

# 健康检查：每 30 秒检测一次应用健康端点
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# ENTRYPOINT 脚本自动执行数据库迁移，然后 exec uvicorn（保证信号正确传递）
# CMD 提供默认参数，可在 docker compose 或 run 命令中覆盖
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["--workers", "4"]
