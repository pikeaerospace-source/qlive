"""Tests for the QLive dual-layer peer swarm."""

import pytest

from qlive.swarm import (
    DEFAULT_TREE_FANOUT,
    MAX_LATENCY_MS,
    MAX_PACKET_LOSS,
    MAX_TREE_DEPTH,
    MESH_PEERS_MAX,
    MESH_PEERS_MIN,
    MIN_BANDWIDTH_KBPS,
    MIN_UPTIME_SECONDS,
    DeliveryTree,
    Peer,
    PeerHealth,
    PeerRole,
    PeerState,
    SwarmManager,
)


def make_peer(
    peer_id: str,
    *,
    healthy: bool = True,
    bandwidth: float = 3000,
    role: PeerRole = PeerRole.VIEWER,
) -> Peer:
    """Create a test peer with configurable health."""
    health = PeerHealth(
        latency_ms=50 if healthy else 1000,
        packet_loss=0.01 if healthy else 0.2,
        uptime_seconds=3600 if healthy else 10,
        bandwidth_kbps=bandwidth,
    )
    return Peer(
        peer_id=peer_id,
        role=role,
        state=PeerState.CONNECTED,
        health=health,
    )


class TestPeerHealth:
    def test_healthy_peer(self):
        health = PeerHealth(
            latency_ms=50, packet_loss=0.01, uptime_seconds=3600, bandwidth_kbps=3000
        )
        assert health.is_healthy is True
        assert health.is_eligible_for_tree is True

    def test_unhealthy_latency(self):
        health = PeerHealth(
            latency_ms=MAX_LATENCY_MS + 1,
            packet_loss=0.01,
            uptime_seconds=3600,
            bandwidth_kbps=3000,
        )
        assert health.is_healthy is False

    def test_unhealthy_packet_loss(self):
        health = PeerHealth(
            latency_ms=50,
            packet_loss=MAX_PACKET_LOSS + 0.1,
            uptime_seconds=3600,
            bandwidth_kbps=3000,
        )
        assert health.is_healthy is False

    def test_unhealthy_uptime(self):
        health = PeerHealth(
            latency_ms=50,
            packet_loss=0.01,
            uptime_seconds=MIN_UPTIME_SECONDS - 1,
            bandwidth_kbps=3000,
        )
        assert health.is_healthy is False

    def test_unhealthy_bandwidth(self):
        health = PeerHealth(
            latency_ms=50,
            packet_loss=0.01,
            uptime_seconds=3600,
            bandwidth_kbps=MIN_BANDWIDTH_KBPS - 1,
        )
        assert health.is_healthy is False

    def test_eligible_for_tree_requires_double_bandwidth(self):
        health = PeerHealth(
            latency_ms=50,
            packet_loss=0.01,
            uptime_seconds=3600,
            bandwidth_kbps=MIN_BANDWIDTH_KBPS,  # Healthy but not double
        )
        assert health.is_healthy is True
        assert health.is_eligible_for_tree is False


class TestPeer:
    def test_defaults(self):
        peer = Peer(peer_id="peer-1")
        assert peer.role == PeerRole.VIEWER
        assert peer.state == PeerState.DISCOVERED
        assert peer.tree_depth == 0
        assert peer.parent_id is None
        assert peer.children == []
        assert peer.mesh_peers == []
        assert peer.is_connected is False
        assert peer.is_tree_node is False

    def test_connected(self):
        peer = Peer(peer_id="peer-1", state=PeerState.CONNECTED)
        assert peer.is_connected is True

    def test_tree_node(self):
        peer = Peer(peer_id="peer-1", role=PeerRole.TREE_NODE)
        assert peer.is_tree_node is True

    def test_can_accept_children(self):
        peer = Peer(peer_id="peer-1")
        assert peer.can_accept_children() is True
        peer.children = ["c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8"]
        assert peer.can_accept_children() is False

    def test_child_count(self):
        peer = Peer(peer_id="peer-1")
        peer.children = ["c1", "c2"]
        assert peer.child_count == 2

    def test_mesh_count(self):
        peer = Peer(peer_id="peer-1")
        peer.mesh_peers = ["m1", "m2", "m3"]
        assert peer.mesh_count == 3


