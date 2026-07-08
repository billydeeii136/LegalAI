#!/usr/bin/env bash
set -u
set -o pipefail

BRANCH="${1:-harvey-elite-2026}"
REPO_LOCAL="${REPO_LOCAL:-/Users/billydeeii136/WSD_CCOS/repos/wsd-ccos-legal}"
RUNTIME_DIR="${RUNTIME_DIR:-/Users/billydeeii136/LegalAI/.harvey/runtime}"
BUNDLE_LOCAL="${BUNDLE_LOCAL:-$RUNTIME_DIR/wsd-ccos-legal.bundle}"
REMOTE_URL="${REMOTE_URL:-https://github.com/billydeeii136/wsd-ccos-legal.git}"
TERMUX_REPO_DIR="${TERMUX_REPO_DIR:-/data/data/com.termux/files/home/legal/wsd-ccos-legal}"
TERMUX_CONFIRM_PATH="${TERMUX_CONFIRM_PATH:-/data/data/com.termux/files/home/.legal-sync/node_confirmation.txt}"
TERMUX_SYNC_SCRIPT="${TERMUX_SYNC_SCRIPT:-/data/data/com.termux/files/home/bin/termux_legal_sync.sh}"
TERMUX_BOOT_SCRIPT="${TERMUX_BOOT_SCRIPT:-/data/data/com.termux/files/home/.termux/boot/legal-sync-boot.sh}"
TMP_REMOTE_BUNDLE="/data/local/tmp/wsd-ccos-legal.bundle"

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

fail() {
  log "ERROR: $*"
  exit 1
}

command -v git >/dev/null 2>&1 || fail "git is required"
command -v adb >/dev/null 2>&1 || fail "adb is required"
[ -d "$REPO_LOCAL/.git" ] || fail "local repo not found: $REPO_LOCAL"

mkdir -p "$RUNTIME_DIR"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_TSV="$RUNTIME_DIR/push_legal_bundle_report_$TS.tsv"
REPORT_LOG="$RUNTIME_DIR/push_legal_bundle_report_$TS.log"

log "creating git bundle from $REPO_LOCAL"
(
  cd "$REPO_LOCAL" || exit 1
  git --no-pager bundle create "$BUNDLE_LOCAL" --all
) || fail "failed to create bundle"

mapfile -t DEVICES < <(adb devices | awk 'NR>1 && $2=="device" {print $1}')

printf "serial\tdeploy_status\trepo_git\tbranch\tsync_script\tboot_script\tconfirmation_path\n" > "$REPORT_TSV"
: > "$REPORT_LOG"

if [ "${#DEVICES[@]}" -eq 0 ]; then
  printf "none\tno_device\tno\tmissing\tno\tno\t%s\n" "$TERMUX_CONFIRM_PATH" >> "$REPORT_TSV"
  log "no connected adb devices detected"
  log "report saved: $REPORT_TSV"
  cat "$REPORT_TSV"
  exit 0
fi

for serial in "${DEVICES[@]}"; do
  log "deploying bundle to $serial"

  if ! adb -s "$serial" push "$BUNDLE_LOCAL" "$TMP_REMOTE_BUNDLE" >/dev/null 2>&1; then
    printf "%s\tpush_bundle_failed\tno\tmissing\tno\tno\t%s\n" "$serial" "$TERMUX_CONFIRM_PATH" >> "$REPORT_TSV"
    continue
  fi

  DEPLOY_OUTPUT="$(
    adb -s "$serial" shell "run-as com.termux sh -lc 'export PATH=/data/data/com.termux/files/usr/bin:\$PATH; mkdir -p /data/data/com.termux/files/home/legal /data/data/com.termux/files/home/.legal-sync; rm -rf \"$TERMUX_REPO_DIR\"; if ! git clone \"$TMP_REMOTE_BUNDLE\" \"$TERMUX_REPO_DIR\" >/dev/null 2>&1; then echo deploy_status=clone_failed; exit 21; fi; if git -C \"$TERMUX_REPO_DIR\" show-ref --verify --quiet \"refs/heads/$BRANCH\"; then git -C \"$TERMUX_REPO_DIR\" checkout \"$BRANCH\" >/dev/null 2>&1 || exit 22; elif git -C \"$TERMUX_REPO_DIR\" show-ref --verify --quiet \"refs/remotes/origin/$BRANCH\"; then git -C \"$TERMUX_REPO_DIR\" checkout -b \"$BRANCH\" \"origin/$BRANCH\" >/dev/null 2>&1 || exit 23; else git -C \"$TERMUX_REPO_DIR\" checkout -b \"$BRANCH\" >/dev/null 2>&1 || exit 24; fi; git -C \"$TERMUX_REPO_DIR\" remote set-url origin \"$REMOTE_URL\" >/dev/null 2>&1 || true; BRANCH_NOW=\$(git -C \"$TERMUX_REPO_DIR\" rev-parse --abbrev-ref HEAD 2>/dev/null || echo missing); REPO_GIT=no; [ -d \"$TERMUX_REPO_DIR/.git\" ] && REPO_GIT=yes; SYNC_OK=no; [ -x \"$TERMUX_SYNC_SCRIPT\" ] && SYNC_OK=yes; BOOT_OK=no; [ -x \"$TERMUX_BOOT_SCRIPT\" ] && BOOT_OK=yes; printf \"timestamp_utc=%s\nserial=%s\ndeploy_status=%s\nsync_script=%s\nboot_script=%s\nrepo_git=%s\nbranch=%s\nrepo_path=%s\n\" \"\$(date -u +%Y-%m-%dT%H:%M:%SZ)\" \"$serial\" \"ok\" \"\$SYNC_OK\" \"\$BOOT_OK\" \"\$REPO_GIT\" \"\$BRANCH_NOW\" \"$TERMUX_REPO_DIR\" > \"$TERMUX_CONFIRM_PATH\"; cat \"$TERMUX_CONFIRM_PATH\"'" 2>&1 || true
  )"

  printf "===== %s =====\n%s\n" "$serial" "$DEPLOY_OUTPUT" >> "$REPORT_LOG"

  deploy_status="$(printf '%s\n' "$DEPLOY_OUTPUT" | awk -F= '/^deploy_status=/{print $2}' | tail -n 1)"
  repo_git="$(printf '%s\n' "$DEPLOY_OUTPUT" | awk -F= '/^repo_git=/{print $2}' | tail -n 1)"
  branch_now="$(printf '%s\n' "$DEPLOY_OUTPUT" | awk -F= '/^branch=/{print $2}' | tail -n 1)"
  sync_ok="$(printf '%s\n' "$DEPLOY_OUTPUT" | awk -F= '/^sync_script=/{print $2}' | tail -n 1)"
  boot_ok="$(printf '%s\n' "$DEPLOY_OUTPUT" | awk -F= '/^boot_script=/{print $2}' | tail -n 1)"

  [ -n "$deploy_status" ] || deploy_status="deploy_output_missing"
  [ -n "$repo_git" ] || repo_git="no"
  [ -n "$branch_now" ] || branch_now="missing"
  [ -n "$sync_ok" ] || sync_ok="no"
  [ -n "$boot_ok" ] || boot_ok="no"

  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$serial" "$deploy_status" "$repo_git" "$branch_now" "$sync_ok" "$boot_ok" "$TERMUX_CONFIRM_PATH" >> "$REPORT_TSV"
done

log "report saved: $REPORT_TSV"
log "log saved: $REPORT_LOG"
cat "$REPORT_TSV"
