# Chunk Format

**Status:** Reference — mirrors `qlive/chunk.py` and `protocol.md` §3.

A chunk is a self-contained, signed unit of media data (a CMAF/fMP4 fragment).

---

## Binary Layout (155-byte header)

| Field | Bytes | Description |
| --- | --- | --- |
| Magic | 4 | `"QLIV"` |
| Version | 1 | `1` |
| Stream ID | 32 | SHA-256 of stream metadata |
| Sequence ID | 8 | Monotonic per stream |
| Timestamp | 8 | Unix epoch ms |
| Duration | 2 | Fragment duration ms (500–2000) |
| Payload Size | 4 | Payload bytes |
| Payload Hash | 32 | SHA-256 of payload |
| Signature | 64 | Ed25519 over header (91 bytes incl. payload hash) |
| Payload | var | CMAF/fMP4 media (optionally encrypted) |

---

## Signing

Each chunk is signed with the broadcaster's Ed25519 key. The signature covers
the **header only** (91 bytes), which embeds the SHA-256 `payload_hash`. Viewers
verify against the broadcaster's public key (resolved from the Qortal Name);
payload integrity is guaranteed because the signed header carries the payload's
hash. Signing the header — not the payload — keeps sign/verify cost constant
regardless of bitrate; see [ENCRYPTION-MODEL.md](ENCRYPTION-MODEL.md).

---

## Encryption (private streams)

For private streams, the payload is encrypted with AES-256-GCM before signing;
the header stays plaintext for routing/verification. See
[ENCRYPTION-MODEL.md](ENCRYPTION-MODEL.md) and `qlive/encryption.py`.

---

## Implementation

- `qlive/chunk.py` — `Chunk`, `create_chunk`, serialization, sign/verify.
- Constants: `MAGIC = b"QLIV"`, `HEADER_SIZE = 155`, `DEFAULT_FRAGMENT_MS = 1000`.

*See [protocol.md](protocol.md) §3 for the full specification.*
