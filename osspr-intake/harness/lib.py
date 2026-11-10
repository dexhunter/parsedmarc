"""Shared pieces for the intake harnesses.

Noise is the full spread of the runs, (max - min) / median * 100, not a
standard deviation. Every harness collects five runs after a warmup.
"""

from __future__ import annotations

import gc
import statistics
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LARGE_AGGREGATE = (
    REPO_ROOT
    / "samples"
    / "aggregate"
    / "!large-example.com!1711897200!1711983600.xml"
)
RUNS = 5


def load_large_aggregate() -> str:
    return LARGE_AGGREGATE.read_text(encoding="utf-8")


def median_and_spread(values: list[float]) -> tuple[float, float]:
    if len(values) < RUNS:
        raise RuntimeError(f"expected at least {RUNS} runs, got {len(values)}")
    med = float(statistics.median(values))
    if med == 0:
        raise RuntimeError(f"median is 0 for {values}")
    spread = (max(values) - min(values)) / med * 100.0
    return med, spread


def collect(fn, runs: int = RUNS) -> list[float]:
    """Measure ``fn`` ``runs`` times, collecting GC between runs."""
    values: list[float] = []
    for _ in range(runs):
        gc.collect()
        values.append(float(fn()))
    return values
