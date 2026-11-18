from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

CSV_PATH = Path("reports/perf/locust_stats.csv")
P95_LIMIT_MS = float(os.getenv("PERF_P95_MS", "500"))
ERROR_RATE_LIMIT = float(os.getenv("PERF_ERROR_RATE", "0.01"))


def main() -> int:
    if not CSV_PATH.exists():
        print(f"missing {CSV_PATH}; run perf/run_perf.sh first", file=sys.stderr)
        return 1

    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    aggregated = next((row for row in rows if row.get("Name") == "Aggregated"), None)
    if aggregated is None:
        print("no Aggregated row in Locust CSV", file=sys.stderr)
        return 1

    requests_count = int(aggregated["Request Count"])
    failures = int(aggregated["Failure Count"])
    if requests_count == 0:
        print(
            "no requests were sent; check Locust --host and user spawn errors",
            file=sys.stderr,
        )
        return 1

    p95 = float(aggregated["95%"])
    error_rate = failures / requests_count

    print(
        f"requests={requests_count} failures={failures} "
        f"error_rate={error_rate:.2%} p95={p95:.0f}ms"
    )

    failed = False
    if error_rate > ERROR_RATE_LIMIT:
        print(
            f"error rate {error_rate:.2%} exceeds {ERROR_RATE_LIMIT:.2%}",
            file=sys.stderr,
        )
        failed = True
    if p95 > P95_LIMIT_MS:
        print(f"p95 {p95:.0f}ms exceeds {P95_LIMIT_MS:.0f}ms", file=sys.stderr)
        failed = True

    if failed:
        return 1
    print("perf thresholds OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
