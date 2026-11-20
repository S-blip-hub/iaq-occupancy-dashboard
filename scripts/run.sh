#!/usr/bin/env bash
# Build dashboard data, figures and SQL tables from a testo export, then run the tests.
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 <testo_export.xlsx|csv> [sheet name]" >&2
  exit 1
fi

cd "$(dirname "$0")/.."
SHEET="${2:-master sheet}"

python -m iaq.build "$1" --sheet "$SHEET"
python -m pytest -q
echo "Dashboard ready: dashboard/index.html"
