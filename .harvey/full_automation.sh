#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="${ROOT_DIR}/runtime"
mkdir -p "${RUNTIME_DIR}"

if [ -f "${ROOT_DIR}/PACER.env" ]; then
  set -a
  . "${ROOT_DIR}/PACER.env"
  set +a
fi

if [ -f "${ROOT_DIR}/LEGAL_RESEARCH.env" ]; then
  set -a
  . "${ROOT_DIR}/LEGAL_RESEARCH.env"
  set +a
fi

python3 "${ROOT_DIR}/scripts/pacer_login_template.py" \
  --watchlist "${ROOT_DIR}/LEGAL_CASE_WATCHLIST.yaml" \
  --session-out "${RUNTIME_DIR}/pacer_session.json"

if [ "${START_MCP_SERVER:-0}" = "1" ]; then
  (
    cd "${ROOT_DIR}/mcp/legal-connectors-mcp"
    npm install
    node server.js
  )
fi

bash "${ROOT_DIR}/sync_harvey.sh" "${1:-harvey-elite-2026}"
