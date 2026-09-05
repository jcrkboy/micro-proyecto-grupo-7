#!/usr/bin/env bash

set -Eeuo pipefail

API_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${API_DIR}/../.." && pwd)"

if [[ -n "${PYTHON_BIN:-}" ]]; then
  PYTHON_EXECUTABLE="${PYTHON_BIN}"
elif [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  PYTHON_EXECUTABLE="${REPO_ROOT}/.venv/bin/python"
elif [[ -x "${REPO_ROOT}/.venv/Scripts/python.exe" ]]; then
  PYTHON_EXECUTABLE="${REPO_ROOT}/.venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_EXECUTABLE="$(command -v python3)"
else
  echo "Error: no se encontró Python. Cree .venv o defina PYTHON_BIN." >&2
  exit 1
fi

export PYTHONPATH="${REPO_ROOT}/apps/api/src:${REPO_ROOT}/packages/sleep-staging/src${PYTHONPATH:+:${PYTHONPATH}}"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8080}"
RELOAD="${RELOAD:-true}"
DEBUG="${DEBUG:-false}"
DEBUG_HOST="${DEBUG_HOST:-127.0.0.1}"
DEBUG_PORT="${DEBUG_PORT:-5678}"
DEBUG_WAIT="${DEBUG_WAIT:-false}"

UVICORN_ARGS=(
  -m uvicorn
  sleep_api.main:app
  --host "${HOST}"
  --port "${PORT}"
)

if [[ "${RELOAD}" == "true" ]]; then
  UVICORN_ARGS+=(--reload)
fi

if [[ "${DEBUG}" == "true" ]]; then
  if ! "${PYTHON_EXECUTABLE}" -c "import debugpy" >/dev/null 2>&1; then
    echo 'Error: debugpy no está instalado. Ejecute: pip install -e "./apps/api[dev]"' >&2
    exit 1
  fi

  DEBUG_ARGS=(-m debugpy --listen "${DEBUG_HOST}:${DEBUG_PORT}")
  if [[ "${DEBUG_WAIT}" == "true" ]]; then
    DEBUG_ARGS+=(--wait-for-client)
  fi
  echo "API en http://${HOST}:${PORT}; depurador en ${DEBUG_HOST}:${DEBUG_PORT}"
  exec "${PYTHON_EXECUTABLE}" "${DEBUG_ARGS[@]}" "${UVICORN_ARGS[@]}" "$@"
fi

echo "API en http://${HOST}:${PORT}"
exec "${PYTHON_EXECUTABLE}" "${UVICORN_ARGS[@]}" "$@"
