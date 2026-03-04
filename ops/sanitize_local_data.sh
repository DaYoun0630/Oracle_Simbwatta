#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Purge local data and runtime artifacts that must never be published.
# Review before running. This is destructive.

rm -rf "$ROOT_DIR/data/raw" \
       "$ROOT_DIR/data/processed" \
       "$ROOT_DIR/data/tmp" \
       "$ROOT_DIR/minio-data" \
       "$ROOT_DIR/runtime" \
       "$ROOT_DIR/db_backups" \
       "$ROOT_DIR/exports"

echo "Local data/runtime removed."
