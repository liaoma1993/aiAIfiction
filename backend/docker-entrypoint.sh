#!/bin/sh
# ============================================================
# AI Fiction - 生产环境 Docker 启动脚本
# 功能：
#   1. 自动执行数据库迁移（alembic upgrade head）
#   2. 以 exec 方式启动 uvicorn（确保信号正确传递给子进程）
# ============================================================
set -e

echo "==> 正在执行数据库迁移..."
alembic upgrade head
echo "==> 数据库迁移完成"

# exec 替换当前 shell 进程，使 uvicorn 成为 PID 1
# CMD 参数（如 --workers 4）会作为 $@ 传入
echo "==> 启动 Uvicorn..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --proxy-headers \
    --forwarded-allow-ips='*' \
    "$@"
