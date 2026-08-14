"""Discrete-event simulation of the QLive delivery swarm.

Models the dual-layer swarm protocol (push-based delivery tree + pull-based
local mesh) at the chunk level, so design questions — tree fanout, mesh size,
retransmission timing, buffer sizing, churn and parent-drop resilience, and
free-rider impact — can be answered with measured results rather than
speculation.

This is a *simplified* model: it captures protocol semantics (tree push, mesh
pull, sliding-window buffering, retransmission) but abstracts the transport
layer (edges have fixed latency and a loss probability, not real sockets).

The simulation is deterministic given a seed, fully offline, and pure Python.
"""

from __future__ import annotations

import heapq
import random
from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SimConfig:
    """Parameters for a single simulation run."""

    num_viewers: int = 100
    fragment_ms: int = 1000
    duration_ms: int = 60_000
    fanout: int = 8
    mesh_size: int = 4
    hop_latency_ms: int = 50
    loss_rate: float = 0.0
    retransmit_rtt_ms: int = 200
    retransmit_attempts: int = 3
    buffer_window_ms: int = 45_000
    churn_per_second: float = 0.0
    parent_drop_per_second: float = 0.0
    free_rider_fraction: float = 0.0
    seed: int = 0

    def __post_init__(self) -> None:
        if self.fanout < 1:
            raise ValueError("fanout must be >= 1")
        if not 0.0 <= self.loss_rate <= 1.0:
            raise ValueError("loss_rate must be in [0, 1]")
        if not 0.0 <= self.free_rider_fraction <= 1.0:
            raise ValueError("free_rider_fraction must be in [0, 1]")
        if self.buffer_window_ms < self.fragment_ms:
            raise ValueError("buffer_window_ms must be >= fragment_ms")

    @property
    def total_chunks(self) -> int:
        return self.duration_ms // self.fragment_ms


@dataclass
class SimResults:
    """Aggregate metrics for a completed simulation."""

    num_nodes: int
    total_chunks: int
    delivery_rate: float
    recovery_rate: float
    e2e_latency_ms: float
    recovery_latency_ms: float
    tree_depth: int
    mean_direct: float
    mean_recovered: float
    mean_missed: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "num_nodes": self.num_nodes,
            "total_chunks": self.total_chunks,
            "delivery_rate": self.delivery_rate,
            "recovery_rate": self.recovery_rate,
            "e2e_latency_ms": self.e2e_latency_ms,
            "recovery_latency_ms": self.recovery_latency_ms,
            "tree_depth": self.tree_depth,
            "mean_direct": self.mean_direct,
            "mean_recovered": self.mean_recovered,
            "mean_missed": self.mean_missed,
        }


@dataclass
class SimNode:
    """A single node in the simulated swarm."""

    node_id: str
    is_relay: bool = False
    free_rider: bool = False
    parent: str | None = None
    children: list[str] = field(default_factory=list)
    mesh_peers: list[str] = field(default_factory=list)
    received: set[int] = field(default_factory=set)
    pending: set[int] = field(default_factory=set)
    direct_count: int = 0
    recovered_count: int = 0
    direct_latency_sum: float = 0.0
    recovery_latency_sum: float = 0.0
    last_contiguous: int = 0
    alive: bool = True


