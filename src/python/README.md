# QLive Python Components

Python components for the QLive decentralized live-streaming protocol.

## Components

The reference implementation lives in the `qlive/` package. All components
run in-memory/offline (no live Qortal network required).

| Module | Description |
| --- | --- |
| `chunk.py` | CMAF/fMP4 ephemeral chunk format, signing, verification |
| `segmenter.py` | FFmpeg-based CMAF/fMP4 segmenter |
| `buffer.py` | RAM-only sliding-window buffer |
| `swarm.py` | Dual-layer peer swarm (tree + mesh) |
| `signaling.py` | QDN signaling (in-memory registry stand-in) |
| `archival.py` | Live → VOD archival pipeline |
| `retransmit.py` | Chunk retransmission protocol |
| `adaptive.py` | Adaptive bitrate control |
| `incentives.py` | Tit-for-tat bandwidth accounting |
| `proof.py` | Proof-of-relay bandwidth receipts |
| `broadcaster.py` / `viewer.py` | Broadcaster and viewer applications |
| `cli.py` | `qlive broadcast` / `qlive watch` CLI |
| `benchmarks/` | Offline benchmark framework |

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check .

# Format
black .
```

## Benchmarks

A local, offline benchmark framework lives in `qlive/benchmarks/` — no live
Qortal network, QDN, FFmpeg, or sockets required. It measures chunk crypto
throughput, buffer memory, encryption, swarm scaling, retransmission,
incentives, proof-of-relay, and the end-to-end delivery model.

```bash
python -m qlive.benchmarks            # run all suites
python -m qlive.benchmarks --list     # list suites
python -m qlive.benchmarks --json     # machine-readable output
```

See `qlive/benchmarks/README.md` for details.

## Dependencies

- Python 3.10+
- See `pyproject.toml` for full dependency list