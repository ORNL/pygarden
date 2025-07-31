#!/usr/bin/env bash
# -*- coding: utf-8 -*-
set -euo pipefail
cat <<EOF
              ____    _    ____  ____  _____ _   _
 _ __  _   _ / ___|  / \  |  _ \|  _ \| ____| \ | |
| '_ \| | | | |  _  / _ \ | |_) | | | |  _| |  \| |
| |_) | |_| | |_| |/ ___ \|  _ <| |_| | |___| |\  |
| .__/ \__, |\____/_/   \_\_| \_\____/|_____|_| \_|
|_|    |___/            release script
()
 \
  \
  ^ ^ ^
EOF
BUMP_KIND=${1:-patch}
source .venv/bin/activate
source .env
# if the first argument is not in the list of bump kinds, print usage
case "$BUMP_KIND" in
  major|minor|patch)
    echo "Bumping version to $BUMP_KIND"
    ;;
  *)
    echo "Usage: $0 <bump_kind>"
    echo "bump_kind can be one of: major, minor, patch"
    exit 1
    ;;
esac
bumpversion --current-version "$(cat COMMON_VERSION)" "$BUMP_KIND"
# check if the version was bumped
if [[ $? -ne 0 ]]; then
  echo "Version was not bumped, exiting"
  exit 1
fi
uv build && uv publish --token "$UV_PUBLISH_TOKEN"
rm -rf dist/
git push
git push --tags
echo "🥳 Released pyGARDEN Successfully"