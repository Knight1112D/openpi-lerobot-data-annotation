#!/usr/bin/env bash
set -euo pipefail

# 在项目主目录创建并安装本项目环境。
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
UV_INDEX_URL="https://mirrors.aliyun.com/pypi/simple/"

if [[ ! -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
  uv venv "${PROJECT_ROOT}/.venv" --python "${PYTHON_BIN}"
fi

uv pip install \
  --python "${PROJECT_ROOT}/.venv/bin/python" \
  --index-url "${UV_INDEX_URL}" \
  "pyarrow>=15.0"

echo "环境已就绪：${PROJECT_ROOT}/.venv"
