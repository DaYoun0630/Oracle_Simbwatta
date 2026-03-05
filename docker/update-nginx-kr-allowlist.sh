#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/docker/nginx-geo"
OUT_FILE="${OUT_DIR}/allow_kr.conf"
TMP_FILE="$(mktemp)"
SOURCE_URL="https://www.ipdeny.com/ipblocks/data/countries/kr.zone"

mkdir -p "${OUT_DIR}"

curl -fsSL "${SOURCE_URL}" -o "${TMP_FILE}"
awk 'NF>0 && $0 !~ /^#/ {print $0 " 1;"}' "${TMP_FILE}" > "${OUT_FILE}"
rm -f "${TMP_FILE}"

count="$(wc -l < "${OUT_FILE}" | tr -d ' ')"
echo "Updated ${OUT_FILE} (${count} CIDRs)"
