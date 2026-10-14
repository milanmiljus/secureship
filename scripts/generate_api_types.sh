#!/bin/bash
set -e
cd "$(dirname "$0")/../frontend"
echo "Generating API types from http://localhost:8000/openapi.json..."
npx orval
echo "Done."
