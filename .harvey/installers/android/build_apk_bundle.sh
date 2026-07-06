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

cat > "${OUTPUT_DIR}/APK_BUILD_PLAN.txt" <<EOF
Generated from: ${TARGETS_FILE}
Artifact: Android APK installer template
Targets:
- galaxy_a15_primary
- galaxy_a15_secondary
- galaxy_a17
TODO: connect Gradle/CI signer + APK/AAB publishing flow.
EOF

cat > "${OUTPUT_DIR}/INSTALL_ANDROID.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
echo "Preparing Android APK installation workflow..."
echo "TODO: replace with adb install / MDM deployment orchestration."
EOF
chmod +x "${OUTPUT_DIR}/INSTALL_ANDROID.sh"

echo "Built Android APK bundle template at ${OUTPUT_DIR}"
