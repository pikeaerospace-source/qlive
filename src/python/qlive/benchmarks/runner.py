"""Benchmark runner primitives for QLive.

Provides a tiny, dependency-free timing and reporting layer used by all
benchmark suites. Designed to be runnable anywhere the ``qlive`` package
is importable — no network or external services required.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Result:
    """A single benchmark measurement."""

    name: str
    value: float
    unit: str = ""
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-friendly dict."""
        return {"name": self.name, "value": self.value, "unit": self.unit, "note": self.note}


def best_time(
    fn: Callable[..., Any],
    *args: Any,
    repeat: int = 3,
    number: int = 1000,
    **kwargs: Any,
) -> float:
    """Return the fastest seconds-per-call of ``fn(*args, **kwargs)``.

    Performs a single warm-up call, then ``repeat`` rounds of ``number``
    calls each, and returns the minimum per-call time across rounds. Using
    the minimum (rather than the mean) reduces the impact of scheduler
    noise and gives a stable throughput estimate.

    Args:
        fn: The callable to benchmark.
        *args: Positional arguments to pass to ``fn``.
        repeat: Number of timing rounds to run.
        number: Number of calls per timing round.
        **kwargs: Keyword arguments to pass to ``fn``.

    Returns:
        Seconds per call (best round).
    """
    fn(*args, **kwargs)  # warm-up
    best = float("inf")
    for _ in range(repeat):
        start = time.perf_counter()
        for _ in range(number):
            fn(*args, **kwargs)
        elapsed = time.perf_counter() - start
        best = min(best, elapsed / number)
    return best


class Suite:
    """Base class for a benchmark suite."""

    name: str = "unnamed"
    description: str = ""

    def run(self) -> list[Result]:
        """Run the suite and return its measurements."""
        raise NotImplementedError


def _fmt_number(value: float) -> str:
    """Format a numeric value with context-appropriate precision."""
    if value == float("inf"):
        return "inf"
    if value >= 1000:
        return f"{value:,.1f}"
    if value >= 100:
        return f"{value:.1f}"
    if value >= 10:
        return f"{value:.2f}"
    if value >= 1:
        return f"{value:.3f}"
    return f"{value:.4f}"


def format_results(results: list[Result]) -> str:
    """Format a list of results as an aligned, human-readable table."""
    if not results:
        return "(no results)"

    name_width = max(len(r.name) for r in results)
    value_width = max(len(_fmt_number(r.value)) for r in results)
    unit_width = max(len(r.unit) for r in results) or 1

    lines = []
    header = (
        f"{'name':<{name_width}}  {'value':>{value_width}}  "
        f"{'unit':<{unit_width}}  note"
    )
    lines.append(header)
    lines.append("-" * len(header))
    for r in results:
        lines.append(
            f"{r.name:<{name_width}}  {_fmt_number(r.value):>{value_width}}  "
            f"{r.unit:<{unit_width}}  {r.note}"
        )
    return "\n".join(lines)
