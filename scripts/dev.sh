#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$ROOT_DIR/.pids"
BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"
LOG_DIR="$ROOT_DIR/logs"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

# 确保目录存在
mkdir -p "$PID_DIR" "$LOG_DIR"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_status() {
    echo -e "${BLUE}[STATUS]${NC} $1"
}

# 检查进程是否运行
is_running() {
    local pid_file=$1
    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$pid_file"
            return 1
        fi
    fi
    return 1
}

# 启动后端
start_backend() {
    if is_running "$BACKEND_PID_FILE"; then
        log_warn "后端已经在运行中 (PID: $(cat $BACKEND_PID_FILE))"
        return 0
    fi

    log_info "启动后端服务..."
    cd "$ROOT_DIR/backend"

    # 检查并创建虚拟环境
    if [[ ! -d ".venv" ]]; then
        log_info "创建 Python 虚拟环境..."
        python3 -m venv .venv
    fi

    source .venv/bin/activate

    # 检查依赖
    if ! python3 -c "import uvicorn" 2>/dev/null; then
        log_info "安装后端依赖..."
        pip install -q -r requirements.txt
    fi

    # 启动服务
    nohup python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001 \
        > "$BACKEND_LOG" 2>&1 &

    local pid=$!
    echo $pid > "$BACKEND_PID_FILE"

    # 等待服务启动
    sleep 2
    if is_running "$BACKEND_PID_FILE"; then
        log_info "后端服务启动成功 (PID: $pid)"
        log_info "后端地址: http://127.0.0.1:8001"
        log_info "日志文件: $BACKEND_LOG"
        return 0
    else
        log_error "后端服务启动失败，请查看日志: $BACKEND_LOG"
        return 1
    fi
}

# 启动前端
start_frontend() {
    if is_running "$FRONTEND_PID_FILE"; then
        log_warn "前端已经在运行中 (PID: $(cat $FRONTEND_PID_FILE))"
        return 0
    fi

    log_info "启动前端服务..."
    cd "$ROOT_DIR/frontend"

    # 检查依赖
    if [[ ! -d "node_modules" ]]; then
        log_info "安装前端依赖..."
        npm install
    fi

    # 启动服务
    nohup npm run dev -- --host 127.0.0.1 \
        > "$FRONTEND_LOG" 2>&1 &

    local pid=$!
    echo $pid > "$FRONTEND_PID_FILE"

    # 等待服务启动
    sleep 3
    if is_running "$FRONTEND_PID_FILE"; then
        log_info "前端服务启动成功 (PID: $pid)"
        log_info "前端地址: http://127.0.0.1:5173"
        log_info "日志文件: $FRONTEND_LOG"
        return 0
    else
        log_error "前端服务启动失败，请查看日志: $FRONTEND_LOG"
        return 1
    fi
}

# 停止后端
stop_backend() {
    if is_running "$BACKEND_PID_FILE"; then
        local pid=$(cat "$BACKEND_PID_FILE")
        log_info "停止后端服务 (PID: $pid)..."
        kill "$pid" 2>/dev/null || true
        sleep 1

        # 如果还在运行，强制杀掉
        if ps -p "$pid" > /dev/null 2>&1; then
            log_warn "强制停止后端服务..."
            kill -9 "$pid" 2>/dev/null || true
        fi

        rm -f "$BACKEND_PID_FILE"
        log_info "后端服务已停止"
    else
        log_warn "后端服务未运行"
    fi
}

# 停止前端
stop_frontend() {
    if is_running "$FRONTEND_PID_FILE"; then
        local pid=$(cat "$FRONTEND_PID_FILE")
        log_info "停止前端服务 (PID: $pid)..."
        kill "$pid" 2>/dev/null || true
        sleep 1

        # 如果还在运行，强制杀掉
        if ps -p "$pid" > /dev/null 2>&1; then
            log_warn "强制停止前端服务..."
            kill -9 "$pid" 2>/dev/null || true
        fi

        rm -f "$FRONTEND_PID_FILE"
        log_info "前端服务已停止"
    else
        log_warn "前端服务未运行"
    fi
}

# 启动所有服务
start_all() {
    echo ""
    log_info "========== 启动 AI Fiction Studio =========="
    start_backend
    echo ""
    start_frontend
    echo ""
    log_info "============================================"
    echo ""
    show_status
}

# 停止所有服务
stop_all() {
    echo ""
    log_info "========== 停止 AI Fiction Studio =========="
    stop_backend
    echo ""
    stop_frontend
    echo ""
    log_info "============================================"
}

# 重启所有服务
restart_all() {
    stop_all
    sleep 1
    start_all
}

# 查看状态
show_status() {
    echo ""
    log_status "========== 服务状态 =========="

    # 后端状态
    if is_running "$BACKEND_PID_FILE"; then
        local pid=$(cat "$BACKEND_PID_FILE")
        echo -e "${GREEN}✓${NC} 后端服务运行中 (PID: $pid)"
        echo "  地址: http://127.0.0.1:8001"
        echo "  日志: $BACKEND_LOG"
    else
        echo -e "${RED}✗${NC} 后端服务未运行"
    fi

    echo ""

    # 前端状态
    if is_running "$FRONTEND_PID_FILE"; then
        local pid=$(cat "$FRONTEND_PID_FILE")
        echo -e "${GREEN}✓${NC} 前端服务运行中 (PID: $pid)"
        echo "  地址: http://127.0.0.1:5173"
        echo "  日志: $FRONTEND_LOG"
    else
        echo -e "${RED}✗${NC} 前端服务未运行"
    fi

    echo ""
    log_status "============================="
    echo ""
}

# 查看日志
show_logs() {
    local service=${1:-all}

    case $service in
        backend)
            log_info "查看后端日志 (Ctrl+C 退出):"
            tail -f "$BACKEND_LOG"
            ;;
        frontend)
            log_info "查看前端日志 (Ctrl+C 退出):"
            tail -f "$FRONTEND_LOG"
            ;;
        all|*)
            log_info "查看所有日志 (Ctrl+C 退出):"
            tail -f "$BACKEND_LOG" "$FRONTEND_LOG"
            ;;
    esac
}

# 显示帮助
show_help() {
    cat << EOF

AI Fiction Studio 开发服务管理脚本

用法:
    $0 [命令]

命令:
    start           启动所有服务（后端 + 前端）
    stop            停止所有服务
    restart         重启所有服务
    status          查看服务状态
    logs [service]  查看日志 (service可选: all|backend|frontend，默认all)

单独管理:
    start-backend   仅启动后端
    start-frontend  仅启动前端
    stop-backend    仅停止后端
    stop-frontend   仅停止前端

其他:
    help            显示此帮助信息

示例:
    $0 start        # 启动所有服务
    $0 stop         # 停止所有服务
    $0 restart      # 重启所有服务
    $0 status       # 查看状态
    $0 logs         # 查看所有日志
    $0 logs backend # 仅查看后端日志

EOF
}

# 主逻辑
main() {
    local command=${1:-start}

    case $command in
        start)
            start_all
            ;;
        stop)
            stop_all
            ;;
        restart)
            restart_all
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "${2:-all}"
            ;;
        start-backend)
            start_backend
            ;;
        start-frontend)
            start_frontend
            ;;
        stop-backend)
            stop_backend
            ;;
        stop-frontend)
            stop_frontend
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
