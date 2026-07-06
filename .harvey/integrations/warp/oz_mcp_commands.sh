#!/usr/bin/env bash
set -euo pipefail

MCP_FILE="${1:-.harvey/MCP_SERVER_CONFIG.example.json}"
PROMPT="${2:-Show configured legal providers and run legal_research_mode_status.}"

oz agent run --mcp "${MCP_FILE}" --prompt "${PROMPT}"
