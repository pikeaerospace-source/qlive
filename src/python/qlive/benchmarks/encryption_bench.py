"""Encryption benchmarks.

Measures AES-256-GCM throughput for the private-stream encryption model
(see ``docs/ENCRYPTION-MODEL.md``): bulk throughput on large buffers and
per-chunk cost at realistic streaming chunk sizes.
"""

from __future__ import annotations

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from qlive.benchmarks.runner import Result, Suite, best_time

BITRATES_KBPS = (1000, 3000, 4500, 6000)


class EncryptionSuite(Suite):
    name = "encryption"
    description = "AES-256-GCM throughput (bulk and per-chunk) for private streams."

    def run(self, quick: bool = False) -> list[Result]:
        results: list[Result] = []
        key = AESGCM.generate_key(bit_length=256)
        aesgcm = AESGCM(key)
        bulk_sizes = (1,) if quick else (1, 10)
        bitrates = (1000, 4500) if quick else BITRATES_KBPS
        chunk_number = 20 if quick else 100

        # 1. Bulk throughput on 1 MB and 10 MB buffers.
        for size_mb in bulk_sizes:
            data = os.urandom(size_mb * 1024 * 1024)
            nonce = os.urandom(12)
            encrypt_s = best_time(aesgcm.encrypt, nonce, data, None, repeat=3, number=1)
            ciphertext = aesgcm.encrypt(nonce, data, None)
            decrypt_s = best_time(aesgcm.decrypt, nonce, ciphertext, None, repeat=3, number=1)
            results.append(
                Result(f"encrypt.{size_mb}MB", size_mb / encrypt_s, "MB/s", "AES-256-GCM")
            )
            results.append(
                Result(f"decrypt.{size_mb}MB", size_mb / decrypt_s, "MB/s", "AES-256-GCM")
            )

        # 2. Per-chunk encryption cost at streaming chunk sizes (1s fragments).
        for bitrate in bitrates:
            payload = os.urandom(int(bitrate * 1000 / 8))
            nonce = os.urandom(12)
            encrypt_s = best_time(
                aesgcm.encrypt, nonce, payload, None, repeat=3, number=chunk_number
            )
            results.append(
                Result(
                    f"encrypt_chunk.{bitrate}kbps",
                    encrypt_s * 1e6,
                    "us",
                    "per 1s chunk (+16B tag)",
                )
            )

        return results
