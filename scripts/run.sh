#!/usr/bin/env bash
set -euo pipefail

# 使用项目内虚拟环境运行数据标注入口。
# Run the annotation entrypoint with the project-local virtual environment.
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ ! -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
  echo "未找到项目环境，请先执行：bash scripts/bootstrap.sh" >&2
  exit 1
fi

exec "${PROJECT_ROOT}/.venv/bin/python" \
  "${PROJECT_ROOT}/scripts/data_annotation.py" "$@"
