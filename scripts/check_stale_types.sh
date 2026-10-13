#!/bin/bash
set -e
cd "$(dirname "$0")/../frontend"
npx orval
if ! git diff --exit-code src/api/; then
  echo "ERROR: Generated API types are stale. Run ./scripts/generate_api_types.sh and commit the result."
  exit 1
fi
echo "API types are up to date."
