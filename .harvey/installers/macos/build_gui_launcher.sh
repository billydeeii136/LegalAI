#!/usr/bin/env bash
set -euo pipefail

TARGETS_FILE=""
OUTPUT_DIR=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --targets)
      TARGETS_FILE="${2:-}"
      shift 2
      ;;
    --output)
      OUTPUT_DIR="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [ -z "$TARGETS_FILE" ] || [ -z "$OUTPUT_DIR" ]; then
  echo "Usage: $0 --targets <DEPLOYMENT_TARGETS.yaml> --output <dir>" >&2
  exit 2
fi

mkdir -p "${OUTPUT_DIR}"

cat > "${OUTPUT_DIR}/LAUNCH_GUI.command" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
echo "Launching Harvey GUI workflow on macOS..."
echo "TODO: replace with packaged app launch + profile bootstrap."
EOF
chmod +x "${OUTPUT_DIR}/LAUNCH_GUI.command"

cat > "${OUTPUT_DIR}/README.txt" <<EOF
Generated from: ${TARGETS_FILE}
Artifact: macOS GUI launcher template
EOF

echo "Built macOS GUI launcher template at ${OUTPUT_DIR}"
