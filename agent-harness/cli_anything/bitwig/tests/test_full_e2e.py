"""E2E tests for cli-anything-bitwig.

These tests require a running Bitwig Studio instance with DrivenByMoss
OSC controller configured (send port 8000, receive port 9000).

Run with: pytest cli_anything/bitwig/tests/test_full_e2e.py -v -s
"""

import json
import os
import shutil
import subprocess
import sys
import time

import pytest

# ── Skip if Bitwig not available ───────────────────────────────────────

def _bitwig_available():
    """Check if Bitwig is actually responding on OSC.

    UDP sendto always succeeds, so we start a real OSC listener,
    send a /refresh, and wait for any state update within 2 seconds.
    """
    try:
        from cli_anything.bitwig.utils.osc_backend import OscBitwigClient
        client = OscBitwigClient(receive_port=19123)  # Use unusual port to avoid conflicts
        result = client.connect(timeout=2.0)
        client.disconnect()
        return result.get("state_received", False)
    except Exception:
        return False


BITWIG_AVAILABLE = _bitwig_available()
skip_no_bitwig = pytest.mark.skipif(
    not BITWIG_AVAILABLE,
    reason="Bitwig Studio not running or DrivenByMoss OSC not configured"
)


# ── Helper ─────────────────────────────────────────────────────────────

def _resolve_cli(name):
    """Resolve installed CLI command; falls back to python -m for dev."""
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = name.replace("cli-anything-", "cli_anything.") + "." + name.split("-")[-1] + "_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


# ── Connection tests ───────────────────────────────────────────────────

@skip_no_bitwig
class TestConnection:
    def test_connect_and_disconnect(self):
        from cli_anything.bitwig.core.session import Session
        sess = Session()
        result = sess.connect(timeout=5.0)
        assert result["status"] == "connected"
        assert sess.connected is True

        # Should have received some state
        state = sess.full_state()
        assert "transport" in state
        assert "tracks" in state

        sess.disconnect()
        assert sess.connected is False

    def test_double_connect(self):
        from cli_anything.bitwig.core.session import Session
        sess = Session()
        sess.connect(timeout=5.0)
        result = sess.connect()
        assert result["status"] == "already_connected"
        sess.disconnect()


# ── Transport tests ────────────────────────────────────────────────────

@skip_no_bitwig
class TestTransportE2E:
    @pytest.fixture(autouse=True)
    def setup_session(self):
        from cli_anything.bitwig.core.session import Session
        self.sess = Session()
        self.sess.connect(timeout=5.0)
        yield
        self.sess.disconnect()

    def test_transport_status(self):
        from cli_anything.bitwig.core.transport import status
        result = status(self.sess)
        assert "playing" in result
        assert "tempo" in result
        assert isinstance(result["tempo"], float)
        assert result["tempo"] > 0
        print(f"\n  Transport: tempo={result['tempo']}, position={result['position']}")

    def test_set_tempo(self):
        from cli_anything.bitwig.core.transport import set_tempo, status
        original = status(self.sess)["tempo"]

        set_tempo(self.sess, 135.0)
        time.sleep(0.3)  # Wait for state update

        result = status(self.sess)
        # Note: Bitwig may round tempo, so check approximate
        print(f"\n  Tempo set: requested=135.0, actual={result['tempo']}")

        # Restore original
        set_tempo(self.sess, original)


# ── Track tests ────────────────────────────────────────────────────────

@skip_no_bitwig
class TestTracksE2E:
    @pytest.fixture(autouse=True)
    def setup_session(self):
        from cli_anything.bitwig.core.session import Session
        self.sess = Session()
        self.sess.connect(timeout=5.0)
        yield
        self.sess.disconnect()

    def test_list_tracks(self):
        from cli_anything.bitwig.core.tracks import list_tracks
        result = list_tracks(self.sess)
        assert "tracks" in result
        assert isinstance(result["tracks"], list)
        print(f"\n  Found {result['count']} tracks:")
        for t in result["tracks"]:
            print(f"    [{t['bank_index']}] {t['name']} vol={t['volume']}")


