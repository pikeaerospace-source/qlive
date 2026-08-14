"""QLive dual-layer peer swarm.

Implements the hybrid tree + mesh swarm protocol defined in
docs/protocol.md section 5.

The swarm consists of:
1. **Primary Delivery Tree** — push-based delivery from the broadcaster
   through high-capacity relay nodes
2. **Secondary Local Mesh** — pull-based fragment exchange among nearby
   viewers for resilience when tree parents drop
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# Swarm constants (from docs/protocol.md section 10)
MAX_TREE_DEPTH = 5
DEFAULT_TREE_FANOUT = 8
MESH_PEERS_MIN = 4
MESH_PEERS_MAX = 16

# Peer health thresholds (from docs/protocol.md section 5.4)
MAX_LATENCY_MS = 500
MAX_PACKET_LOSS = 0.05  # 5%
MIN_UPTIME_SECONDS = 60
MIN_BANDWIDTH_KBPS = 1000  # 1 Mbps


class SwarmError(Exception):
    """Base exception for swarm errors."""


class PeerRole(Enum):
    """Roles a peer can have in the swarm."""

    BROADCASTER = "broadcaster"
    TREE_NODE = "tree_node"
    VIEWER = "viewer"


class PeerState(Enum):
    """Peer connection states."""

    DISCOVERED = "discovered"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    BANNED = "banned"


@dataclass
class PeerHealth:
    """Health metrics for a peer."""

    latency_ms: float = 0.0
    packet_loss: float = 0.0
    uptime_seconds: float = 0.0
    bandwidth_kbps: float = 0.0
    last_seen: int = field(default_factory=lambda: int(time.time()))

    @property
    def is_healthy(self) -> bool:
        """Whether the peer meets all health thresholds."""
        return (
            self.latency_ms <= MAX_LATENCY_MS
            and self.packet_loss <= MAX_PACKET_LOSS
            and self.uptime_seconds >= MIN_UPTIME_SECONDS
            and self.bandwidth_kbps >= MIN_BANDWIDTH_KBPS
        )

    @property
    def is_eligible_for_tree(self) -> bool:
        """Whether the peer can serve as a tree node."""
        return self.is_healthy and self.bandwidth_kbps >= MIN_BANDWIDTH_KBPS * 2


@dataclass
class Peer:
    """A peer in the swarm."""

    peer_id: str
    role: PeerRole = PeerRole.VIEWER
    state: PeerState = PeerState.DISCOVERED
    health: PeerHealth = field(default_factory=PeerHealth)
    tree_depth: int = 0
    parent_id: Optional[str] = None
    children: list[str] = field(default_factory=list)
    mesh_peers: list[str] = field(default_factory=list)
    joined_at: int = field(default_factory=lambda: int(time.time()))

    @property
    def is_connected(self) -> bool:
        """Whether the peer is connected."""
        return self.state == PeerState.CONNECTED

    @property
    def is_tree_node(self) -> bool:
        """Whether the peer is a tree node."""
        return self.role == PeerRole.TREE_NODE

    @property
    def child_count(self) -> int:
        """Number of children in the tree."""
        return len(self.children)

    @property
    def mesh_count(self) -> int:
        """Number of mesh peers."""
        return len(self.mesh_peers)

    def can_accept_children(self, max_fanout: int = DEFAULT_TREE_FANOUT) -> bool:
        """Whether the peer can accept more tree children."""
        return self.child_count < max_fanout


@dataclass
class SwarmStats:
    """Statistics for swarm monitoring."""

    total_peers: int = 0
    connected_peers: int = 0
    tree_nodes: int = 0
    viewers: int = 0
    tree_depth: int = 0
    mesh_connections: int = 0
    fallbacks: int = 0


class DeliveryTree:
    """Primary delivery tree for push-based fragment distribution.

    The tree is rooted at the broadcaster and branches through
    high-capacity relay nodes. Each node has a maximum fan-out and
    the tree has a maximum depth.
    """

    def __init__(
        self,
        broadcaster_id: str,
        max_fanout: int = DEFAULT_TREE_FANOUT,
        max_depth: int = MAX_TREE_DEPTH,
    ) -> None:
        self.broadcaster_id = broadcaster_id
        self.max_fanout = max_fanout
        self.max_depth = max_depth
        self._peers: dict[str, Peer] = {}
        self._broadcaster = Peer(
            peer_id=broadcaster_id,
            role=PeerRole.BROADCASTER,
            state=PeerState.CONNECTED,
            tree_depth=0,
        )
        self._peers[broadcaster_id] = self._broadcaster

    @property
    def broadcaster(self) -> Peer:
        """The broadcaster peer."""
        return self._broadcaster

    @property
    def peers(self) -> dict[str, Peer]:
        """All peers in the tree."""
        return self._peers

    @property
    def depth(self) -> int:
        """Current maximum tree depth."""
        max_depth = 0
        for peer in self._peers.values():
            if peer.tree_depth > max_depth:
                max_depth = peer.tree_depth
        return max_depth

    def add_peer(self, peer: Peer) -> None:
        """Add a peer to the tree."""
        self._peers[peer.peer_id] = peer

    def remove_peer(self, peer_id: str) -> None:
        """Remove a peer and reattach its children to the parent."""
        peer = self._peers.get(peer_id)
        if not peer:
            return

        # Reattach children to parent
        if peer.parent_id and peer.parent_id in self._peers:
            parent = self._peers[peer.parent_id]
            if peer_id in parent.children:
                parent.children.remove(peer_id)

        # Reattach peer's children to peer's parent (or broadcaster)
        new_parent_id = peer.parent_id or self.broadcaster_id
        for child_id in peer.children:
            if child_id in self._peers:
                child = self._peers[child_id]
                child.parent_id = new_parent_id
                child.tree_depth = peer.tree_depth
                if new_parent_id in self._peers:
                    self._peers[new_parent_id].children.append(child_id)

        del self._peers[peer_id]

    def find_parent(self, peer: Peer) -> Optional[Peer]:
        """Find the best parent for a peer in the tree.

        Selects the shallowest node with available capacity. Only the
        broadcaster and already-attached peers (those with a parent) are
        eligible — unattached peers sitting in the peer map (e.g. mesh
        viewers) must never become tree parents.
        """
        best: Optional[Peer] = None
        best_depth = self.max_depth + 1

        for candidate in self._peers.values():
            if not candidate.is_connected:
                continue
            # Skip unattached peers (mesh viewers): they have no parent and
            # tree_depth == 0, which would otherwise make them look like the
            # broadcaster and flatten the tree.
            if candidate.peer_id != self.broadcaster_id and candidate.parent_id is None:
                continue
            if not candidate.can_accept_children(self.max_fanout):
                continue
            if candidate.tree_depth >= self.max_depth:
                continue
            if candidate.tree_depth < best_depth:
                best = candidate
                best_depth = candidate.tree_depth

        return best

    def attach(self, peer: Peer) -> bool:
        """Attach a peer to the tree.

        Returns True if the peer was successfully attached.
        """
        if peer.peer_id in self._peers and peer.parent_id:
            return True  # Already attached

        parent = self.find_parent(peer)
        if not parent:
            return False

        peer.parent_id = parent.peer_id
        peer.tree_depth = parent.tree_depth + 1
        parent.children.append(peer.peer_id)
        self._peers[peer.peer_id] = peer
        return True

    def get_path(self, peer_id: str) -> list[str]:
        """Get the delivery path from broadcaster to a peer."""
        path: list[str] = []
        current = self._peers.get(peer_id)
        while current and current.peer_id != self.broadcaster_id:
            path.insert(0, current.peer_id)
            current = self._peers.get(current.parent_id or "")
        if current:
            path.insert(0, self.broadcaster_id)
        return path

    def get_downstream(self, peer_id: str) -> list[str]:
        """Get all peers downstream of a given peer (including itself)."""
        downstream: list[str] = []
        stack = [peer_id]
        while stack:
            current = stack.pop()
            if current in self._peers:
                downstream.append(current)
                stack.extend(self._peers[current].children)
        return downstream


class SwarmManager:
    """Manages the dual-layer peer swarm.

    Combines the primary delivery tree with the secondary local mesh.
    Handles peer join/leave, tree attachment, mesh formation, and
    fallback when tree parents drop.
    """

    def __init__(
        self,
        node_id: str,
        max_fanout: int = DEFAULT_TREE_FANOUT,
        max_depth: int = MAX_TREE_DEPTH,
        mesh_min: int = MESH_PEERS_MIN,
        mesh_max: int = MESH_PEERS_MAX,
    ) -> None:
        self.node_id = node_id
        self.mesh_min = mesh_min
        self.mesh_max = mesh_max
        self.tree = DeliveryTree(node_id, max_fanout, max_depth)
        self._mesh: dict[str, Peer] = {}
        self._stats = SwarmStats()
        self._fallback_count = 0

    @property
    def stats(self) -> SwarmStats:
        """Current swarm statistics."""
        self._update_stats()
        return self._stats

    @property
    def mesh_peers(self) -> dict[str, Peer]:
        """Peers in the local mesh."""
        return self._mesh

    @property
    def fallback_count(self) -> int:
        """Number of tree → mesh fallbacks performed."""
        return self._fallback_count

    def join(self, peer: Peer) -> bool:
        """Add a peer to the swarm.

        The peer is attached to the tree if eligible, and added to
        the mesh if it's a viewer.
        """
        peer.state = PeerState.CONNECTED
        peer.joined_at = int(time.time())

        # Try to attach to tree
        if peer.health.is_eligible_for_tree:
            peer.role = PeerRole.TREE_NODE
            if self.tree.attach(peer):
                return True

        # Fall back to viewer role
        peer.role = PeerRole.VIEWER
        self.tree.add_peer(peer)
        self._add_to_mesh(peer)
        return True

    def leave(self, peer_id: str) -> None:
        """Remove a peer from the swarm."""
        # Remove from tree
        self.tree.remove_peer(peer_id)

        # Remove from mesh
        if peer_id in self._mesh:
            del self._mesh[peer_id]

        # Remove from other peers' mesh lists
        for peer in self._mesh.values():
            if peer_id in peer.mesh_peers:
                peer.mesh_peers.remove(peer_id)

    def handle_parent_drop(self, parent_id: str) -> bool:
        """Handle a tree parent dropping.

        Falls back to mesh pull mode and attempts to reattach to the tree.

        Returns True if the node was reattached to the tree.
        """
        self._fallback_count += 1
        self._stats.fallbacks += 1

        # Remove the dropped parent
        self.tree.remove_peer(parent_id)

        # Try to reattach to the tree
        node = self.tree.peers.get(self.node_id)
        if node:
            node.parent_id = None
            node.tree_depth = 0
            if self.tree.attach(node):
                return True

        # Stay in mesh mode
        return False

    def update_health(self, peer_id: str, health: PeerHealth) -> None:
        """Update a peer's health metrics."""
        if peer_id in self.tree.peers:
            self.tree.peers[peer_id].health = health
        if peer_id in self._mesh:
            self._mesh[peer_id].health = health

    def get_missing_from_mesh(self, sequence_ids: list[int]) -> list[str]:
        """Get mesh peers that might have the missing chunks."""
        return [peer_id for peer_id in self._mesh if self._mesh[peer_id].is_connected]

    def _add_to_mesh(self, peer: Peer) -> None:
        """Add a peer to the local mesh."""
        if len(self._mesh) >= self.mesh_max:
            return
        self._mesh[peer.peer_id] = peer
        peer.mesh_peers = list(self._mesh.keys())

    def _update_stats(self) -> None:
        """Refresh swarm statistics."""
        self._stats.total_peers = len(self.tree.peers)
        self._stats.connected_peers = sum(
            1 for p in self.tree.peers.values() if p.is_connected
        )
        self._stats.tree_nodes = sum(
            1 for p in self.tree.peers.values() if p.is_tree_node
        )
        self._stats.viewers = sum(
            1 for p in self.tree.peers.values() if p.role == PeerRole.VIEWER
        )
        self._stats.tree_depth = self.tree.depth
        self._stats.mesh_connections = len(self._mesh)