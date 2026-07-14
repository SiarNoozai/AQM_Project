"""Minimaler .env-Loader ohne Zusatzabhaengigkeiten.

Laedt Umgebungsvariablen aus `.env` (Repo-Root) und `backend/.env`,
ohne bereits gesetzte Variablen zu ueberschreiben.
"""

from __future__ import annotations

import os
from pathlib import Path


def load_env_files() -> None:
    backend_dir = Path(__file__).resolve().parent
    candidates = [backend_dir.parent / ".env", backend_dir / ".env"]
    for env_file in candidates:
        try:
            if not env_file.is_file():
                continue
            for raw_line in env_file.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
        except Exception:
            continue
