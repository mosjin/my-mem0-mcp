#!/usr/bin/bash

# 用法说明
# 运行本脚本以启动 mem0-mcp 服务
# 确保已创建 Python 虚拟环境并安装依赖
# Windows 用户请使用 Git Bash 或 WSL 运行本脚本

# 设置错误时退出
set -e

# 检查虚拟环境是否存在
if [ ! -d ".venv" ]; then
  echo "[错误] 未找到 .venv 虚拟环境目录，请先创建虚拟环境。"
  echo "例如: python -m venv .venv 或者 uv venv"
  exit 1
fi

# 检查增强版客户端文件是否存在
if [ ! -f "enhanced_mem0_client.py" ]; then
  echo "[错误] 未找到 enhanced_mem0_client.py 文件，请确保该文件存在。"
  exit 1
fi

# 激活虚拟环境
echo "[信息] 正在激活虚拟环境..."
source .venv/Scripts/activate
if [ $? -ne 0 ]; then
  echo "[错误] 虚拟环境激活失败，请检查 .venv/Scripts/activate 路径。"
  exit 1
fi

echo "[信息] 虚拟环境已激活"
echo "[信息] 检查Python版本..."
python --version

echo "[信息] 检查依赖包..."
python -c "import httpx, mem0, mcp; print('所有依赖包已安装')" || {
  echo "[错误] 依赖包检查失败，请运行: uv pip install -e ."
  exit 1
}

echo "[信息] 开始启动增强版 mem0-mcp 服务..."
echo "[信息] 服务将运行在 http://0.0.0.0:8080/sse"
echo "[信息] 按 Ctrl+C 停止服务"

# 实时输出 main.py 的内容，并设置环境变量
export PYTHONUNBUFFERED=1
export MEM0_TIMEOUT=600
export MEM0_WRITE_TIMEOUT=300
export MEM0_MAX_RETRIES=5

uv run python -u main.py --host 0.0.0.0 --port 8080

# 退出提示
if [ $? -eq 0 ]; then
  echo "[完成] mem0-mcp 服务正常退出。"
else
  echo "[警告] mem0-mcp 服务异常退出，请检查错误信息。"
fi
