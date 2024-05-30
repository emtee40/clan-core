#!/usr/bin/env bash
set -euo pipefail

remoteFork="${1:-origin}"
remoteUpstream="${2:-upstream}"
targetBranch="${3:-main}"
shift && shift
TMPDIR="$(mktemp -d)"
currentBranch="$(git rev-parse --abbrev-ref HEAD)"
user="$(git config --get remote.origin.url | awk -F'[@:/]' '{print $3}' | tr -d '\n')"
tempRemoteBranch="$user-$currentBranch"
root_dir=$(git rev-parse --show-toplevel)

# Function to check if a remote exists
check_remote() {
  if git remote get-url "$1" > /dev/null 2>&1; then
    return 0
  else
    return 1
  fi
}

# Check if the remote 'upstream' is defined
if ! check_remote "$remoteUpstream"; then
  echo "Error: $remoteUpstream remote is not defined."
  echo "Please fork the repository and add the $remoteUpstream remote."
  echo "$ git remote add $remoteUpstream <upstream-url>"
  exit 1
fi

upstream_url=$(git remote get-url "$remoteUpstream")
repo=$(echo "$upstream_url" | sed -E 's#.*:([^/]+/[^.]+)\.git#\1#')

treefmt -C "$root_dir"
git log --reverse --pretty="format:%s%n%n%b%n%n" "$remoteUpstream/$targetBranch..HEAD" > "$TMPDIR"/commit-msg


$EDITOR "$TMPDIR"/commit-msg

COMMIT_MSG=$(cat "$TMPDIR"/commit-msg)

firstLine=$(echo "$COMMIT_MSG" | head -n1)
rest=$(echo "$COMMIT_MSG" | tail -n+2)

if [[ "$firstLine" == "$rest" ]]; then
  rest=""
fi

git push --force -u "$remoteFork" HEAD:refs/heads/"$tempRemoteBranch"

tea pr create \
  --repo "$repo" \
  --head "$user:$tempRemoteBranch" \
  --title "$firstLine" \
  --description "$rest" \
  "$@"