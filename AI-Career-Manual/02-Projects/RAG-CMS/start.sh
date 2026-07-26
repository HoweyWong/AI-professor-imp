#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_dir"

if [[ ! -f .venv/bin/activate ]]; then
  echo "未找到 .venv。请先执行：python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

source .venv/bin/activate

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
else
  echo "提示：未找到 .env；健康检查和文档上传可用，问答接口将返回 503。" >&2
fi

exec python -m uvicorn app.main:app --reload "$@"
