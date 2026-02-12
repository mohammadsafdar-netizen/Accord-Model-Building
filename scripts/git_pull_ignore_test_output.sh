#!/bin/bash
# Run from repo root when "git pull" fails due to test_output/ changes.
# Backs up test_output, pulls, then you can delete the backup or keep it.

set -e
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

if [ -d "test_output" ]; then
  echo "Moving test_output to test_output.bak so pull can proceed..."
  mv test_output test_output.bak
fi

git pull origin main

echo "Done. Pull succeeded."
echo "  - Your old run output is in test_output.bak (delete it if you don't need: rm -rf test_output.bak)"
echo "  - test_output will be recreated when you run the pipeline again."
