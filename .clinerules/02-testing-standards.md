# Unit Testing Standards

## Python Tests

### Framework
- **pytest** 8+ with `pytest-asyncio`, `pytest-cov`.
- Run: `cd src/python && pytest`
- Coverage target: **≥ 90%** on new code.

### Test File Layout
- Each source module `qlive/<module>.py` has a matching test file `tests/python/test_<module>.py`.
- Use `from qlive.<module> import ...` — avoid importing into `qlive/__init__.py`.

### Naming
- **Classes:** `Test<Module>` or `Test<Feature>` (pytest class-based grouping).
- **Methods:** `test_<scenario>` describing the behaviour under test.
- Use descriptive names — e.g. `test_sign_and_verify`, `test_deserialize_too_short`.

### Fixtures
- Define fixtures at module level or in `conftest.py`.
- One fixture per logical resource (e.g. `stream_id`, `key_pair`, `sample_payload`).
- Keep fixtures minimal; prefer composition over inheritance.

### Patterns
- **Happy path** first, **error cases** second.
- Test edge cases: invalid inputs, boundary values, empty data, corrupted data.
- For cryptographic operations, generate fresh keys in fixtures — never hardcode keys.
- Use `pytest.raises(...)` for expected exceptions.

### Example Structure

```python
"""Tests for QLive ephemeral chunk format."""

import hashlib

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from qlive.chunk import (
    Chunk,
    ChunkFormatError,
    ChunkSignatureError,
    ...
)


@pytest.fixture
def stream_id() -> bytes:
    return hashlib.sha256(b"test-stream").digest()


@pytest.fixture
def key_pair() -> tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
    private_key = ed25519.Ed25519PrivateKey.generate()
    return private_key, private_key.public_key()


class TestCreateChunk:
    def test_create_valid_chunk(self, stream_id, sample_payload):
        ...

    def test_invalid_stream_id_length(self, sample_payload):
        with pytest.raises(ChunkFormatError):
            create_chunk(b"short", 1, sample_payload)


class TestChunkProperties:
    ...

class TestSigning:
    ...

class TestSerialization:
    ...
```

### Async Tests
- Use `async def test_...` with `pytest-asyncio` (auto mode enabled in `pyproject.toml`).

---

## JavaScript / TypeScript Tests

### Framework
- **Vitest** with `@testing-library/react`, `@testing-library/jest-dom`, `jsdom`.
- Run: `cd src/js && npm test` (or `npm run test:watch`).

### File Layout
- Co-locate tests with source: `src/data/api.test.ts`, `src/components/StreamCard.test.tsx`.
- Use `.test.ts` / `.test.tsx` suffix.

### Naming
- `describe("<ComponentName>", ...)` for test suites.
- `it("should <behaviour>", ...)` for individual tests.

### Patterns
- Prefer `screen.getByRole` / `getByText` over test IDs.
- Use `userEvent` for interactions.
- Mock data services at the API boundary (`src/data/api.ts`).

---

## Java Tests (forthcoming)

- **JUnit 5** + Mockito.
- Test per class, mirroring production source tree.
- Aim for ≥ 80% coverage.

---

## Coverage Requirements

| Layer | Minimum | Command |
|-------|---------|---------|
| Python core | 90% | `cd src/python && pytest --cov=qlive` |
| Python benchmarks | Smoke | `python -m qlive.benchmarks` |
| JS/TS Web UI | 80% | `cd src/js && npm test` |
| Java (when added) | 80% | `mvn test` |

---

## What Not To Test

- Trivial getters/setters or properties.
- External library behaviour (test your integration, not the library).
- Code that will be rewritten before v0.2.
- Benchmark code (smoke-test that benchmarks run without error only).
