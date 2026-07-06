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
if [ -z "${PACER_USERNAME:-}" ] && [ -n "${PACER_KEYCHAIN_ACCOUNT:-}" ]; then
  PACER_USERNAME="${PACER_KEYCHAIN_ACCOUNT}"
fi

if [ -z "${PACER_PASSWORD:-}" ] && [ -n "${PACER_KEYCHAIN_SERVICE:-}" ] && command -v security >/dev/null 2>&1; then
  PACER_PASSWORD="$(security find-generic-password -s "${PACER_KEYCHAIN_SERVICE}" -a "${PACER_KEYCHAIN_ACCOUNT:-${PACER_USERNAME:-}}" -w 2>/dev/null || true)"
fi

python3 "${ROOT_DIR}/scripts/pacer_login_template.py" \
  --watchlist "${ROOT_DIR}/LEGAL_CASE_WATCHLIST.yaml" \
  --session-out "${RUNTIME_DIR}/pacer_session.json" \
  --state-out "${RUNTIME_DIR}/pacer_storage_state.json" \
  --mode "${PACER_LOGIN_MODE:-auto}" \
  --mfa-timeout-seconds "${PACER_MFA_TIMEOUT_SECONDS:-300}"

DRIVE_ANCHOR_MAX_FILES="${DRIVE_ANCHOR_MAX_FILES:-2000}" \
DRIVE_ANCHOR_MAX_DEPTH="${DRIVE_ANCHOR_MAX_DEPTH:-1}" \
python3 "${ROOT_DIR}/scripts/discover_drive_case_anchors.py" || true

python3 "${ROOT_DIR}/scripts/pacer_case_sync.py" \
  --watchlist "${ROOT_DIR}/LEGAL_CASE_WATCHLIST.yaml" \
  --session-in "${RUNTIME_DIR}/pacer_session.json" \
  --report-out "${RUNTIME_DIR}/pacer_case_sync_report.json" \
  --identity-anchors "${ROOT_DIR}/LEGAL_IDENTITY_ANCHORS.yaml" \
  --drive-discovered "${ROOT_DIR}/DRIVE_DISCOVERED_CASE_ANCHORS.json"

if [ "${START_MCP_SERVER:-0}" = "1" ]; then
  (
    cd "${ROOT_DIR}/mcp/legal-connectors-mcp"
    npm install
    node server.js
  )
fi

bash "${ROOT_DIR}/sync_harvey.sh" "${1:-harvey-elite-2026}"
