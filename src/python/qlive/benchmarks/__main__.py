"""Command-line entry point for the QLive benchmark framework.

Usage:
    python -m qlive.benchmarks               # run all suites
    python -m qlive.benchmarks chunk buffer   # run specific suites
    python -m qlive.benchmarks --list         # list available suites
    python -m qlive.benchmarks --json         # machine-readable output
    python -m qlive.benchmarks --quick        # reduced workloads (fast smoke check)
"""

from __future__ import annotations

import argparse
import json
import sys

from qlive.benchmarks import runner
from qlive.benchmarks.buffer_bench import BufferSuite
from qlive.benchmarks.chunk_bench import ChunkSuite
from qlive.benchmarks.encryption_bench import EncryptionSuite
from qlive.benchmarks.incentives_bench import IncentivesSuite
from qlive.benchmarks.pipeline_bench import PipelineSuite
from qlive.benchmarks.proof_bench import ProofSuite
from qlive.benchmarks.reputation_bench import ReputationSuite
from qlive.benchmarks.retransmit_bench import RetransmitSuite
from qlive.benchmarks.sim_bench import SimSuite
from qlive.benchmarks.swarm_bench import SwarmSuite

SUITES: dict[str, runner.Suite] = {
    suite.name: suite
    for suite in (
        ChunkSuite(),
        BufferSuite(),
        EncryptionSuite(),
        SwarmSuite(),
        RetransmitSuite(),
        IncentivesSuite(),
        ProofSuite(),
        ReputationSuite(),
        PipelineSuite(),
        SimSuite(),
    )
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="qlive.benchmarks",
        description="QLive local benchmark framework (no network required)",
    )
    parser.add_argument(
        "suites",
        nargs="*",
        help="Suite names to run (default: all). See --list.",
    )
    parser.add_argument("--list", action="store_true", help="List available suites")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run reduced workloads (fewer iterations/sizes) for fast smoke checks",
    )
    args = parser.parse_args(argv)

    if args.list:
        for suite in SUITES.values():
            print(f"{suite.name:<12} {suite.description}")
        return 0

    unknown = [name for name in args.suites if name not in SUITES]
    if unknown:
        print(f"Unknown suite(s): {', '.join(unknown)}", file=sys.stderr)
        print(f"Available: {', '.join(SUITES)}", file=sys.stderr)
        return 2

    selected = [SUITES[name] for name in args.suites] if args.suites else list(SUITES.values())

    outputs: list[tuple[str, str, list[runner.Result]]] = []
    for suite in selected:
        outputs.append((suite.name, suite.description, suite.run(quick=args.quick)))

    if args.json:
        payload = {name: [r.as_dict() for r in results] for name, _desc, results in outputs}
        print(json.dumps(payload, indent=2))
        return 0

    for name, description, results in outputs:
        print(f"\n=== {name}: {description} ===")
        print(runner.format_results(results))

    return 0


if __name__ == "__main__":
    sys.exit(main())
