# Swarm Protocol

**Status:** Reference — mirrors `qlive/swarm.py` and `protocol.md` §5.

The swarm is a dual-layer **tree + mesh** hybrid.

---

## Primary Delivery Tree

- High-capacity, high-uptime peers form a push-based tree from the broadcaster.
- `DEFAULT_TREE_FANOUT = 8`, `MAX_TREE_DEPTH = 5`.
- Capacity-based node selection: the shallowest node with room wins.

## Secondary Local Mesh

- Nearby viewers exchange missing fragments over pull-based data channels.
- `MESH_PEERS_MIN = 4`, `MESH_PEERS_MAX = 16`.

## Fallback

When a tree parent drops, the affected node falls back to pulling from its
mesh, then reattaches to the tree (see `DeliveryTree.remove_peer`).

## Peer Health

A peer is healthy if `latency ≤ 500 ms`, `packet_loss ≤ 5%`,
`uptime ≥ 60 s`, `bandwidth ≥ 1 Mbps`; tree-eligible at `≥ 2 Mbps`.

---

## Tuning (from SWARM-SIMULATION.md)

- Fanout **8** default (depth 3, ~130 ms); mesh size **4–8** (97–100% recovery).
- Parent drops cost more than leaf churn; relay stability is the priority.

---

## Implementation

- `qlive/swarm.py` — `Peer`, `PeerHealth`, `DeliveryTree`, `SwarmManager`.
- `qlive/simulation.py` — the discrete-event model used for tuning.

*See [protocol.md](protocol.md) §5 for the full specification.*
