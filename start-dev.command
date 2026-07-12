#!/usr/bin/env bash

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${ROOT_DIR}" || exit 1

./start-dev.sh
STATUS=$?

echo
read -r -p "Druecke Enter zum Schliessen..."
exit "${STATUS}"
