#!/usr/bin/env python3
"""Count object allocations inside one warm parse_aggregate_report_xml call.

The counter is PYMEM_DOMAIN_OBJ malloc + calloc + realloc. The success path
parses the XML twice; the probe tree is discarded, so those allocations do
not survive the call. The harness compiles osspr-intake/harness/alloccount.c
with the running interpreter (gcc and Python headers) into /tmp.

Prints baseline_value (median count) and noise_pct = (max - min) / median
* 100 over 5 runs.
"""

from __future__ import annotations

import os
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path

os.environ.setdefault("GITHUB_ACTIONS", "true")

import parsedmarc  # noqa: E402

from lib import collect, load_large_aggregate, median_and_spread  # noqa: E402

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "alloccount.c"


def _load_counter():
    include = sysconfig.get_config_var("INCLUDEPY")
    if not include:
        raise RuntimeError("INCLUDEPY is unset; Python development headers are required")
    out_dir = Path(tempfile.gettempdir()) / "osspr-intake-alloccount"
    out_dir.mkdir(parents=True, exist_ok=True)
    module_path = out_dir / "alloccount.so"
    compile_cmd = [
        "gcc",
        "-shared",
        "-fPIC",
        "-O2",
        f"-I{include}",
        "-o",
        str(module_path),
        str(SOURCE),
    ]
    subprocess.run(compile_cmd, check=True)
    sys.path.insert(0, str(out_dir))
    import alloccount  # noqa: WPS433

    return alloccount


def main() -> None:
    counter = _load_counter()
    xml = load_large_aggregate()
    # Install the hook and warm caches (IP info, reverse-DNS map) before
    # the counted runs, so the count is the parse itself.
    counter.start()
    report = None
    for _ in range(2):
        report = parsedmarc.parse_aggregate_report_xml(
            xml, offline=True, always_use_local_files=True
        )
    if report is None or len(report["records"]) != 2286:
        raise RuntimeError("unexpected record count")

    def once() -> float:
        counter.reset()
        parsed = parsedmarc.parse_aggregate_report_xml(
            xml, offline=True, always_use_local_files=True
        )
        total = counter.count()
        if len(parsed["records"]) != 2286 or total < 1000:
            raise RuntimeError(f"allocation count looks wrong: {total}")
        return float(total)

    runs = collect(once)
    median, spread = median_and_spread(runs)
    print(f"baseline_value={median:.6f}")
    print(f"noise_pct={spread:.6f}")
    print("runs_allocs=" + ",".join(str(int(value)) for value in runs))


if __name__ == "__main__":
    main()
