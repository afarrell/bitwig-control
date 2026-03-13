"""Session management for Bitwig CLI.

Manages the OSC connection lifecycle and provides access to the shared
BitwigState cache. Unlike file-based harnesses, there's no local project
file — all state comes from the live Bitwig instance.
"""

import json
import os
from pathlib import Path
from typing import Any, Optional

from cli_anything.bitwig.utils.osc_backend import OscBitwigClient


# Default connection config location
_CONFIG_DIR = Path.home() / ".cli-anything-bitwig"
_CONFIG_FILE = _CONFIG_DIR / "config.json"


class Session:
    """Manages the connection to a running Bitwig instance."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        send_port: int = 8000,
        receive_port: int = 9000,
    ):
        self.host = host
        self.send_port = send_port
        self.receive_port = receive_port
        self._client: Optional[OscBitwigClient] = None
        self._bank_offset = 0  # Track bank scroll position
        self._scene_bank_offset = 0

    @property
    def client(self) -> OscBitwigClient:
        if self._client is None:
            raise RuntimeError("Not connected. Run 'connect' first.")
        return self._client

    @property
    def connected(self) -> bool:
        return self._client is not None and self._client.connected

    def connect(self, timeout: float = 3.0) -> dict:
        """Connect to Bitwig via OSC."""
        if self._client and self._client.connected:
            return {
                "status": "already_connected",
                "host": self.host,
                "send_port": self.send_port,
                "receive_port": self.receive_port,
            }

        self._client = OscBitwigClient(
            bitwig_host=self.host,
            send_port=self.send_port,
            receive_port=self.receive_port,
        )
        result = self._client.connect(timeout=timeout)

        if not result["connected"]:
            self._client = None
            raise RuntimeError(
                "Could not connect to Bitwig Studio.\n"
                "Make sure:\n"
                "  1. Bitwig Studio is running\n"
                "  2. DrivenByMoss is installed and configured\n"
                "  3. Open Sound Control controller is added in Bitwig:\n"
                "     Settings > Controllers > Add > Open Sound Control\n"
                f"  4. Send port is set to {self.receive_port}\n"
                f"  5. Receive port is set to {self.send_port}"
            )

        return {
            "status": "connected",
            **result,
        }

    def disconnect(self) -> dict:
        """Disconnect from Bitwig."""
        if self._client:
            self._client.disconnect()
            self._client = None
        return {"status": "disconnected"}

    def send(self, address: str, *args) -> None:
        """Send an OSC message to Bitwig."""
        self.client.send(address, *args)

    def send_wait(self, address: str, *args, wait: float = 0.1) -> None:
        """Send an OSC message and wait for state update."""
        self.client.send_and_wait(address, *args, wait=wait)

    def get_state(self, *keys: str) -> Any:
        """Get a value from the cached Bitwig state."""
        return self.client.state.get(*keys)

    def full_state(self) -> dict:
        """Get a complete snapshot of the cached Bitwig state."""
        return self.client.state.snapshot()

    def status(self) -> dict:
        """Return connection status info."""
        return {
            "connected": self.connected,
            "host": self.host,
            "send_port": self.send_port,
            "receive_port": self.receive_port,
            "bank_offset": self._bank_offset,
            "scene_bank_offset": self._scene_bank_offset,
            "state_age_ms": (
                round((
                    __import__("time").time() - self.client.state.last_update
                ) * 1000)
                if self.connected else None
            ),
        }

    # ── Bank navigation ────────────────────────────────────────────

    def scroll_tracks(self, direction: int) -> dict:
        """Scroll the track bank. direction: +1 forward, -1 backward."""
        if direction > 0:
            self.send("/track/bank/+", 1)
            self._bank_offset += 8
        else:
            self.send("/track/bank/-", 1)
            self._bank_offset = max(0, self._bank_offset - 8)
        return {"bank_offset": self._bank_offset}

    def scroll_scenes(self, direction: int) -> dict:
        """Scroll the scene bank. direction: +1 forward, -1 backward."""
        if direction > 0:
            self.send("/scene/bank/+", 1)
            self._scene_bank_offset += 8
        else:
            self.send("/scene/bank/-", 1)
            self._scene_bank_offset = max(0, self._scene_bank_offset - 8)
        return {"scene_bank_offset": self._scene_bank_offset}

    # ── Config persistence ─────────────────────────────────────────

    def save_config(self) -> str:
        """Save connection config to disk."""
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        config = {
            "host": self.host,
            "send_port": self.send_port,
            "receive_port": self.receive_port,
        }
        _CONFIG_FILE.write_text(json.dumps(config, indent=2))
        return str(_CONFIG_FILE)

    @classmethod
    def load_config(cls) -> "Session":
        """Load session with saved connection config, or defaults."""
        if _CONFIG_FILE.exists():
            try:
                config = json.loads(_CONFIG_FILE.read_text())
                return cls(
                    host=config.get("host", "127.0.0.1"),
                    send_port=config.get("send_port", 8000),
                    receive_port=config.get("receive_port", 9000),
                )
            except (json.JSONDecodeError, KeyError):
                pass
        return cls()
