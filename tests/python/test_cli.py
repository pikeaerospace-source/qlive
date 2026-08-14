"""Tests for the QLive CLI."""

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from qlive.cli import load_private_key, main, run_broadcast, run_watch


@pytest.fixture
def private_key() -> ed25519.Ed25519PrivateKey:
    """A fresh Ed25519 private key."""
    return ed25519.Ed25519PrivateKey.generate()


@pytest.fixture
def key_file(tmp_path, private_key) -> str:
    """Write a private key to a temp file."""
    key_path = tmp_path / "test_key.pem"
    key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    return str(key_path)


class TestLoadPrivateKey:
    def test_load_valid_key(self, key_file):
        loaded = load_private_key(key_file)
        assert loaded is not None

    def test_load_missing_key(self, tmp_path):
        with pytest.raises(SystemExit):
            load_private_key(str(tmp_path / "missing.pem"))

    def test_load_invalid_key(self, tmp_path):
        bad_file = tmp_path / "bad.pem"
        bad_file.write_text("not a key")
        with pytest.raises(SystemExit):
            load_private_key(str(bad_file))


class TestRunBroadcast:
    @pytest.mark.asyncio
    async def test_run_broadcast(self, key_file):
        args = MagicMock()
        args.key = key_file
        args.name = "test-name"
        args.source = "test.mp4"
        args.title = None
        args.description = None
        args.category = None
        args.fragment_ms = 1000
        args.video_bitrate = "4500k"
        args.audio_bitrate = "128k"
        args.fps = 30
        args.width = 1920
        args.height = 1080
        args.ffmpeg = "ffmpeg"
        args.no_archive = False

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            with patch("qlive.cli.Broadcaster.run", new_callable=AsyncMock):
                result = await run_broadcast(args)

        assert result == 0


class TestRunWatch:
    @pytest.mark.asyncio
    async def test_run_watch_qortal_url(self):
        args = MagicMock()
        args.stream = "qortal://test-name/live"
        args.node = None

        with patch("asyncio.sleep", side_effect=KeyboardInterrupt):
            result = await run_watch(args)

        assert result == 0

    @pytest.mark.asyncio
    async def test_run_watch_hex_id(self):
        stream_id = hashlib.sha256(b"test").digest()
        args = MagicMock()
        args.stream = stream_id.hex()
        args.node = "test-node"

        with patch("asyncio.sleep", side_effect=KeyboardInterrupt):
            result = await run_watch(args)

        assert result == 0

    @pytest.mark.asyncio
    async def test_run_watch_invalid_id(self):
        args = MagicMock()
        args.stream = "not-a-valid-hex"
        args.node = None

        result = await run_watch(args)
        assert result == 1


class TestMain:
    def test_no_command(self, capsys):
        with patch("sys.argv", ["qlive"]):
            result = main()
        assert result == 0
        assert "usage:" in capsys.readouterr().out

    def test_version(self, capsys):
        with patch("sys.argv", ["qlive", "--version"]):
            with pytest.raises(SystemExit) as exc:
                main()
        assert exc.value.code == 0
        assert "qlive" in capsys.readouterr().out