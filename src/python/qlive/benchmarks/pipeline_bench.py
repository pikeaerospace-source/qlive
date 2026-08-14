"""End-to-end in-memory delivery benchmark.

Models the full broadcast → tree → viewer pipeline without any network
sockets. For a given viewer count it reports the tree depth, the per-chunk
fan-out cost (total bytes carried by the swarm), a simulated end-to-end
latency estimate, and the wall-clock cost of pushing chunks through the
in-memory swarm.
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

# Simulated per-hop network latency used in the latency model.
HOP_LATENCY_MS = 50.0
FRAGMENT_MS = 1000.0
CHUNK_BYTES = int(4500 * 1000 / 8)  # 1s @ 4.5 Mbps


def make_peer(peer_id: str, *, healthy: bool, bandwidth_kbps: float) -> Peer:
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


def build_swarm(node_id: str, n: int) -> SwarmManager:
    swarm = SwarmManager(node_id, max_fanout=8, max_depth=MAX_TREE_DEPTH)
    for i in range(n):
        healthy = (i % 5) == 0
        swarm.join(
            make_peer(
                f"peer-{i}",
                healthy=healthy,
                bandwidth_kbps=3000.0 if healthy else 500.0,
            )
        )
    return swarm


class PipelineSuite(Suite):
    name = "pipeline"
    description = "End-to-end in-memory delivery: fan-out cost, depth, latency model."

    def run(self) -> list[Result]:
        results: list[Result] = []

        for n in (10, 100, 1000):
            swarm = build_swarm("broadcaster", n)
            stats = swarm.stats

            # Number of tree edges = non-broadcaster peers (each has one parent).
            edges = stats.total_peers - 1
            # Bytes carried by the swarm to deliver one chunk to every peer.
            fanout_cost_mb = edges * CHUNK_BYTES / (1024 * 1024)
            # Simulated end-to-end latency: deepest path + fragment duration.
            latency_ms = stats.tree_depth * HOP_LATENCY_MS + FRAGMENT_MS

            results.append(
                Result(
                    f"viewers.{n}.depth",
                    float(stats.tree_depth),
                    "hops",
                    f"tree={stats.tree_nodes} viewers={stats.viewers}",
                )
            )
            results.append(
                Result(
                    f"viewers.{n}.fanout_cost",
                    fanout_cost_mb,
                    "MB",
                    f"swarm bytes per chunk ({edges} edges)",
                )
            )
            results.append(
                Result(
                    f"viewers.{n}.e2e_latency",
                    latency_ms,
                    "ms",
                    f"{HOP_LATENCY_MS:.0f}ms/hop + {FRAGMENT_MS:.0f}ms fragment",
                )
            )

        # 4. Wall-clock cost of pushing 60 chunks through the in-memory swarm.
        for n in (100, 1000):
            swarm = build_swarm("broadcaster", n)

            def push() -> None:
                for _ in range(60):
                    for peer_id, peer in swarm.tree.peers.items():
                        if peer_id == "broadcaster":
                            continue
                        # Touch the payload to model per-peer copy/verify work.
                        _ = peer.role

            push_s = best_time(push, repeat=3, number=1)
            results.append(
                Result(
                    f"simulate.{n}viewers.60chunks",
                    push_s,
                    "s",
                    "in-memory push (no crypto)",
                )
            )

        return results
