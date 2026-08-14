"""Smoke tests for the QLive local benchmark framework."""

import math

from qlive.benchmarks import __main__ as benchmarks_main
from qlive.benchmarks.runner import Result, best_time, format_results


def test_best_time_returns_nonnegative():
    assert best_time(lambda: None, repeat=2, number=100) >= 0.0


def test_format_results_contains_values():
    out = format_results([Result("x", 1.2345, "us", "note")])
    assert "x" in out
    assert "1.234" in out


def test_all_suites_produce_finite_results():
    for suite in benchmarks_main.SUITES.values():
        results = suite.run()
        assert results, f"{suite.name} produced no results"
        for result in results:
            assert isinstance(result, Result)
            assert math.isfinite(result.value), (
                f"{suite.name}: non-finite value for {result.name}"
            )
            assert result.value >= 0, f"{suite.name}: negative value for {result.name}"


def test_cli_list_returns_zero():
    assert benchmarks_main.main(["--list"]) == 0


def test_cli_json_returns_zero():
    assert benchmarks_main.main(["incentives", "--json"]) == 0


def test_cli_unknown_suite_returns_two():
    assert benchmarks_main.main(["does-not-exist"]) == 2
