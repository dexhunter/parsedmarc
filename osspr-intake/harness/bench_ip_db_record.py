#!/usr/bin/env python3
"""Time get_ip_address_db_record across one large report's source IPs.

The function opens the MMDB for every call and closes it when the reader
falls out of scope. The workload is the 2,286 distinct source addresses in
the bundled large aggregate report, looked up once each per run. There is
no result cache inside get_ip_address_db_record, so every run pays the opens.

The clock is time.process_time (CPU time), which includes the open() and
read() syscalls. Prints median_ms and noise_pct = (max - min) / median *
100 over 5 runs.
"""

from __future__ import annotations

import os
import time

os.environ.setdefault("GITHUB_ACTIONS", "true")

import parsedmarc  # noqa: E402
from parsedmarc.utils import get_ip_address_db_record  # noqa: E402

from lib import collect, load_large_aggregate, median_and_spread  # noqa: E402


def main() -> None:
    xml = load_large_aggregate()
    report = parsedmarc.parse_aggregate_report_xml(
        xml, offline=True, always_use_local_files=True
    )
    ips = [record["source"]["ip_address"] for record in report["records"]]
    if len(ips) != 2286 or len(set(ips)) != 2286:
        raise RuntimeError(f"expected 2286 distinct source IPs, got {len(set(ips))}")
    # One untimed pass opens the database for every address so the recorded
    # runs are not the first touch of the file cache.
    for ip in ips:
        get_ip_address_db_record(ip)

    def once() -> float:
        started = time.process_time()
        last = None
        for ip in ips:
            last = get_ip_address_db_record(ip)
        elapsed_ms = (time.process_time() - started) * 1000.0
        if not isinstance(last, dict) or "asn" not in last or "country" not in last:
            raise RuntimeError("lookup did not return an IP database record")
        return elapsed_ms

    runs = collect(once)
    median, spread = median_and_spread(runs)
    print(f"median_ms={median:.6f}")
    print(f"noise_pct={spread:.6f}")
    print("runs_ms=" + ",".join(f"{value:.6f}" for value in runs))


if __name__ == "__main__":
    main()
