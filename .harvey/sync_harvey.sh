#!/usr/bin/env bash
set -o pipefail

BRANCH="${1:-harvey-elite-2026}"
GITHUB_REMOTE="${GITHUB_REMOTE:-billy}"
GITLAB_REMOTE="${GITLAB_REMOTE:-gitlab}"
GOOGLE_DRIVE_MOUNT="${GOOGLE_DRIVE_MOUNT:-}"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Not inside a git repository."
  exit 1
fi

echo "[1/5] Fetching remotes..."
git fetch --all --prune

if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  git checkout "${BRANCH}"
else
  git checkout -b "${BRANCH}"
fi

echo "[2/5] Pulling latest from origin..."
git pull --ff-only origin "$(git rev-parse --abbrev-ref HEAD)" >/dev/null 2>&1 || true

echo "[3/5] Pushing to GitHub remote '${GITHUB_REMOTE}'..."
git push -u "${GITHUB_REMOTE}" "${BRANCH}" || true

if git remote get-url "${GITLAB_REMOTE}" >/dev/null 2>&1; then
  echo "[4/5] Pushing to GitLab remote '${GITLAB_REMOTE}'..."
  git push -u "${GITLAB_REMOTE}" "${BRANCH}" || true
else
  echo "[4/5] GitLab remote '${GITLAB_REMOTE}' not configured, skipping."
fi

if [ -n "${GOOGLE_DRIVE_MOUNT}" ] && [ -d "${GOOGLE_DRIVE_MOUNT}" ]; then
  echo "[5/5] Exporting .harvey profile snapshot to Google Drive mount..."
  repo_name="$(basename "$(pwd)")"
  tar -czf "${GOOGLE_DRIVE_MOUNT}/${repo_name}-harvey-profile.tar.gz" .harvey 2>/dev/null || true
else
  echo "[5/5] GOOGLE_DRIVE_MOUNT not set or not found, skipping Drive export."
fi

echo "Harvey sync completed."
