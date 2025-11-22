#!/bin/bash

# Hacker News RAG 应用启动脚本

echo "🚀 启动 Hacker News RAG 应用..."

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行: python -m venv venv"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "⚠️  .env 文件不存在，请配置环境变量"
    echo "参考 .env.example 创建 .env 文件"
    exit 1
fi

# 创建必要的目录
mkdir -p data/chromadb
mkdir -p logs

echo "✅ 环境检查完成"

# 启动 FastAPI 后端（后台运行）
echo "🔧 启动 FastAPI 后端 (http://localhost:8000)..."
venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 启动 Streamlit 前端
echo "🎨 启动 Streamlit 前端 (http://localhost:8501)..."
venv/bin/streamlit run ui/streamlit_app.py

# 清理：当 Streamlit 退出时，关闭后端
echo "🛑 关闭应用..."
kill $BACKEND_PID 2>/dev/null

echo "✅ 应用已关闭"