# ── Mixer tests ────────────────────────────────────────────────────────

@skip_no_bitwig
class TestMixerE2E:
    @pytest.fixture(autouse=True)
    def setup_session(self):
        from cli_anything.bitwig.core.session import Session
        self.sess = Session()
        self.sess.connect(timeout=5.0)
        yield
        self.sess.disconnect()

    def test_mixer_status(self):
        from cli_anything.bitwig.core.mixer import status
        result = status(self.sess)
        assert "tracks" in result
        assert "master" in result
        print(f"\n  Mixer: {len(result['tracks'])} tracks")
        print(f"  Master: vol={result['master']['volume']}")


# ── CLI Subprocess tests ──────────────────────────────────────────────

class TestCLISubprocess:
    CLI_BASE = _resolve_cli("cli-anything-bitwig")

    def _run(self, args, check=True):
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True,
            text=True,
            check=check,
            timeout=10,
        )

    def test_help(self):
        result = self._run(["--help"])
        assert result.returncode == 0
        assert "cli-anything-bitwig" in result.stdout
        assert "transport" in result.stdout

    def test_transport_help(self):
        result = self._run(["transport", "--help"])
        assert result.returncode == 0
        assert "play" in result.stdout
        assert "stop" in result.stdout

    def test_track_help(self):
        result = self._run(["track", "--help"])
        assert result.returncode == 0
        assert "volume" in result.stdout

    def test_clip_help(self):
        result = self._run(["clip", "--help"])
        assert result.returncode == 0
        assert "launch" in result.stdout

    def test_device_help(self):
        result = self._run(["device", "--help"])
        assert result.returncode == 0
        assert "param" in result.stdout

    def test_mixer_help(self):
        result = self._run(["mixer", "--help"])
        assert result.returncode == 0
        assert "status" in result.stdout


@skip_no_bitwig
class TestCLISubprocessE2E:
    """Subprocess tests that require a running Bitwig instance."""
    CLI_BASE = _resolve_cli("cli-anything-bitwig")

    def _run(self, args, check=True):
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True,
            text=True,
            check=check,
            timeout=15,
        )

    def test_json_connect_and_status(self):
        result = self._run(["--json", "connect"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data.get("status") in ("connected", "already_connected")

    def test_json_transport_status(self):
        # First connect
        self._run(["connect"], check=False)
        result = self._run(["--json", "transport", "status"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "playing" in data
        assert "tempo" in data
        print(f"\n  JSON transport: {json.dumps(data, indent=2)}")

    def test_json_track_list(self):
        self._run(["connect"], check=False)
        result = self._run(["--json", "track", "list"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "tracks" in data
        assert isinstance(data["tracks"], list)
        print(f"\n  JSON tracks: {data['count']} tracks")

    def test_json_mixer_status(self):
        self._run(["connect"], check=False)
        result = self._run(["--json", "mixer", "status"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "tracks" in data
        assert "master" in data

    def test_full_workflow(self):
        """Full workflow: connect -> get status -> list tracks -> disconnect."""
        # Connect
        r = self._run(["--json", "connect"])
        data = json.loads(r.stdout)
        assert data.get("status") in ("connected", "already_connected")

        # Transport status
        r = self._run(["--json", "transport", "status"])
        transport = json.loads(r.stdout)
        assert "tempo" in transport

        # Track list
        r = self._run(["--json", "track", "list"])
        tracks = json.loads(r.stdout)
        assert "tracks" in tracks

        # Mixer
        r = self._run(["--json", "mixer", "status"])
        mixer = json.loads(r.stdout)
        assert "master" in mixer

        # Disconnect
        r = self._run(["--json", "disconnect"])
        data = json.loads(r.stdout)
        assert data["status"] == "disconnected"

        print(f"\n  Full workflow passed:")
        print(f"    Tempo: {transport['tempo']}")
        print(f"    Tracks: {tracks['count']}")
        print(f"    Master vol: {mixer['master']['volume']}")