class TestDeliveryTree:
    def test_init(self):
        tree = DeliveryTree("broadcaster")
        assert tree.broadcaster_id == "broadcaster"
        assert tree.max_fanout == DEFAULT_TREE_FANOUT
        assert tree.max_depth == MAX_TREE_DEPTH
        assert tree.depth == 0
        assert tree.broadcaster.role == PeerRole.BROADCASTER

    def test_add_peer(self):
        tree = DeliveryTree("broadcaster")
        peer = make_peer("peer-1")
        tree.add_peer(peer)
        assert "peer-1" in tree.peers

    def test_attach_to_broadcaster(self):
        tree = DeliveryTree("broadcaster")
        peer = make_peer("peer-1")
        assert tree.attach(peer) is True
        assert peer.parent_id == "broadcaster"
        assert peer.tree_depth == 1
        assert "peer-1" in tree.broadcaster.children

    def test_attach_chain(self):
        tree = DeliveryTree("broadcaster")
        p1 = make_peer("peer-1")
        p2 = make_peer("peer-2")
        p3 = make_peer("peer-3")
        tree.attach(p1)
        tree.attach(p2)
        tree.attach(p3)
        assert p1.tree_depth == 1
        assert p2.tree_depth == 1
        assert p3.tree_depth == 1

    def test_attach_uses_shallowest(self):
        tree = DeliveryTree("broadcaster")
        # Fill broadcaster's fanout
        for i in range(DEFAULT_TREE_FANOUT):
            tree.attach(make_peer(f"peer-{i}"))
        # New peer should attach to a depth-1 node
        new_peer = make_peer("new-peer")
        assert tree.attach(new_peer) is True
        assert new_peer.tree_depth == 2

    def test_attach_skips_unattached_peers(self):
        # Regression: unattached peers (mesh viewers) sit in the peer map
        # with tree_depth == 0 and no parent, and must never become parents.
        tree = DeliveryTree("broadcaster")
        viewer = make_peer("viewer-1")
        tree.add_peer(viewer)  # unattached, tree_depth == 0

        # Fill the broadcaster's fanout with real tree nodes.
        for i in range(DEFAULT_TREE_FANOUT):
            tree.attach(make_peer(f"peer-{i}"))

        # The next peer must attach to a depth-1 tree node, not the viewer.
        new_peer = make_peer("new-peer")
        assert tree.attach(new_peer) is True
        assert new_peer.tree_depth == 2
        assert new_peer.parent_id != "viewer-1"
        assert viewer.children == []

    def test_attach_no_parent_available(self):
        tree = DeliveryTree("broadcaster", max_fanout=1, max_depth=1)
        tree.attach(make_peer("peer-1"))
        # Broadcaster full, depth 1 max
        assert tree.attach(make_peer("peer-2")) is False

    def test_remove_peer_reattaches_children(self):
        tree = DeliveryTree("broadcaster")
        p1 = make_peer("peer-1")
        p2 = make_peer("peer-2")
        tree.attach(p1)
        tree.attach(p2)
        # p2 is child of broadcaster, p1 is child of broadcaster
        # Remove p1, p2 should still be attached
        tree.remove_peer("peer-1")
        assert "peer-1" not in tree.peers
        assert "peer-2" in tree.peers

    def test_get_path(self):
        tree = DeliveryTree("broadcaster")
        p1 = make_peer("peer-1")
        p2 = make_peer("peer-2")
        tree.attach(p1)
        # Force p2 to be child of p1
        p2.parent_id = "peer-1"
        p2.tree_depth = 2
        p1.children.append("peer-2")
        tree.add_peer(p2)

        path = tree.get_path("peer-2")
        assert path == ["broadcaster", "peer-1", "peer-2"]

    def test_get_downstream(self):
        tree = DeliveryTree("broadcaster")
        p1 = make_peer("peer-1")
        p2 = make_peer("peer-2")
        tree.attach(p1)
        p2.parent_id = "peer-1"
        p2.tree_depth = 2
        p1.children.append("peer-2")
        tree.add_peer(p2)

        downstream = tree.get_downstream("peer-1")
        assert set(downstream) == {"peer-1", "peer-2"}


