#!/usr/bin/env bash
set -euo pipefail

TARGETS_FILE=""
OUTPUT_ROOT=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --targets)
      TARGETS_FILE="${2:-}"
      shift 2
      ;;
    --output-root)
      OUTPUT_ROOT="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [ -z "$TARGETS_FILE" ] || [ -z "$OUTPUT_ROOT" ]; then
  echo "Usage: $0 --targets <DEPLOYMENT_TARGETS.yaml> --output-root <dir>" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "${OUTPUT_ROOT}"

bash "${SCRIPT_DIR}/macos/build_cli_bundle.sh" --targets "${TARGETS_FILE}" --output "${OUTPUT_ROOT}/macos-cli"
bash "${SCRIPT_DIR}/macos/build_gui_launcher.sh" --targets "${TARGETS_FILE}" --output "${OUTPUT_ROOT}/macos-gui"
bash "${SCRIPT_DIR}/android/build_apk_bundle.sh" --targets "${TARGETS_FILE}" --output "${OUTPUT_ROOT}/android-apk"
bash "${SCRIPT_DIR}/devtools/install_devtool_integrations.sh" \
  --harvey-root "$(cd "${SCRIPT_DIR}/.." && pwd)" \
  --output "${OUTPUT_ROOT}/devtools" \
  --no-apply-workspace \
  --no-apply-codex-profile

echo "Installer pipeline complete: ${OUTPUT_ROOT}"
