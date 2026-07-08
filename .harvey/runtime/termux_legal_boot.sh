#!/data/data/com.termux/files/usr/bin/bash
TERMUX_HOME="/data/data/com.termux/files/home"
export HOME="$TERMUX_HOME"
SYNC_SCRIPT="$HOME/bin/termux_legal_sync.sh"
BOOT_LOG="$HOME/.legal-sync/boot.log"

mkdir -p "$HOME/.legal-sync"
{
  echo "[boot] $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if [ -x "$SYNC_SCRIPT" ]; then
    "$SYNC_SCRIPT"
  else
    echo "[error] missing sync script: $SYNC_SCRIPT"
  fi
} >> "$BOOT_LOG" 2>&1
