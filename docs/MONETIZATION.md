# QLive Monetization & QORT Token Economy

**Status:** Draft v0.2.0 — subject to change during Phase 4 (Incentives) implementation.

When evaluating the **QORT token economy** for a live-streaming protocol on Qortal, the core goal is balancing sustainability for content creators, bandwidth node providers, and viewers—without making live streaming cost-prohibitive or vulnerable to spam.

Here is how QORT spending and tokenomics would break down across the system:

---

## Table of Contents

- [1. Publishing Costs: On-Chain Signaling vs. Off-Chain Ephemeral Data](#1-publishing-costs-on-chain-signaling-vs-off-chain-ephemeral-data)
- [2. Monetization & Value Flow for Streamers](#2-monetization--value-flow-for-streamers)
- [3. Bandwidth Incentives & P2P Node Costs (Proof-of-Relay)](#3-bandwidth-incentives--p2p-node-costs-proof-of-relay)
- [4. Free-Rider & Spam Prevention](#4-free-rider--spam-prevention)
- [5. QORT Burn vs. Transfer](#5-qort-burn-vs-transfer)
- [6. Streamer Revenue Split](#6-streamer-revenue-split)
- [7. Creator Economy Tiers](#7-creator-economy-tiers)
- [8. Economic Attack Vectors](#8-economic-attack-vectors)
- [9. Dispute Resolution](#9-dispute-resolution)
- [10. Analytics & Transparency](#10-analytics--transparency)
- [11. Minimum Viable Economics](#11-minimum-viable-economics)
- [12. Reputation-Based Pricing](#12-reputation-based-pricing)
- [Summary of QORT Flow](#summary-of-qort-flow)

---

## 1. Publishing Costs: On-Chain Signaling vs. Off-Chain Ephemeral Data

In standard QDN operations, publishing a site, app, or Q-Tube video incurs a **fractional QORT transaction fee** to register the data build/manifest on-chain, while the static data chunks are hosted for free by peer nodes holding or serving that content.

For a live stream, paying a QORT transaction fee for every single video fragment (e.g., every 1-second CMAF slice) would be economically impossible and clog the blockchain.

* **Stream Registration Fee (Micro-QORT):** The broadcaster pays a single, nominal QORT transaction fee (e.g., 0.001–0.01 QORT) to broadcast a `START_STREAM` transaction under their registered Qortal Name. This registers the active stream metadata, encryption keys, and seed relays on-chain.
* **Ephemeral In-Flight Data (0 QORT Chain Fee):** Real-time video fragments sent over the ephemeral P2P overlay bypass the ledger entirely. Broadcasters do not pay on-chain fees per second of streaming.
* **Optional VOD Archival Fee:** If the streamer chooses to automatically save the live stream to Q-Tube upon finishing, a standard QDN publishing fee applies once to register the final stitched manifest.

---

## 2. Monetization & Value Flow for Streamers

Streaming on Qortal opens up native, direct Web3 monetization mechanisms without middleman platforms taking a 30%–50% cut:

```
┌─────────────────────────────────────────────────────────────┐
│                    Viewer Payment Options                   │
├──────────────────────────┬──────────────────────────────────┤
│ Free / Public Stream     │ Sponsored by Tips & Superchats   │
│ Direct QORT Tipping      │ Real-Time Per-Second Microtips   │
│ Paid Token-Gated Stream  │ Dynamic Access Key (Pay-Per-View)│
└──────────────────────────┴──────────────────────────────────┘

```

* **Direct Micro-Tipping / Superchats:** Viewers send direct QORT tips to the broadcaster's Qortal Name during the stream via low-friction, fast-settlement transactions. Tips are batched and settled on-chain periodically (e.g., every 5 minutes) to minimize transaction overhead while maintaining near-real-time feel.
* **Pay-Per-View / Subscriber Gating:** Broadcasters can encrypt the stream's symmetric key. To decrypt and join the ephemeral swarm, a viewer's node executes a smart contract / API call paying a set QORT fee to the creator to receive the stream key.
* **Micro-Subscriptions:** Instead of monthly flat fees, viewers could stream micro-fractions of QORT per minute of watching using state channels. State channels allow off-chain balance updates with a single on-chain settlement at the end of the session.

### Pay-Per-View Key Distribution Flow

```
Viewer → Pays QORT → Receives Encrypted Stream Key → Joins Swarm
   │                    │                              │
   │                    │                              └─ Key is bound to
   │                    │                                 viewer's Qortal Name
   │                    └─ Key expires after stream ends
   └─ Payment recorded on-chain
```

**Key sharing prevention:** Each stream key is bound to the viewer's Qortal Name and includes a unique viewer nonce. If a key is shared, the broadcaster can revoke it mid-stream by rotating the stream key (per protocol spec section 8.2). Key rotation happens every 5–10 minutes, limiting the damage of key leakage.

---

## 3. Bandwidth Incentives & P2P Node Costs (Proof-of-Relay)

The biggest cost in live video isn't computing—it's **outbound bandwidth**. If nodes relay gigabytes of live stream traffic for free, high-bandwidth seeders will bear all the cost.

* **Free Tier (Community Relay):** Minting nodes and high-tier community members can opt in to relay public streams for free as part of supporting the Qortal network infrastructure.
* **Bandwidth Rewards (Proof-of-Relay):** To encourage high-speed relay nodes (especially for large streams with thousands of viewers), viewers or the broadcaster can allocate a **QORT Bounty Pool**.
* As nodes relay verified video chunks to downstream peers, they collect signed cryptographic bandwidth receipts from those peers.
* At regular intervals or stream conclusion, nodes redeem these receipts against the stream's bounty pool to earn QORT proportional to the megabytes successfully served.

### Receipt Verification

- Each receipt includes: relay node ID, downstream node ID, bytes relayed, timestamp, and a signature from the downstream node
- Receipts are verified against the stream's chunk sequence to prevent fake claims
- Only receipts for chunks that exist in the stream's hash chain are valid
- Receipts are batched and submitted for redemption at stream end

---

## 4. Free-Rider & Spam Prevention

Without centralized servers to rate-limit users, spam prevention relies on crypto-economic barriers:

| Attack / Abuse Scenario | QORT Economic Mitigation |
| --- | --- |
| **Stream Spamming / Sybil Streams** | Requiring a minimal QORT deposit or name ownership fee to open an active `START_STREAM` channel prevents bots from opening thousands of junk streams. |
| **Bandwidth Leeching** | Peer-to-peer swarms enforce "tit-for-tat" data sharing. Nodes that upload zero data or do not hold minimum QORT/Minting status are deprioritized by relay nodes. |
| **Malicious Chunk Injection** | Since each live chunk is signed by the broadcaster's key, malicious nodes trying to serve corrupted data are immediately banned by peer nodes without wasting QORT on-chain. |

---

## 5. QORT Burn vs. Transfer

A critical design decision is whether the `START_STREAM` registration fee is **burned** (deflationary) or **transferred** to a network treasury.

| Model | Pros | Cons |
| --- | --- | --- |
| **Burn** | Deflationary pressure on QORT supply; simple; no governance needed | No funds for network development |
| **Treasury** | Funds network development, relay incentives, and community grants | Requires governance; potential for misuse |
| **Hybrid (50/50)** | Balanced approach; some deflation + some treasury funding | More complex accounting |

**Recommendation:** Start with a **hybrid model** — 50% burned, 50% to a QLive development treasury. This can be adjusted via community governance as the ecosystem matures.

---

## 6. Streamer Revenue Split

When a stream generates revenue (tips, PPV, subscriptions), the default split should be:

| Recipient | Share | Purpose |
| --- | --- | --- |
| **Streamer** | 80% | Content creator compensation |
| **Relay Nodes** | 15% | Bandwidth infrastructure compensation |
| **Network Treasury** | 5% | Protocol development and maintenance |

This split is a **default** — streamers can adjust the relay node share upward to attract more relay capacity for large streams. The split is defined in the stream metadata and enforced by the smart contract that distributes revenue.

---

## 7. Creator Economy Tiers

Different streamers have different monetization needs. QLive should support three tiers:

| Tier | Monetization Options | Requirements |
| --- | --- | --- |
| **Free / Community** | Tips, superchats | Registered Qortal Name |
| **Supporter** | Tips + subscriber-only chat + early access to VOD | Minimum QORT stake or reputation score |
| **Premium** | Pay-Per-View, token-gated streams, micro-subscriptions | Verified identity, established reputation, minimum QORT deposit |

Tiers are not fixed — streamers can upgrade as their reputation and audience grow. The tier system creates a natural progression path for creators.

---

## 8. Economic Attack Vectors

Beyond the basic spam prevention, the economy must defend against more sophisticated attacks:

| Attack | Description | Mitigation |
| --- | --- | --- |
| **Fake Relay Receipts** | Nodes collude to generate fake bandwidth receipts | Receipts must reference actual chunks from the stream's hash chain; random sampling verification |
| **Key Reselling** | A viewer shares their PPV stream key with others | Keys bound to Qortal Name + viewer nonce; periodic key rotation; broadcaster can revoke |
| **Colluding Viewers** | A group of viewers colludes to split a single PPV payment | Key rotation limits simultaneous viewers per key; rate limiting on key requests |
| **Bounty Pool Draining** | Malicious nodes claim relay rewards without serving data | Receipts verified against chunk delivery logs; delayed redemption (e.g., 24h) allows dispute window |
| **Tip Fraud** | Fake tips to inflate streamer reputation | Tips are on-chain and verifiable; reputation is based on verified on-chain activity |
| **Sybil Relay Nodes** | Attackers create many fake relay nodes to capture bounty pool | Relay nodes must have minimum QORT stake; reputation-weighted relay selection |

---

## 9. Dispute Resolution

When economic disputes arise, there must be a clear resolution path:

1. **Automated Verification:** Most disputes (e.g., fake receipts) are resolved automatically by the protocol's verification mechanisms.
2. **Community Arbitration:** For disputes that require human judgment (e.g., "streamer took payment but didn't deliver"), a community arbitration pool of trusted Qortal members reviews evidence.
3. **Slashing:** Nodes found to be acting maliciously have their QORT stake slashed. The slashed amount goes to the dispute reporter as a bounty.
4. **Appeal:** Arbitrated decisions can be appealed to a higher tier of arbitrators within a 7-day window.

---

## 10. Analytics & Transparency

For the economy to function, participants need visibility into the value flow:

- **Streamer Dashboard:** Real-time earnings from tips, PPV, and subscriptions; viewer count; relay node contributions
- **Relay Node Dashboard:** Bandwidth served, receipts collected, QORT earned per stream
- **Public Ledger:** All economic transactions (tips, PPV payments, relay redemptions) are on-chain and publicly verifiable
- **Reputation Scores:** Publicly visible reputation scores for streamers and relay nodes, based on verified on-chain activity

---

## 11. Minimum Viable Economics

To onboard new creators without barriers:

| Item | Minimum QORT | Notes |
| --- | --- | --- |
| **Qortal Name Registration** | ~0.01 QORT | Required for any streaming |
| **START_STREAM Fee** | 0.001–0.01 QORT | Per stream event |
| **VOD Archival Fee** | Standard QDN fee | Only if archiving to Q-Tube |
| **Total to Start Streaming** | **~0.02 QORT** | Negligible barrier to entry |

This ensures that **anyone with a Qortal Name can start streaming** for less than a fraction of a cent, while still providing enough economic friction to prevent spam.

---

## 12. Reputation-Based Pricing

To reward established, trustworthy participants:

- **Streamers** with high reputation scores pay **reduced START_STREAM fees** (e.g., 50% discount at reputation level 3+)
- **Relay nodes** with high reputation get **priority in tree selection** and **higher bounty pool share**
- **Viewers** with good tit-for-tat ratios get **priority bandwidth** from relay nodes
- Reputation is earned through verified on-chain activity and decays over time if not maintained

This creates a positive feedback loop: good actors are rewarded with lower costs and better service, which incentivizes more good behavior.

---

## Summary of QORT Flow

In short, **viewing a standard public stream would remain free for end-users**, while broadcasters would pay only a negligible micro-fee to register the live event on-chain.

The primary QORT expenditure shifts from being a mandatory infrastructure cost (like AWS/Twitch server bills) to a **voluntary value loop**: viewers tipping creators, creators rewarding high-performance relay nodes, or viewers paying QORT for premium/gated live content.

```
                    ┌─────────────────────┐
                    │   QORT Value Loop   │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        ┌──────────┐    ┌──────────┐    ┌──────────┐
        │ Viewers  │───▶│ Streamers│───▶│  Relay   │
        │  (Tips,  │    │  (80%)   │    │  Nodes   │
        │  PPV)    │    └────┬─────┘    │  (15%)   │
        └──────────┘         │          └────┬─────┘
                             │               │
                             ▼               ▼
                       ┌─────────────────────────┐
                       │   Network Treasury (5%) │
                       └─────────────────────────┘
```

---

*This document is a living artifact. Update it as the economy evolves.*