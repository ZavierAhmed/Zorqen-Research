#!/usr/bin/env bash
# Wait for PostgreSQL readiness (used by local Docker workflows).
set -euo pipefail

HOST="${1:-127.0.0.1}"
PORT="${2:-5432}"
RETRIES="${3:-30}"

echo "Waiting for PostgreSQL at ${HOST}:${PORT} ..."
for i in $(seq 1 "${RETRIES}"); do
  if (echo >"/dev/tcp/${HOST}/${PORT}") >/dev/null 2>&1; then
    echo "PostgreSQL port is open."
    exit 0
  fi
  sleep 1
done

echo "Timed out waiting for PostgreSQL." >&2
exit 1
