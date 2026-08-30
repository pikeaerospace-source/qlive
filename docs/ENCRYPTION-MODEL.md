# ENCRYPTION-MODEL — Research

**Research task:** Per-stream symmetric keys vs. per-viewer asymmetric keys? Key rotation strategy?

**Status:** In progress (`[~]`)

**Related:** [protocol.md](protocol.md) §8.2, `src/python/qlive/chunk.py`, `src/python/qlive/signaling.py`, [TODO-RESEARCH.md](../TODO-RESEARCH.md) → Security Research

---

## Status Legend

- `[ ]` — Not started
- `[~]` — In progress
- `[x]` — Complete

---

## Research Questions

- [~] Per-stream symmetric keys vs. per-viewer asymmetric keys?
- [~] Key rotation strategy (frequency, mechanism)?
- [~] Public (signed-only) vs. private (encrypted) streams — support both?
- [x] Quantify encryption throughput (AES-256-GCM).
- [x] Quantify signing cost and identify a scaling problem in the current design.
- [x] Sign only the header (which embeds the payload hash) instead of the full payload — implemented in `chunk.py` (constant-cost sign/verify; see §3)
- [ ] Design key distribution for private streams (QDN-encrypted key envelopes).

---

## Findings

### 1. Encryption throughput (AES-256-GCM, measured)

| Payload | Encrypt | Decrypt |
| --- | --- | --- |
| 1 MB | 810 MB/s | 1116 MB/s |
| 10 MB | 868 MB/s | 878 MB/s |

AES-256-GCM is far faster than any realistic stream bitrate (≤ 6 Mbps = 0.75 MB/s). Encryption adds a **16-byte authentication tag** per chunk (negligible). Per-chunk AES-GCM encryption/decryption is a non-issue for throughput.

### 2. Signing cost scales with payload size (measured)

| Bitrate (1s chunk) | Payload | Sign | Verify |
| --- | --- | --- | --- |
| 1000 kbps | 125 KB | 388 µs | 281 µs |
| 4500 kbps | 562 KB | 1480 µs | 959 µs |
| 6000 kbps | 750 KB | 1986 µs | 1222 µs |

**Problem (resolved 2026-08-30):** `Chunk.signing_data` previously covered `header + payload` (the full payload), so Ed25519 sign/verify cost grew linearly with bitrate. This was unnecessary — the header already contains a SHA-256 `payload_hash`.

**Recommendation:** Sign only `header` (which includes `payload_hash`), not the full payload. This makes sign/verify cost **constant** (~50–100 µs) regardless of payload size, and preserves integrity (tampering with the payload changes its hash, which is covered by the signature).

### 3. Current state of the code

- `chunk.py` sign/verify now covers **only the header** (91 bytes, which embeds
  the SHA-256 `payload_hash`), implementing the §5 recommendation — Ed25519
  sign/verify cost is constant regardless of bitrate.
- `signaling.py` has an `EncryptionInfo` dataclass (`enabled`, `key_id`) but no
  actual encryption implementation yet.
- `protocol.md` §8.2 specifies AES-256-GCM with keys distributed via QDN,
  rotated every 5–10 min.

---

## Analysis: Symmetric vs. Asymmetric

| Model | Pros | Cons |
| --- | --- | --- |
| **Per-stream symmetric (AES-256-GCM)** | One key per stream; fast; constant per-chunk cost; simple relay model (relays don't need the key) | Key must be distributed to all authorized viewers; revocation = re-key + re-distribute |
| **Per-viewer asymmetric (e.g., ECIES/HPKE per viewer)** | Per-viewer revocation is trivial; no shared secret | Re-encrypting every chunk for every viewer is O(viewers) and destroys the multicast/tree efficiency; impractical for a relay swarm |
| **Hybrid (recommended)** | Symmetric stream key + per-viewer key envelopes | Best of both; standard practice (like HLS/DRM) |

**Conclusion:** Per-stream **symmetric** encryption is the only model that preserves the tree/mesh multicast efficiency (relays forward ciphertext without decrypting). Per-viewer asymmetric encryption would require per-viewer ciphertext and defeat the entire swarm architecture.

---

## Recommendation

1. **Use a per-stream symmetric key (AES-256-GCM)** for private streams.
2. **Distribute the key via QDN** as a key envelope encrypted to each authorized viewer's public key (hybrid: symmetric stream key wrapped in per-viewer asymmetric envelopes). This keeps the data plane multicast-efficient while enabling per-viewer authorization.
3. **Rotate the key every 5–10 minutes** (as already specified). Each rotation publishes a new key envelope set to QDN; viewers fetch the new key before the old one expires. Use a `key_id` in the chunk header (or metadata) so viewers know which key to use.
4. **Support both public and private streams:**
   - Public: signed-only (no encryption), key distribution N/A.
   - Private: signed + encrypted (AES-256-GCM), key-gated via QDN envelopes.
5. **Fix signing to cover only the payload hash** (see §2). This is a prerequisite for cheap high-bitrate operation and reduces CPU on relays that verify every chunk.
6. **Keep the header plaintext** for routing/verification; encrypt only the payload (already specified in §8.2).

---

## Test Results

Benchmark harness: `/tmp/qlive_research_bench.py` (sections 2, 5). Full test suite: **266 passed**.

---

## Open Questions

- [ ] What asymmetric scheme for key envelopes — X25519 + HKDF (HPKE), or ECIES over secp256k1 (to reuse Qortal keys)?
- [ ] How to handle mid-stream viewer revocation (a viewer authorized at start but revoked later)? Re-key + re-distribute is the only robust option; document the cost.
- [ ] Should key rotation be time-based (5–10 min) or event-based (on membership change)?
- [ ] Is the Qortal Name key pair (Ed25519) suitable for both signing and key-envelope encryption, or should a separate encryption key be used?

---

## Decisions Log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-08-14 | Per-stream symmetric AES-256-GCM + hybrid key envelopes | Preserves multicast efficiency; enables per-viewer authorization |
| 2026-08-14 | Sign payload hash, not payload | Makes sign/verify cost constant; removes bitrate-scaling cost |

---

*This document is a living artifact. Update it as the key-distribution design is implemented.*
