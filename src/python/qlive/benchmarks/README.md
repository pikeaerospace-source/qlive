# QLive Benchmark Framework

Local, offline benchmarks for the QLive reference implementation.

Everything runs in-process against the `qlive` package — **no live Qortal
network, QDN, FFmpeg, or real sockets required**. The benchmarks measure CPU
throughput, memory footprint, and scaling behaviour of the core protocol
components so design decisions (chunk sizing, buffer sizing, encryption,
swarm topology, incentives) can be grounded in measured numbers.

## Running

From `src/python/` (or anywhere the `qlive` package is importable):

```bash
# List available suites
python -m qlive.benchmarks --list

# Run every suite
python -m qlive.benchmarks

# Run specific suites
python -m qlive.benchmarks chunk buffer encryption

# Reduced workloads (fast smoke check — CI / sanity runs)
python -m qlive.benchmarks --quick

# Machine-readable output (JSON)
python -m qlive.benchmarks --json > results.json
```

`--quick` runs each suite with reduced workloads (fewer iterations and/or
smaller sizes) while keeping the same result structure, so it completes in
well under a second. It is intended for CI smoke checks and fast iteration;
use a full run for numbers you intend to compare.

## Suites

| Suite | What it measures |
| --- | --- |
| `chunk` | Fixed header overhead ratio; Ed25519 sign/verify, SHA-256, and serialize/deserialize throughput |
| `buffer` | RAM footprint at various bitrates/windows; add/evict and lookup throughput |
| `encryption` | AES-256-GCM bulk and per-chunk throughput for private streams |
| `swarm` | Tree/mesh construction scaling, fanout-vs-depth, churn, node-removal reattachment |
| `retransmit` | Request/handle/timeout/recovery-cycle throughput |
| `incentives` | Tit-for-tat bandwidth accounting and classification throughput |
| `proof` | Proof-of-relay receipt sign/verify/redeem throughput |
| `pipeline` | End-to-end in-memory delivery model: tree depth, fan-out cost, latency estimate |
| `sim` | Discrete-event swarm simulation: fanout, mesh, retransmit, buffer, churn, free-riders |

## Methodology

- `runner.best_time()` warms up once, then reports the **fastest** of
  `repeat` rounds (each of `number` calls) to reduce scheduler noise.
- Payloads are generated with `os.urandom` (incompressible, like real video)
  to avoid any cache/compression artifacts in hashing and crypto timings.
- Absolute numbers are environment-dependent (CPU, Python version, OpenSSL
  backend); treat them as **relative** comparisons across parameters, not
  portable constants.

## Findings surfaced by this harness

The `swarm` suite initially reported a flat delivery tree (depth = 1) for
every peer count. Investigation revealed a bug in `DeliveryTree.find_parent`:
unattached peers (mesh viewers, which live in the peer map with
`tree_depth == 0` and no parent) were being selected as tree parents,
flattening the tree and defeating the depth-based latency model. The bug was
fixed and covered by `tests/python/test_swarm.py::TestDeliveryTree::test_attach_skips_unattached_peers`.
After the fix, tree depth scales correctly (e.g., depth 2 → 3 → 4 for
100 → 1000 → 3000 peers).

## Extending

Add a new module in this package that subclasses `runner.Suite`, then register
it in `__main__.py`'s `SUITES` dict. A suite is just:

```python
from qlive.benchmarks.runner import Result, Suite, best_time

class MySuite(Suite):
    name = "my-suite"
    description = "What this measures."

    def run(self) -> list[Result]:
        t = best_time(some_function, arg1, repeat=3, number=1000)
        return [Result("my.metric", t * 1e6, "us", "optional note")]
```
