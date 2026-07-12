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

wait_for_backend_ready() {
  local url="http://127.0.0.1:8000/api/health"
  local max_attempts=90
  local attempt=1

  if ! command -v curl >/dev/null 2>&1; then
    sleep 2
    return
  fi

  while (( attempt <= max_attempts )); do
    if ! kill -0 "${BACKEND_PID}" 2>/dev/null; then
      echo "[error] Backend wurde waehrend des Starts beendet."
      wait "${BACKEND_PID}" || true
      exit 1
    fi

    if curl --silent --fail "${url}" >/dev/null 2>&1; then
      return
    fi

    if (( attempt == 1 )); then
      echo "[wait] Backend initialisiert noch. Warte auf ${url} ..."
    fi

    sleep 1
    attempt=$((attempt + 1))
  done

  echo "[error] Backend antwortet nach ${max_attempts} Sekunden noch nicht auf ${url}."
  echo "[hint] Pruefe die Backend-Ausgabe. Moeglicherweise haengt die Python-Umgebung beim Import."
  exit 1
}

ensure_port_is_free() {
  local port="$1"
  local service_name="$2"

  if ! command -v lsof >/dev/null 2>&1; then
    return
  fi

  local listeners
  listeners="$(lsof -n -P -iTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -z "${listeners}" ]]; then
    return
  fi

  echo "[error] Port ${port} ist bereits belegt. ${service_name} kann nicht gestartet werden."
  echo "[hint] Beende zuerst den bestehenden Listener auf Port ${port}:"
  echo "${listeners}"
  echo "[hint] Beispiel: kill <PID>"
  exit 1
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

ensure_port_is_free 8000 "Backend"
ensure_port_is_free 5173 "Frontend"

echo "[start] Backend auf http://127.0.0.1:8000"
(
  cd "${BACKEND_DIR}"
  exec "${BACKEND_PYTHON}" -m uvicorn main:app --host 127.0.0.1 --port 8000
) &
BACKEND_PID=$!

wait_for_backend_ready

echo "[start] Frontend auf http://127.0.0.1:5173"
(
  cd "${ROOT_DIR}"
  exec npm run dev:frontend
) &
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
