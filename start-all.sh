#!/bin/bash
# ============================================
# QA Agent 一键启动脚本（除 Docker 外）
# 用法: bash start-all.sh
# 前提: Docker 已启动 (Qdrant + MinIO)
# ============================================

set -e

# 项目根目录
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOGS_DIR="$ROOT_DIR/logs"
mkdir -p "$LOGS_DIR"

# 端口配置
PYTHON_PORT=8000
AUTH_PORT=8080
DOC_PORT=8081
CHAT_PORT=8082
AUDIT_PORT=8083
FRONTEND_PORT=5173

# PID 跟踪
PIDS=()

cleanup() {
    echo ""
    echo "正在停止所有服务..."
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            wait "$pid" 2>/dev/null
        fi
    done
    # 清理残留子进程
    jobs -p | xargs -r kill 2>/dev/null
    echo "所有服务已停止。"
    exit 0
}
trap cleanup INT TERM

# 辅助函数: 检查端口是否就绪
check_port() {
    local port=$1
    local path=$2
    curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 "http://localhost:$port$path" 2>/dev/null | grep -q "200\|401\|404\|405" && return 0
    return 1
}

# 辅助函数: 等待端口就绪
wait_for_port() {
    local port=$1
    local name=$2
    local path=${3:-/}
    local timeout=${4:-120}
    local elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if check_port "$port" "$path"; then
            echo "  [$name] ✓ 就绪 (端口 $port)"
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    echo "  [$name] ✗ 超时 (端口 $port) — 查看 $LOGS_DIR/${name}.log"
    return 1
}

echo ""
echo "========================================"
echo "  QA Agent 一键启动"
echo "  项目目录: $ROOT_DIR"
echo "========================================"
echo ""

# ---- 1. Python AI 服务 ----
echo "[1/5] 启动 Python AI 服务 (端口 $PYTHON_PORT)..."
cd "$ROOT_DIR/python"
poetry run uvicorn api.main:app --host 0.0.0.0 --port $PYTHON_PORT \
    > "$LOGS_DIR/python.log" 2>&1 &
PIDS+=($!)
cd "$ROOT_DIR"

# ---- 2. Java Auth ----
echo "[2/5] 启动 Java Auth (端口 $AUTH_PORT)..."
cd "$ROOT_DIR/java"
mvn -pl auth spring-boot:run -q \
    > "$LOGS_DIR/auth.log" 2>&1 &
PIDS+=($!)
cd "$ROOT_DIR"
sleep 4

# ---- 3. Java Document ----
echo "[3/5] 启动 Java Document (端口 $DOC_PORT)..."
cd "$ROOT_DIR/java"
mvn -pl document spring-boot:run -q \
    > "$LOGS_DIR/document.log" 2>&1 &
PIDS+=($!)
cd "$ROOT_DIR"
sleep 4

# ---- 4. Java Chat ----
echo "[4/5] 启动 Java Chat (端口 $CHAT_PORT)..."
cd "$ROOT_DIR/java"
mvn -pl chat spring-boot:run -q \
    > "$LOGS_DIR/chat.log" 2>&1 &
PIDS+=($!)
cd "$ROOT_DIR"
sleep 4

# ---- 5. Java Audit + Frontend ----
echo "[5/5] 启动 Java Audit (端口 $AUDIT_PORT) + 前端 (端口 $FRONTEND_PORT)..."
cd "$ROOT_DIR/java"
mvn -pl audit spring-boot:run -q \
    > "$LOGS_DIR/audit.log" 2>&1 &
PIDS+=($!)
cd "$ROOT_DIR"
sleep 4

cd "$ROOT_DIR/java/frontend"
npm run dev \
    > "$LOGS_DIR/frontend.log" 2>&1 &
PIDS+=($!)
cd "$ROOT_DIR"

echo ""
echo "等待所有服务就绪..."
echo ""

# ---- 健康检查 ----
wait_for_port $PYTHON_PORT "python" "/api/agent/health"
wait_for_port $AUTH_PORT "auth" "/api/auth/login"
wait_for_port $DOC_PORT "document" "/api/documents"
wait_for_port $CHAT_PORT "chat" "/api/chat/stream"
wait_for_port $AUDIT_PORT "audit" "/api/audit/logs"
wait_for_port $FRONTEND_PORT "frontend" "/"

echo ""
echo "========================================"
echo "  所有服务启动完成！"
echo "========================================"
echo ""
echo "  前端界面:   http://localhost:$FRONTEND_PORT"
echo "  Python AI:  http://localhost:$PYTHON_PORT/docs"
echo "  Auth API:   http://localhost:$AUTH_PORT"
echo "  Document:   http://localhost:$DOC_PORT"
echo "  Chat:       http://localhost:$CHAT_PORT"
echo "  Audit:      http://localhost:$AUDIT_PORT"
echo ""
echo "  日志目录: $LOGS_DIR"
echo "  按 Ctrl+C 停止所有服务"
echo ""

# 等待任意子进程退出或 Ctrl+C
wait
