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

## Dependencies

- Python 3.10+
- See `pyproject.toml` for full dependency list