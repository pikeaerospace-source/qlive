# THREAT-MODEL — Research

**Research task:** Document the threat model for QLive live streaming and analyze the attack vectors (chunk injection, swarm manipulation, economic attacks).

**Status:** Complete (`[x]`)

**Related:** [protocol.md](protocol.md) §8, [SECURITY-MODEL.md](SECURITY-MODEL.md), `src/python/qlive/chunk.py`, `proof.py`, `incentives.py`

---

## Status Legend

- `[ ]` — Not started
- `[~]` — In progress
- `[x]` — Complete

---

## Assets

| Asset | Security property |
| --- | --- |
| Stream content (video/audio) | Integrity; confidentiality (private streams) |
| Streamer identity (Qortal Name) | Authenticity, non-repudiation |
| Viewer privacy | Confidentiality of viewing activity |
| Node resources (CPU, RAM, bandwidth) | Availability |
| Reputation / rewards (proof-of-relay receipts) | Integrity, non-forgeability |

---

## Actors

- **Broadcaster** — produces and signs chunks.
- **Viewer** — consumes chunks, may serve mesh retransmission.
- **Relay** — forwards chunks down the tree; collects proof-of-relay receipts.
- **Attackers:**
  - *Malicious viewer* — injects chunks, free-rides, floods requests.
  - *Malicious relay* — eclipses, selectively forwards, fabricates receipts.
  - *Sybil attacker* — spins up many identities to dominate a swarm.
  - *Economic attacker* — farms rewards, double-spends receipts.
  - *Passive eavesdropper* — observes traffic.

---

## STRIDE Threat Table

| Threat | QLive manifestation | Mitigation |
| --- | --- | --- |
| **S**poofing | Stream spoofing (fake broadcaster); peer spoofing | Qortal Name identity binding; Ed25519 signatures |
| **T**ampering | Chunk injection / modification | Ed25519 signature + SHA-256 payload hash (`chunk.py`) |
| **R**epudiation | Relay denies serving bytes | Downstream-signed bandwidth receipts (`proof.py`) |
| **I**nfo disclosure | Eavesdropping on private streams | AES-256-GCM per-stream encryption |
| **D**oS | Flooding, resource exhaustion, eclipse | Rate limiting, tit-for-tat, buffer memory ceiling |
| **E**levation of privilege | Sybil identities gaining influence | Qortal Name registration cost |

---

## Attack Vectors

### 1. Chunk injection (Tampering / Spoofing)

An attacker sends forged or modified chunks to a viewer. Each chunk carries an
Ed25519 signature over `header + payload` (the header includes a SHA-256
`payload_hash`). A viewer verifies the signature against the broadcaster's
public key (resolved from the Qortal Name) and rejects any chunk whose
signature or hash fails.

**Residual risk:** a malicious *relay* can still **selectively drop** chunks
(availability, not integrity) — addressed by mesh retransmission (see
SWARM-SIMULATION.md). Signing the full payload (rather than only the hash)
is a known inefficiency, but not a security hole (see ENCRYPTION-MODEL.md).

### 2. Stream spoofing (Spoofing)

An attacker publishes stream metadata under a victim's Qortal Name. Mitigated
by binding metadata to the Qortal Name's key: the stream ID is the SHA-256 of
the metadata, and chunk signatures must match the name's public key. A
spoofer without the name's private key cannot produce valid chunks.

### 3. Swarm manipulation / eclipse (DoS / Spoofing)

An attacker surrounds a victim with malicious peers, cutting it off from the
honest swarm (eclipse). Mitigations: peer lists come from QDN (not the
attacker), mesh peers are diverse, and health checks drop unresponsive peers.

### 4. Sybil (Elevation of privilege)

An attacker creates many identities to dominate a swarm (e.g., to eclipse or
to farm rewards). Mitigated by the **cost of Qortal Name registration** — see
SECURITY-MODEL.md for the cost model.

### 5. Eavesdropping (Info disclosure)

Passive sniffing of chunk traffic. Public streams are signed-only (no
confidentiality). Private streams are encrypted with a per-stream AES-256-GCM
key distributed only to authorized viewers (see SECURITY-MODEL.md).

### 6. DoS (availability)

- **Flooding** — spam chunks/requests. Mitigated by rate limiting and
  tit-for-tat (free-riders are deprioritized/disconnected).
- **Resource exhaustion** — oversized chunks. Mitigated by the buffer memory
  ceiling (`DEFAULT_MAX_MEMORY_BYTES = 256 MB`) and chunk-size validation.

### 7. Economic attacks

- **Receipt forgery** — fabricating proof-of-relay receipts. Mitigated by
  downstream-signed receipts + a 24 h dispute window + a bounded bounty pool
  (see SECURITY-MODEL.md).
- **Free-rider gaming** — contributing just enough to avoid throttling.
  Mitigated by tit-for-tat thresholds (see SECURITY-MODEL.md).
- **Sybil farming** — many identities to farm rewards. Mitigated by the
  registration cost + the bounded bounty pool.

---

## Mitigation Mapping

| Attack | Layer | Mechanism | Where |
| --- | --- | --- | --- |
| Chunk injection | Data | Ed25519 signature + payload hash | `chunk.py` |
| Stream spoofing | Signaling | Qortal Name identity binding | `signaling.py` |
| Selective drop | Data | Mesh retransmission | `retransmit.py`, `simulation.py` |
| Eclipse | Swarm | QDN peer lists, health checks | `swarm.py` |
| Sybil | Identity | Qortal Name registration cost | Qortal Core |
| Eavesdropping | Data | AES-256-GCM (private streams) | (to implement) |
| Flooding | Transport | Rate limiting, tit-for-tat | `incentives.py` |
| Resource exhaustion | Buffer | 256 MB memory ceiling | `buffer.py` |
| Receipt forgery | Incentive | Downstream-signed receipts + dispute window | `proof.py` |
| Free-rider gaming | Incentive | Tit-for-tat thresholds | `incentives.py` |

---

## Open Questions

- [ ] What is the actual Qortal Name registration fee? (Needed to quantify the sybil cost model.)
- [ ] Is the 24 h dispute window long enough for receipt challenges?
- [ ] Should relays be required to post a bond to deter receipt forgery?
- [ ] What rate-limit parameters are appropriate per node?

---

## Decisions Log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-08-14 | Threat model documented (STRIDE + 7 attack vectors) | Foundation for the security research questions |
| 2026-08-14 | Receipt forgery bounded by dispute window + bounty cap | Limits economic upside of fabrication |

---

*This document is a living artifact. Update it as the security model evolves.*

