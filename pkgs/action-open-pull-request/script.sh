#!/usr/bin/env bash
set -euo pipefail

REMOTE_BRANCH="${REMOTE_BRANCH:-auto-pr}"

git diff --quiet || {
  echo "Working tree is dirty, please commit first"
  exit 1
}

git push origin "HEAD:$REMOTE_BRANCH"

tea pr create \
  --head "$REMOTE_BRANCH" \
  --labels "0.kind: automation" \
  --title "This PR was created automatically"
