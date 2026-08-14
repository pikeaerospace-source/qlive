"""Tests for the QLive discrete-event swarm simulation."""

import pytest

from qlive.simulation import SimConfig, Simulation, run_sweep


def test_baseline_perfect_delivery():
    config = SimConfig(num_viewers=50, duration_ms=10_000, loss_rate=0.0, seed=1)
    results = Simulation(config).run()
    assert results.delivery_rate == 1.0
    assert results.mean_missed == 0.0
    assert results.recovery_rate == 0.0  # nothing lost, nothing recovered


def test_loss_reduces_delivery():
    config = SimConfig(num_viewers=50, duration_ms=10_000, loss_rate=0.1, seed=1)
    results = Simulation(config).run()
    assert results.delivery_rate < 1.0


def test_mesh_enables_recovery():
    base = SimConfig(num_viewers=50, duration_ms=10_000, loss_rate=0.1, seed=1)
    no_mesh = Simulation(SimConfig(**{**base.__dict__, "mesh_size": 0})).run()
    with_mesh = Simulation(SimConfig(**{**base.__dict__, "mesh_size": 16})).run()
    assert no_mesh.recovery_rate == 0.0
    assert with_mesh.recovery_rate > 0.0


def test_larger_buffer_improves_recovery():
    base = SimConfig(num_viewers=50, duration_ms=10_000, loss_rate=0.1, seed=1)
    tiny = Simulation(SimConfig(**{**base.__dict__, "buffer_window_ms": 2000})).run()
    big = Simulation(SimConfig(**{**base.__dict__, "buffer_window_ms": 30_000})).run()
    assert big.recovery_rate >= tiny.recovery_rate


def test_deterministic_with_seed():
    config = SimConfig(num_viewers=50, duration_ms=10_000, loss_rate=0.05, seed=42)
    a = Simulation(config).run()
    b = Simulation(config).run()
    assert a.as_dict() == b.as_dict()


def test_fanout_affects_depth():
    base = SimConfig(num_viewers=200, duration_ms=5000, seed=1)
    shallow = Simulation(SimConfig(**{**base.__dict__, "fanout": 16})).run()
    deep = Simulation(SimConfig(**{**base.__dict__, "fanout": 2})).run()
    assert deep.tree_depth > shallow.tree_depth


def test_run_sweep():
    base = SimConfig(num_viewers=20, duration_ms=5000, seed=1)
    pairs = run_sweep(base, "loss_rate", [0.0, 0.1])
    assert len(pairs) == 2
    assert pairs[0][0] == 0.0
    assert pairs[0][1].delivery_rate == 1.0
    assert pairs[1][1].delivery_rate < 1.0


def test_invalid_config():
    with pytest.raises(ValueError):
        SimConfig(loss_rate=1.5)
    with pytest.raises(ValueError):
        SimConfig(fanout=0)
    with pytest.raises(ValueError):
        SimConfig(buffer_window_ms=100)  # < fragment_ms
