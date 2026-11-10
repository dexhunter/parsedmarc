#!/usr/bin/env python3
"""Peak traced memory of parsed_aggregate_reports_to_csv.

tracemalloc is started after the report exists, so the figure is what the
CSV conversion itself allocates. The returned CSV is about 650 KB; the peak
is several times that because every flat row dict is retained, and each row
is copied into a second dict for _csv_safe, until the StringIO is finished.

Prints baseline_value (median peak bytes) and noise_pct = (max - min) /
median * 100 over 5 runs.
"""

from __future__ import annotations

import os
import tracemalloc

os.environ.setdefault("GITHUB_ACTIONS", "true")

import parsedmarc  # noqa: E402

from lib import collect, load_large_aggregate, median_and_spread  # noqa: E402


def main() -> None:
    xml = load_large_aggregate()
    report = parsedmarc.parse_aggregate_report_xml(
        xml, offline=True, always_use_local_files=True
    )
    if len(report["records"]) != 2286:
        raise RuntimeError("unexpected record count")
    # Warm the CSV path (header, formula scan) before measuring.
    warmup = parsedmarc.parsed_aggregate_reports_to_csv(report)
    if not warmup.startswith("xml_schema,"):
        raise RuntimeError("CSV header changed")

    def once() -> float:
        tracemalloc.start()
        try:
            csv_text = parsedmarc.parsed_aggregate_reports_to_csv(report)
            _current, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        if len(csv_text) < 100000:
            raise RuntimeError("CSV unexpectedly small")
        return float(peak)

    runs = collect(once)
    median, spread = median_and_spread(runs)
    print(f"baseline_value={median:.6f}")
    print(f"noise_pct={spread:.6f}")
    print("runs_bytes=" + ",".join(str(int(value)) for value in runs))


if __name__ == "__main__":
    main()
