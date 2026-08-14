# Security Policy

## Supported Versions

QLive is in early design/development. No stable releases exist yet. Security support applies to the latest development state on the `main` branch.

| Version | Supported |
| --- | --- |
| main (dev) | ✅ |
| < 0.1.0 | ❌ |

---

## Reporting a Vulnerability

**Please do NOT open a public issue for security vulnerabilities.**

Instead, report vulnerabilities privately to:

- **Email:** mike@pikeaero.com
- **Subject:** `[QLive Security] <brief description>`

### What to include

- **Description** of the vulnerability
- **Severity** assessment (if known)
- **Steps to reproduce** or proof of concept
- **Affected components** (transport, signaling, buffer, etc.)
- **Suggested fix** (if you have one)

### Response expectations

- **Acknowledgment:** Within 48 hours
- **Initial assessment:** Within 1 week
- **Fix timeline:** Depends on severity and complexity

---

## Security Considerations for QLive

QLive is a decentralized P2P live-streaming protocol. Security is critical. Key threat areas:

### 1. Chunk Injection / Stream Spoofing
- **Threat:** Malicious peers inject fake video chunks into the swarm.
- **Mitigation:** Cryptographic in-flight signing — each chunk is signed by the broadcaster's Qortal Name/Key pair. Viewer nodes verify signatures in real time.

### 2. Denial of Service (DoS)
- **Threat:** Peers flood the swarm with garbage data or connection requests.
- **Mitigation:** Tit-for-tat bandwidth accounting, rate limiting, peer reputation.

### 3. Free-Riding
- **Threat:** Peers consume bandwidth without contributing.
- **Mitigation:** Tit-for-tat data swapping, proof-of-relay receipts.

### 4. Privacy / Eavesdropping
- **Threat:** Unauthorized parties intercept private streams.
- **Mitigation:** Per-stream encryption keys distributed via QDN signaling.

### 5. Sybil Attacks
- **Threat:** Attackers create many fake nodes to dominate the swarm.
- **Mitigation:** Qortal Name identity binding, reputation systems.

### 6. Storage Bloat
- **Threat:** Malicious streams force nodes to store excessive data.
- **Mitigation:** RAM-only sliding-window buffering with strict eviction.

---

## Security Best Practices for Contributors

- Never commit secrets, keys, or credentials
- Use `.env` files for local configuration (gitignored)
- Sanitize all user input
- Validate all network data before processing
- Use constant-time comparison for signature verification
- Keep dependencies updated
- Run security linters (bandit for Python, npm audit for JS, etc.)

---

## Disclosure Policy

We follow responsible disclosure:

1. Reporter privately notifies maintainers
2. Maintainers acknowledge and assess
3. Fix is developed and tested
4. Fix is released
5. Vulnerability is publicly disclosed after the fix is available

---

*Security is a shared responsibility. Report responsibly, patch promptly.*