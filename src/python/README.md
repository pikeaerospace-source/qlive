# QLive Python Components

Python components for the QLive decentralized live-streaming protocol.

## Planned Components

| Component | Status | Description |
| --- | --- | --- |
| `chunking/` | Planned | CMAF/fMP4 ephemeral chunking engine |
| `buffer/` | Planned | RAM-only sliding-window buffer |
| `swarm/` | Planned | Dual-layer peer swarm (tree + mesh) |
| `signaling/` | Planned | QDN signaling integration |
| `archival/` | Planned | Live → VOD archival pipeline |
| `incentives/` | Planned | Tit-for-tat and proof-of-relay |

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