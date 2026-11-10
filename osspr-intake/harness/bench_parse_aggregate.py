#!/usr/bin/env python3
"""Time parse_aggregate_report_xml on the bundled large aggregate report.

The success path parses the document twice (a probe xmltodict.parse whose
tree is discarded, then _parse_limited_xml). One run is one parse of that
report, after a warmup parse that fills the IP cache.

The clock is time.process_time (CPU time spent in the process, including
the parser's syscalls). Prints median_ms and noise_pct = (max - min) /
median * 100 over 5 runs.
"""

from __future__ import annotations

import os
import time

os.environ.setdefault("GITHUB_ACTIONS", "true")

import parsedmarc  # noqa: E402

from lib import collect, load_large_aggregate, median_and_spread  # noqa: E402


def main() -> None:
    xml = load_large_aggregate()
    parsedmarc.parse_aggregate_report_xml(
        xml, offline=True, always_use_local_files=True
    )

    def once() -> float:
        started = time.process_time()
        report = parsedmarc.parse_aggregate_report_xml(
            xml, offline=True, always_use_local_files=True
        )
        elapsed_ms = (time.process_time() - started) * 1000.0
        if len(report["records"]) != 2286:
            raise RuntimeError("unexpected parse result")
        return elapsed_ms

    runs = collect(once)
    median, spread = median_and_spread(runs)
    print(f"median_ms={median:.6f}")
    print(f"noise_pct={spread:.6f}")
    print("runs_ms=" + ",".join(f"{value:.6f}" for value in runs))


if __name__ == "__main__":
    main()
