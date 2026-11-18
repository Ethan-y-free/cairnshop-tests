#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
mkdir -p reports/perf

locust -f perf/locustfile.py \
    --headless \
    --host "${CAIRNSHOP_TEST_BASE_URL:-http://127.0.0.1:8080}" \
    -u "${USERS:-20}" \
    -r "${SPAWN_RATE:-2}" \
    -t "${DURATION:-60s}" \
    --csv=reports/perf/locust \
    --html=reports/perf/report.html \
    --only-summary

python scripts/check_perf.py
