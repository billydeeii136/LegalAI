#!/data/data/com.termux/files/usr/bin/bash
TERMUX_HOME="/data/data/com.termux/files/home"
TERMUX_PREFIX="/data/data/com.termux/files/usr"
export HOME="$TERMUX_HOME"
export PREFIX="$TERMUX_PREFIX"
export PATH="$TERMUX_PREFIX/bin:$PATH"

REPO_URL="${LEGAL_REPO_URL:-https://github.com/billydeeii136/wsd-ccos-legal.git}"
BRANCH="${LEGAL_REPO_BRANCH:-harvey-elite-2026}"
REPO_DIR="${LEGAL_REPO_DIR:-$HOME/legal/wsd-ccos-legal}"
BUNDLE_PATH="${LEGAL_BUNDLE_PATH:-/data/local/tmp/wsd-ccos-legal.bundle}"
LOG_DIR="$HOME/.legal-sync/logs"
LOG_FILE="$LOG_DIR/sync-$(date +%Y%m%d-%H%M%S).log"
STATUS_FILE="$HOME/.legal-sync/last_sync_status.env"

mkdir -p "$LOG_DIR" "$(dirname "$REPO_DIR")"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "[start] $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "[repo] $REPO_URL"
echo "[branch] $BRANCH"
echo "[target] $REPO_DIR"
echo "[bundle] $BUNDLE_PATH"

if ! command -v git >/dev/null 2>&1; then
  echo "[info] git not found, attempting install via pkg"
  if command -v pkg >/dev/null 2>&1; then
    pkg update -y || true
    pkg install -y git openssh ca-certificates curl || true
  fi
fi

if ! command -v git >/dev/null 2>&1; then
  echo "[error] git still unavailable; cannot sync repository"
  exit 1
fi

clone_source="none"
if [ -d "$REPO_DIR/.git" ]; then
  echo "[info] repo exists, refreshing"
  git -C "$REPO_DIR" remote set-url origin "$REPO_URL" || true
  git -C "$REPO_DIR" fetch --all --prune || true
else
  if [ -f "$BUNDLE_PATH" ]; then
    echo "[info] cloning from local bundle"
    git clone "$BUNDLE_PATH" "$REPO_DIR" && clone_source="bundle"
  fi
  if [ ! -d "$REPO_DIR/.git" ]; then
    echo "[info] cloning from remote URL"
    git clone --branch "$BRANCH" --single-branch "$REPO_URL" "$REPO_DIR" || git clone "$REPO_URL" "$REPO_DIR"
    clone_source="remote"
  fi
fi

if [ -d "$REPO_DIR/.git" ]; then
  if git -C "$REPO_DIR" ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
    remote_check="ok"
    git -C "$REPO_DIR" checkout "$BRANCH" || git -C "$REPO_DIR" checkout -b "$BRANCH" "origin/$BRANCH"
    git -C "$REPO_DIR" pull --ff-only origin "$BRANCH" && remote_pull="ok" || remote_pull="failed"
  else
    remote_check="failed"
    CURRENT_BRANCH="$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD)"
    git -C "$REPO_DIR" pull --ff-only origin "$CURRENT_BRANCH" && remote_pull="ok" || remote_pull="failed"
  fi
  if [ "$remote_pull" = "failed" ] && [ -f "$BUNDLE_PATH" ]; then
    echo "[warn] remote pull failed; attempting bundle refresh"
    git -C "$REPO_DIR" fetch "$BUNDLE_PATH" "$BRANCH" || true
    if git -C "$REPO_DIR" show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
      git -C "$REPO_DIR" checkout "$BRANCH" || true
    fi
  fi
  branch_now="$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo missing)"
  repo_git="no"
  [ -d "$REPO_DIR/.git" ] && repo_git="yes"
  cat > "$STATUS_FILE" <<STATUS_EOF
timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
repo_path=$REPO_DIR
repo_git=$repo_git
branch=$branch_now
clone_source=$clone_source
remote_check=$remote_check
remote_pull=$remote_pull
bundle_path=$BUNDLE_PATH
STATUS_EOF
  echo "[status] $STATUS_FILE"
  git -C "$REPO_DIR" status --short --branch || true
  echo "[done] sync complete"
else
  echo "[error] repository directory is missing after clone/sync"
  exit 1
fi