class TestSwarmManager:
    def test_init(self):
        manager = SwarmManager("node-1")
        assert manager.node_id == "node-1"
        assert manager.mesh_min == MESH_PEERS_MIN
        assert manager.mesh_max == MESH_PEERS_MAX
        assert manager.fallback_count == 0
        assert manager.mesh_peers == {}

    def test_join_healthy_peer_to_tree(self):
        manager = SwarmManager("node-1")
        peer = make_peer("peer-1", bandwidth=3000)
        assert manager.join(peer) is True
        assert peer.role == PeerRole.TREE_NODE
        assert peer.parent_id == "node-1"
        assert peer.state == PeerState.CONNECTED

    def test_join_unhealthy_peer_to_mesh(self):
        manager = SwarmManager("node-1")
        peer = make_peer("peer-1", healthy=False)
        assert manager.join(peer) is True
        assert peer.role == PeerRole.VIEWER
        assert "peer-1" in manager.mesh_peers

    def test_join_low_bandwidth_peer_to_mesh(self):
        manager = SwarmManager("node-1")
        peer = make_peer("peer-1", bandwidth=MIN_BANDWIDTH_KBPS)
        assert manager.join(peer) is True
        assert peer.role == PeerRole.VIEWER
        assert "peer-1" in manager.mesh_peers

    def test_leave(self):
        manager = SwarmManager("node-1")
        peer = make_peer("peer-1", healthy=False)
        manager.join(peer)
        manager.leave("peer-1")
        assert "peer-1" not in manager.tree.peers
        assert "peer-1" not in manager.mesh_peers

    def test_handle_parent_drop_reattach(self):
        manager = SwarmManager("node-1")
        # Add a tree node
        tree_node = make_peer("tree-1", bandwidth=3000)
        manager.join(tree_node)
        # Add a viewer under the tree node
        viewer = make_peer("viewer-1", healthy=False)
        viewer.parent_id = "tree-1"
        viewer.tree_depth = 2
        manager.tree.add_peer(viewer)
        tree_node.children.append("viewer-1")

        # Handle tree-1 dropping - viewer should be reattached to broadcaster
        manager.tree.remove_peer("tree-1")
        assert viewer.parent_id == "node-1"
        assert viewer.tree_depth == 1
        assert "viewer-1" in manager.tree.broadcaster.children
        assert manager.fallback_count == 0  # Direct tree removal, not manager fallback

    def test_handle_parent_drop_reattaches_to_broadcaster(self):
        manager = SwarmManager("node-1", max_fanout=1, max_depth=1)
        # Fill broadcaster's fanout with a tree node
        tree_node = make_peer("tree-1", bandwidth=3000)
        manager.join(tree_node)
        # Add a viewer under the tree node
        viewer = make_peer("viewer-1", healthy=False)
        viewer.parent_id = "tree-1"
        viewer.tree_depth = 2
        manager.tree.add_peer(viewer)
        tree_node.children.append("viewer-1")

        # Handle tree-1 dropping - viewer is reattached to broadcaster
        manager.tree.remove_peer("tree-1")
        assert viewer.parent_id == "node-1"
        assert viewer.tree_depth == 1
        assert "viewer-1" in manager.tree.broadcaster.children
        assert manager.fallback_count == 0

    def test_update_health(self):
        manager = SwarmManager("node-1")
        peer = make_peer("peer-1", healthy=False)
        manager.join(peer)

        new_health = PeerHealth(
            latency_ms=50, packet_loss=0.01, uptime_seconds=3600, bandwidth_kbps=3000
        )
        manager.update_health("peer-1", new_health)
        assert manager.mesh_peers["peer-1"].health.is_healthy is True

    def test_get_missing_from_mesh(self):
        manager = SwarmManager("node-1")
        p1 = make_peer("peer-1", healthy=False)
        p2 = make_peer("peer-2", healthy=False)
        manager.join(p1)
        manager.join(p2)
        peers = manager.get_missing_from_mesh([1, 2, 3])
        assert set(peers) == {"peer-1", "peer-2"}

    def test_stats(self):
        manager = SwarmManager("node-1")
        manager.join(make_peer("peer-1", bandwidth=3000))
        manager.join(make_peer("peer-2", healthy=False))
        manager.join(make_peer("peer-3", healthy=False))

        stats = manager.stats
        assert stats.total_peers == 4  # node-1 + 3 peers
        assert stats.connected_peers == 4
        assert stats.tree_nodes == 1  # peer-1 (node-1 is broadcaster)
        assert stats.viewers == 2  # peer-2, peer-3
        assert stats.mesh_connections == 2
