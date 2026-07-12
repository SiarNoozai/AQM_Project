#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
BACKEND_PYTHON="${BACKEND_DIR}/.venv/bin/python"

cleanup() {
  if [[ -n "${FRONTEND_PID:-}" ]] && kill -0 "${FRONTEND_PID}" 2>/dev/null; then
    kill "${FRONTEND_PID}" 2>/dev/null || true
  fi
  if [[ -n "${BACKEND_PID:-}" ]] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
    kill "${BACKEND_PID}" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

cd "${ROOT_DIR}"

if [[ ! -d "${ROOT_DIR}/node_modules" ]]; then
  echo "[setup] node_modules fehlen. Fuehre npm install aus..."
  npm install
fi

if [[ ! -x "${BACKEND_PYTHON}" ]]; then
  if command -v uv >/dev/null 2>&1; then
    echo "[setup] Backend-Venv fehlt. Fuehre uv sync aus..."
    (
      cd "${BACKEND_DIR}"
      uv sync
    )
  else
    echo "[error] Backend-Venv fehlt und 'uv' ist nicht installiert."
    echo "[hint] Installiere uv mit: python3 -m pip install uv"
    exit 1
  fi
fi

echo "[start] Backend auf http://127.0.0.1:8000"
(
  cd "${BACKEND_DIR}"
  exec "${BACKEND_PYTHON}" -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
) > >(sed 's/^/[backend] /') 2> >(sed 's/^/[backend] /' >&2) &
BACKEND_PID=$!

sleep 2

if ! kill -0 "${BACKEND_PID}" 2>/dev/null; then
  echo "[error] Backend konnte nicht gestartet werden."
  wait "${BACKEND_PID}" || true
  exit 1
fi

echo "[start] Frontend auf http://127.0.0.1:5173"
(
  cd "${ROOT_DIR}"
  exec npm run dev:frontend
) > >(sed 's/^/[frontend] /') 2> >(sed 's/^/[frontend] /' >&2) &
FRONTEND_PID=$!

echo "[ready] Anwendung startet. Mit Ctrl + C beendest du Frontend und Backend zusammen."

while true; do
  if ! kill -0 "${BACKEND_PID}" 2>/dev/null; then
    echo "[error] Backend wurde beendet."
    wait "${BACKEND_PID}" || true
    exit 1
  fi

  if ! kill -0 "${FRONTEND_PID}" 2>/dev/null; then
    wait "${FRONTEND_PID}"
    exit $?
  fi

  sleep 1
done
