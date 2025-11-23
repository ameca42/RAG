#!/bin/bash

# HN RAG 小红书风格应用启动脚本
# 同时启动 FastAPI 后端和 React 前端

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 启动 HN RAG 小红书风格应用..."
echo ""

# 检查数据目录
if [ ! -d "data" ]; then
    mkdir -p data
fi

# 检查是否有文章数据
if [ ! -f "data/articles.json" ]; then
    echo "⚠️  警告: 没有文章数据，请先运行爬虫:"
    echo "   venv/bin/python -m app.crawler.crawler -n 30"
    echo ""
fi

# 启动后端
echo "📦 启动 FastAPI 后端 (端口 8000)..."
venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "   后端 PID: $BACKEND_PID"

# 等待后端启动
sleep 3

# 启动前端
echo ""
echo "🎨 启动 React 前端 (端口 5173)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
echo "   前端 PID: $FRONTEND_PID"

cd ..

echo ""
echo "✅ 应用已启动!"
echo ""
echo "📍 访问地址:"
echo "   - 前端界面: http://localhost:5173"
echo "   - 后端 API: http://localhost:8000"
echo "   - API 文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服务..."

# 捕获退出信号，清理进程
cleanup() {
    echo ""
    echo "🛑 正在停止服务..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo "服务已停止"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 等待任意进程退出
wait
