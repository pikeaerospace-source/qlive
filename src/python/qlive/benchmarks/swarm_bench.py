"""Dual-layer swarm benchmarks.

Measures tree/mesh construction scaling, the fanout vs. depth tradeoff,
join/leave churn throughput, and tree reattachment on node removal.
"""

from __future__ import annotations

from qlive.benchmarks.runner import Result, Suite, best_time
from qlive.swarm import (
    MAX_TREE_DEPTH,
    Peer,
    PeerHealth,
    PeerRole,
    PeerState,
    SwarmManager,
)


def make_peer(peer_id: str, *, healthy: bool, bandwidth_kbps: float) -> Peer:
    """Create a connected peer with configurable health."""
    health = PeerHealth(
        latency_ms=50.0 if healthy else 1000.0,
        packet_loss=0.01 if healthy else 0.2,
        uptime_seconds=3600.0 if healthy else 10.0,
        bandwidth_kbps=bandwidth_kbps,
    )
    return Peer(
        peer_id=peer_id,
        role=PeerRole.VIEWER,
        state=PeerState.CONNECTED,
        health=health,
    )


def build_swarm(node_id: str, n: int, *, max_fanout: int = 8) -> SwarmManager:
    """Build a swarm of ``n`` peers where every 5th peer is tree-eligible."""
    swarm = SwarmManager(node_id, max_fanout=max_fanout, max_depth=MAX_TREE_DEPTH)
    for i in range(n):
        healthy = (i % 5) == 0  # 20% tree-eligible
        peer = make_peer(
            f"peer-{i}",
            healthy=healthy,
            bandwidth_kbps=3000.0 if healthy else 500.0,
        )
        swarm.join(peer)
    return swarm


class SwarmSuite(Suite):
    name = "swarm"
    description = "Tree/mesh swarm: construction scaling, fanout, churn, reattachment."

    def run(self, quick: bool = False) -> list[Result]:
        results: list[Result] = []
        build_n = (100, 300) if quick else (100, 1000, 3000)
        fanout_n = 200 if quick else 2000
        warm_n = 50 if quick else 100
        churn_n = 200 if quick else 1000
        reattach_n = 200 if quick else 2000
        drop_number = 20 if quick else 100

        # 1. Construction scaling (join cost is O(n) per peer → O(n^2) total).
        for n in build_n:
            repeat = 3 if n <= 1000 else 1
            build_s = best_time(build_swarm, "broadcaster", n, repeat=repeat, number=1)
            swarm = build_swarm("broadcaster", n)
            stats = swarm.stats
            results.append(
                Result(
                    f"build.n{n}",
                    build_s,
                    "s",
                    f"depth={stats.tree_depth} tree={stats.tree_nodes} viewers={stats.viewers}",
                )
            )

        # 2. Fanout vs. depth for a fixed peer count.
        for fanout in (4, 8, 16):
            swarm = build_swarm("broadcaster", fanout_n, max_fanout=fanout)
            stats = swarm.stats
            results.append(
                Result(
                    f"fanout.{fanout}.depth",
                    float(stats.tree_depth),
                    "hops",
                    f"n={fanout_n} viewers={stats.viewers} tree={stats.tree_nodes}",
                )
            )

        # 3. Churn throughput (join + leave per peer).
        def churn() -> None:
            swarm = SwarmManager("broadcaster")
            for i in range(warm_n):
                swarm.join(make_peer(f"warm-{i}", healthy=False, bandwidth_kbps=500.0))
            for i in range(churn_n):
                peer_id = f"churn-{i}"
                swarm.join(make_peer(peer_id, healthy=False, bandwidth_kbps=500.0))
                swarm.leave(peer_id)

        churn_s = best_time(churn, repeat=3, number=1) / churn_n
        results.append(
            Result("churn.join_leave", churn_s * 1e6, "us", "per join+leave cycle")
        )

        # 4. Tree reattachment on node removal.
        swarm = build_swarm("broadcaster", reattach_n)
        # Drop the first non-broadcaster tree node and reattach its children.
        tree_node_id = next(
            pid for pid, p in swarm.tree.peers.items() if p.is_tree_node
        )

        def drop() -> None:
            swarm.tree.remove_peer(tree_node_id)

        drop_s = best_time(drop, repeat=3, number=drop_number)
        results.append(
            Result(
                "reattach.remove_tree_node",
                drop_s * 1e6,
                "us",
                "remove_peer with child reattachment",
            )
        )

        return results
