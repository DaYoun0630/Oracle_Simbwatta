#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-mci-postgres}"
POSTGRES_DB="${POSTGRES_DB:-cognitive}"
POSTGRES_USER="${POSTGRES_USER:-mci_user}"

echo "Applying migrations to container=${POSTGRES_CONTAINER} db=${POSTGRES_DB} user=${POSTGRES_USER}"

for f in \
  "${ROOT_DIR}/migrations/001_init.sql" \
  "${ROOT_DIR}/migrations/002_clinical_tables.sql" \
  "${ROOT_DIR}/migrations/003_schema_alignment.sql"
do
  echo "-> $(basename "$f")"
  docker exec -i "${POSTGRES_CONTAINER}" \
    psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -v ON_ERROR_STOP=1 -f /dev/stdin < "$f"
done

echo "Migrations applied."

