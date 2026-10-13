#!/bin/bash
# CI check: ensure generated API types are up-to-date.
# Runs orval and fails if there are any uncommitted changes to generated files.
set -e

echo "Generating API types..."
cd frontend && npx orval

echo "Checking for stale generated types..."
if ! git diff --exit-code -- src/api/generated; then
    echo "ERROR: Generated API types are stale. Run scripts/generate_api_types.sh and commit the changes."
    exit 1
fi

echo "API types are up-to-date."
