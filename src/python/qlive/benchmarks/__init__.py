"""QLive local benchmark framework.

Offline, deterministic benchmarks for the QLive reference implementation.

None of these require a live Qortal network, QDN, FFmpeg, or real sockets —
everything runs in-process against the :mod:`qlive` package. They measure
CPU throughput, memory footprint, and scaling behaviour of the core
protocol components (chunking, buffering, encryption, swarm, retransmission,
incentives, proof-of-relay, and the end-to-end delivery pipeline).

See ``README.md`` in this directory for usage.
"""
