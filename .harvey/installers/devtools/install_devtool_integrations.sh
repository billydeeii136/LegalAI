#!/usr/bin/env bash
set -euo pipefail

HARVEY_ROOT=""
OUTPUT_DIR=""
APPLY_WORKSPACE=1
APPLY_CODEX_PROFILE=1

while [ "$#" -gt 0 ]; do
  case "$1" in
    --harvey-root)
      HARVEY_ROOT="${2:-}"
      shift 2
      ;;
    --output)
      OUTPUT_DIR="${2:-}"
      shift 2
      ;;
    --no-apply-workspace)
      APPLY_WORKSPACE=0
      shift
      ;;
    --no-apply-codex-profile)
      APPLY_CODEX_PROFILE=0
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [ -z "${HARVEY_ROOT}" ]; then
  HARVEY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fi

if [ -z "${OUTPUT_DIR}" ]; then
  OUTPUT_DIR="${HARVEY_ROOT}/runtime/devtools"
fi

WORKSPACE_ROOT="$(cd "${HARVEY_ROOT}/.." && pwd)"

mkdir -p "${OUTPUT_DIR}/warp" "${OUTPUT_DIR}/vscode" "${OUTPUT_DIR}/codex" "${OUTPUT_DIR}/chatgpt" "${OUTPUT_DIR}/xcode"

cp "${HARVEY_ROOT}/MCP_SERVER_CONFIG.example.json" "${OUTPUT_DIR}/warp/harvey-mcp.json"
cp "${HARVEY_ROOT}/integrations/warp/oz_mcp_commands.sh" "${OUTPUT_DIR}/warp/oz_mcp_commands.sh"
chmod +x "${OUTPUT_DIR}/warp/oz_mcp_commands.sh"

cp "${HARVEY_ROOT}/integrations/vscode/extensions.json" "${OUTPUT_DIR}/vscode/extensions.json"
cp "${HARVEY_ROOT}/integrations/vscode/settings.json" "${OUTPUT_DIR}/vscode/settings.json"

cp "${HARVEY_ROOT}/integrations/codex/config.toml" "${OUTPUT_DIR}/codex/harvey-legal.config.toml"
cp "${HARVEY_ROOT}/integrations/chatgpt/responses_mcp_tools.example.json" \
  "${OUTPUT_DIR}/chatgpt/responses_mcp_tools.example.json"
cp "${HARVEY_ROOT}/integrations/xcode/HARVEY_LEGAL_ASSISTANT.xcconfig" \
  "${OUTPUT_DIR}/xcode/HARVEY_LEGAL_ASSISTANT.xcconfig"

if [ "${APPLY_WORKSPACE}" = "1" ]; then
  mkdir -p "${WORKSPACE_ROOT}/.vscode"
  cp "${HARVEY_ROOT}/integrations/vscode/extensions.json" "${WORKSPACE_ROOT}/.vscode/extensions.json"
  cp "${HARVEY_ROOT}/integrations/vscode/settings.json" "${WORKSPACE_ROOT}/.vscode/settings.json"
fi

if [ "${APPLY_CODEX_PROFILE}" = "1" ]; then
  mkdir -p "${HOME}/.codex"
  cp "${HARVEY_ROOT}/integrations/codex/config.toml" "${HOME}/.codex/harvey-legal.config.toml"
fi

cat > "${OUTPUT_DIR}/INSTALL_SUMMARY.txt" <<EOF
Generated devtool integration artifacts at: ${OUTPUT_DIR}
Workspace applied: ${APPLY_WORKSPACE}
Codex profile applied: ${APPLY_CODEX_PROFILE}

Installed/packaged:
- Warp MCP config + launch helpers
- VS Code and GitHub Copilot workspace settings
- Codex MCP profile template
- ChatGPT Responses API MCP tool template
- Xcode assistant xcconfig template

Next steps:
1) Fill provider keys in .harvey/LEGAL_RESEARCH.env
2) Fill retained counsel roster in .harvey/LICENSED_COUNSEL_ROSTER_TEMPLATE.yaml
3) Start MCP server: node .harvey/mcp/legal-connectors-mcp/server.js
4) For Warp CLI runs: use .harvey/integrations/warp/oz_mcp_commands.sh
EOF

echo "Devtool integration install complete: ${OUTPUT_DIR}"
