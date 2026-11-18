#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
CAIRNSHOP_TEST_REQUIRE_CAIRNKV=0 pytest tests/api -m api "$@"