class Simulation:
    """A discrete-event simulation of chunk delivery through the swarm."""

    BROADCASTER_ID = "b0"

    def __init__(self, config: SimConfig) -> None:
        self.config = config
        self.rng = random.Random(config.seed)
        self.nodes: dict[str, SimNode] = {}
        self._events: list[tuple[float, int, Any]] = []
        self._counter = 0
        self.time = 0.0
        self._next_viewer = 0

    # ---- public API -----------------------------------------------------

    def run(self) -> SimResults:
        self._setup_topology()
        self._schedule_emits()
        self._schedule_churn()

        end_time = self.config.duration_ms + self.config.buffer_window_ms
        while self._events:
            time, _, payload = heapq.heappop(self._events)
            if time > end_time:
                break
            self.time = time
            self._dispatch(payload)

        return self._results()

    # ---- setup ----------------------------------------------------------

    def _setup_topology(self) -> None:
        broadcaster = SimNode(self.BROADCASTER_ID, is_relay=True)
        self.nodes[self.BROADCASTER_ID] = broadcaster

        for _ in range(self.config.num_viewers):
            self._join_node(self._new_viewer_id())

        leaves = [
            n for n in self.nodes.values() if n.node_id != self.BROADCASTER_ID and not n.is_relay
        ]
        n_free = int(len(leaves) * self.config.free_rider_fraction)
        for node in self.rng.sample(leaves, n_free):
            node.free_rider = True

        self._wire_mesh()

    def _join_node(self, node_id: str) -> SimNode:
        node = SimNode(node_id)
        self.nodes[node_id] = node
        parent = self._find_parent()
        if parent is not None:
            node.parent = parent.node_id
            parent.children.append(node_id)
            parent.is_relay = True
        else:
            node.parent = self.BROADCASTER_ID
            self.nodes[self.BROADCASTER_ID].children.append(node_id)
        return node

    def _wire_mesh(self) -> None:
        ids = [n.node_id for n in self.nodes.values() if n.node_id != self.BROADCASTER_ID]
        for node_id in ids:
            node = self.nodes[node_id]
            candidates = [p for p in ids if p != node_id]
            node.mesh_peers = self.rng.sample(
                candidates, min(self.config.mesh_size, len(candidates))
            )

    def _schedule_emits(self) -> None:
        for seq in range(1, self.config.total_chunks + 1):
            self._push((seq - 1) * self.config.fragment_ms, ("emit", seq))

    def _schedule_churn(self) -> None:
        duration = self.config.duration_ms

        def alive_leaves() -> list[SimNode]:
            return [
                n
                for n in self.nodes.values()
                if n.node_id != self.BROADCASTER_ID and not n.is_relay and n.alive
            ]

        def alive_relays() -> list[SimNode]:
            return [
                n
                for n in self.nodes.values()
                if n.node_id != self.BROADCASTER_ID and n.is_relay and n.alive
            ]

        n_churn = int(self.config.churn_per_second * duration / 1000)
        for _ in range(n_churn):
            t = self.rng.uniform(0, duration)
            leaves = alive_leaves()
            if leaves:
                self._push(t, ("leave", self.rng.choice(leaves).node_id))
                self._push(t, ("join", self._new_viewer_id()))

        n_drop = int(self.config.parent_drop_per_second * duration / 1000)
        for _ in range(n_drop):
            t = self.rng.uniform(0, duration)
            relays = alive_relays()
            if relays:
                self._push(t, ("leave", self.rng.choice(relays).node_id))

    # ---- event helpers --------------------------------------------------

    def _push(self, time: float, payload: Any) -> None:
        self._counter += 1
        heapq.heappush(self._events, (time, self._counter, payload))

    def _dispatch(self, payload: Any) -> None:
        kind = payload[0]
        if kind == "emit":
            self._on_emit(payload[1])
        elif kind == "arrive":
            self._on_arrive(payload[1], payload[2])
        elif kind == "retransmit":
            self._on_retransmit(payload[1], payload[2], payload[3])
        elif kind == "leave":
            self._on_leave(payload[1])
        elif kind == "join":
            self._on_join(payload[1])

    # ---- event handlers -------------------------------------------------

    def _on_emit(self, seq: int) -> None:
        for child_id in list(self.nodes[self.BROADCASTER_ID].children):
            self._forward(child_id, seq)

    def _forward(self, node_id: str, seq: int) -> None:
        if self.rng.random() < self.config.loss_rate:
            return
        self._push(self.time + self.config.hop_latency_ms, ("arrive", node_id, seq))

    def _on_arrive(self, node_id: str, seq: int) -> None:
        node = self.nodes[node_id]
        if not node.alive or seq in node.received:
            return

        node.received.add(seq)
        node.direct_count += 1
        node.direct_latency_sum += self.time - self._emit_time(seq)

        if seq > node.last_contiguous + 1:
            for missing in range(node.last_contiguous + 1, seq):
                if missing not in node.pending:
                    node.pending.add(missing)
                    self._push(
                        self.time + self.config.retransmit_rtt_ms,
                        ("retransmit", node_id, missing, 1),
                    )
        self._advance_contiguous(node)

        for child_id in list(node.children):
            self._forward(child_id, seq)

    def _on_retransmit(self, node_id: str, seq: int, attempt: int) -> None:
        node = self.nodes[node_id]
        if not node.alive or seq in node.received:
            node.pending.discard(seq)
            self._advance_contiguous(node)
            return

        if not self._recoverable(seq):
            node.pending.discard(seq)
            return

        peers = [p for p in node.mesh_peers if self.nodes[p].alive]
        if peers:
            peer = self.rng.choice(peers)
            peer_node = self.nodes[peer]
            if not peer_node.free_rider and seq in peer_node.received:
                node.received.add(seq)
                node.recovered_count += 1
                node.recovery_latency_sum += self.time - self._emit_time(seq)
                node.pending.discard(seq)
                self._advance_contiguous(node)
                return

        if attempt < self.config.retransmit_attempts:
            self._push(
                self.time + self.config.retransmit_rtt_ms,
                ("retransmit", node_id, seq, attempt + 1),
            )
        else:
            node.pending.discard(seq)

    def _on_leave(self, node_id: str) -> None:
        node = self.nodes[node_id]
        if not node.alive:
            return
        node.alive = False

        if node.parent is not None:
            parent = self.nodes.get(node.parent)
            if parent is not None and node_id in parent.children:
                parent.children.remove(node_id)

        for child_id in list(node.children):
            child = self.nodes[child_id]
            child.parent = None
            new_parent = self._find_parent()
            if new_parent is not None:
                child.parent = new_parent.node_id
                new_parent.children.append(child_id)
                new_parent.is_relay = True
            else:
                child.parent = self.BROADCASTER_ID
                self.nodes[self.BROADCASTER_ID].children.append(child_id)
        node.children.clear()

    def _on_join(self, node_id: str) -> None:
        self._join_node(node_id)
        self._wire_mesh()

    # ---- helpers --------------------------------------------------------

    def _advance_contiguous(self, node: SimNode) -> None:
        while node.last_contiguous + 1 in node.received:
            node.last_contiguous += 1

    def _find_parent(self) -> SimNode | None:
        queue: deque[str] = deque([self.BROADCASTER_ID])
        while queue:
            node_id = queue.popleft()
            node = self.nodes[node_id]
            if node.alive and len(node.children) < self.config.fanout:
                return node
            queue.extend(node.children)
        return None

    def _emit_time(self, seq: int) -> float:
        return (seq - 1) * self.config.fragment_ms

    def _recoverable(self, seq: int) -> bool:
        return self.time <= self._emit_time(seq) + self.config.buffer_window_ms

    def _new_viewer_id(self) -> str:
        vid = self._next_viewer
        self._next_viewer += 1
        return f"v{vid}"

    # ---- results --------------------------------------------------------

    def _results(self) -> SimResults:
        total = self.config.total_chunks
        viewers = [n for n in self.nodes.values() if n.node_id != self.BROADCASTER_ID]

        total_direct = sum(n.direct_count for n in viewers)
        total_recovered = sum(n.recovered_count for n in viewers)
        total_missed = sum(total - n.direct_count - n.recovered_count for n in viewers)

        delivery_rate = (total_direct + total_recovered) / (total * len(viewers))
        recovery_rate = total_recovered / max(1, total_recovered + total_missed)
        e2e_latency = sum(n.direct_latency_sum for n in viewers) / max(1, total_direct)
        recovery_latency = sum(n.recovery_latency_sum for n in viewers) / max(1, total_recovered)

        return SimResults(
            num_nodes=len(self.nodes),
            total_chunks=total,
            delivery_rate=delivery_rate,
            recovery_rate=recovery_rate,
            e2e_latency_ms=e2e_latency,
            recovery_latency_ms=recovery_latency,
            tree_depth=self._tree_depth(),
            mean_direct=total_direct / len(viewers),
            mean_recovered=total_recovered / len(viewers),
            mean_missed=total_missed / len(viewers),
        )

    def _tree_depth(self) -> int:
        def depth(node_id: str) -> int:
            node = self.nodes[node_id]
            if not node.children:
                return 0
            return 1 + max(depth(c) for c in node.children)

        return depth(self.BROADCASTER_ID)


def run_sweep(
    base: SimConfig,
    param: str,
    values: list[Any],
) -> list[tuple[Any, SimResults]]:
    """Run the same simulation varying a single parameter.

    Args:
        base: Baseline configuration.
        param: The config field name to vary.
        values: The values to sweep over.

    Returns:
        A list of ``(value, results)`` pairs.
    """
    out: list[tuple[Any, SimResults]] = []
    for value in values:
        config = SimConfig(**{**base.__dict__, param: value})
        out.append((value, Simulation(config).run()))
    return out
