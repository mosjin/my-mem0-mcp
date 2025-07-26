#!/usr/bin/bash

# 用法说明
# 运行本脚本以启动 mem0-mcp 服务
# 确保已创建 Python 虚拟环境并安装依赖
# Windows 用户请使用 Git Bash 或 WSL 运行本脚本

# 检查虚拟环境是否存在
if [ ! -d ".venv" ]; then
  echo "[错误] 未找到 .venv 虚拟环境目录，请先创建虚拟环境。"
  echo "例如: python -m venv .venv 或者 uv venv"
  exit 1
fi

# 激活虚拟环境
source .venv/Scripts/activate
if [ $? -ne 0 ]; then
  echo "[错误] 虚拟环境激活失败，请检查 .venv/Scripts/activate 路径。"
  exit 1
fi

echo "[提示] 虚拟环境已激活，开始运行 main.py ..."

# 实时输出 main.py 的内容
uv run python -u main.py

# 退出提示
if [ $? -eq 0 ]; then
  echo "[完成] main.py 正常退出。"
else
  echo "[警告] main.py 运行异常退出，请检查错误信息。"
fi
