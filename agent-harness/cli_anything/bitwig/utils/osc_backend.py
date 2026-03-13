"""OSC backend for communicating with Bitwig Studio via DrivenByMoss.

This module handles all OSC communication:
- Sending commands to Bitwig (transport, tracks, clips, etc.)
- Receiving state updates from Bitwig in a background thread
- Maintaining a local state cache for fast introspection
"""

import socket
import threading
import time
from typing import Any, Optional


def _check_osc_lib():
    """Verify python-osc is installed."""
    try:
        import pythonosc  # noqa: F401
        return True
    except ImportError:
        raise RuntimeError(
            "python-osc is not installed. Install it with:\n"
            "  pip install python-osc\n"
            "  # or: pip install cli-anything-bitwig"
        )


class BitwigState:
    """Thread-safe cache of Bitwig's current state, populated by OSC feedback."""

    def __init__(self):
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {
            "transport": {
                "playing": False,
                "recording": False,
                "tempo": 120.0,
                "position": "1.1.0",
                "numerator": 4,
                "denominator": 4,
                "loop": False,
                "click": False,
                "automation_write": False,
                "overdub": False,
            },
            "tracks": {},
            "master": {
                "volume": 1.0,
                "volume_str": "0.0 dB",
                "pan": 0.5,
                "mute": False,
                "solo": False,
            },
            "scenes": {},
            "device": {
                "name": "",
                "bypass": False,
                "params": {},
                "page_name": "",
            },
            "browser": {
                "active": False,
            },
            "project": {
                "name": "",
                "engine": True,
            },
            "layout": "arrange",
        }
        self._last_update = 0.0

    def get(self, *keys: str) -> Any:
        """Thread-safe get from nested state dict."""
        with self._lock:
            val = self._data
            for k in keys:
                if isinstance(val, dict):
                    val = val.get(k)
                else:
                    return None
            return val

    def set(self, *keys_and_value):
        """Thread-safe set in nested state dict. Last arg is the value."""
        *keys, value = keys_and_value
        with self._lock:
            d = self._data
            for k in keys[:-1]:
                if k not in d or not isinstance(d[k], dict):
                    d[k] = {}
                d = d[k]
            d[keys[-1]] = value
            self._last_update = time.time()

    def snapshot(self) -> dict:
        """Return a deep copy of the full state."""
        import copy
        with self._lock:
            return copy.deepcopy(self._data)

    @property
    def last_update(self) -> float:
        with self._lock:
            return self._last_update


class OscBitwigClient:
    """OSC client/server for bidirectional communication with Bitwig.

    Sends commands to Bitwig via DrivenByMoss OSC protocol,
    receives state updates in a background thread.
    """

    def __init__(
        self,
        bitwig_host: str = "127.0.0.1",
        send_port: int = 8000,
        receive_port: int = 9000,
    ):
        self.bitwig_host = bitwig_host
        self.send_port = send_port
        self.receive_port = receive_port
        self.state = BitwigState()

        self._client = None
        self._server = None
        self._server_thread: Optional[threading.Thread] = None
        self._connected = False

    def connect(self, timeout: float = 3.0) -> dict:
        """Establish OSC connection to Bitwig.

        Starts the OSC client (sender) and server (receiver).
        Returns connection status dict.
        """
        _check_osc_lib()

        from pythonosc.udp_client import SimpleUDPClient
        from pythonosc.osc_server import ThreadingOSCUDPServer
        from pythonosc.dispatcher import Dispatcher

        # Create sender
        self._client = SimpleUDPClient(self.bitwig_host, self.send_port)

        # Create receiver with state-caching handlers
        dispatcher = Dispatcher()
        self._register_handlers(dispatcher)

        # Try to bind the receive port
        try:
            self._server = ThreadingOSCUDPServer(
                ("0.0.0.0", self.receive_port), dispatcher
            )
        except OSError as e:
            if "Address already in use" in str(e):
                raise RuntimeError(
                    f"Port {self.receive_port} is already in use. "
                    f"Another cli-anything-bitwig instance may be running. "
                    f"Use --receive-port to specify a different port."
                )
            raise

        # Start listener thread
        self._server_thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
            name="bitwig-osc-listener",
        )
        self._server_thread.start()

        # Ping Bitwig to trigger state updates
        self._client.send_message("/refresh", [])

        # Wait briefly for initial state
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.state.last_update > 0:
                self._connected = True
                break
            time.sleep(0.05)

        return {
            "connected": self._connected,
            "host": self.bitwig_host,
            "send_port": self.send_port,
            "receive_port": self.receive_port,
            "state_received": self.state.last_update > 0,
        }

    def disconnect(self):
        """Shut down OSC connection."""
        if self._server:
            self._server.shutdown()
            self._server = None
        self._server_thread = None
        self._client = None
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def send(self, address: str, *args) -> None:
        """Send an OSC message to Bitwig.

        Args:
            address: OSC address (e.g., "/play", "/track/1/volume")
            *args: Message arguments (floats, ints, strings)
        """
        if not self._client:
            raise RuntimeError(
                "Not connected to Bitwig. Run 'connect' first."
            )
        self._client.send_message(address, list(args) if args else [])

    def send_and_wait(self, address: str, *args, wait: float = 0.1) -> None:
        """Send an OSC message and wait briefly for state to update."""
        before = self.state.last_update
        self.send(address, *args)
        deadline = time.time() + wait
        while time.time() < deadline:
            if self.state.last_update > before:
                return
            time.sleep(0.01)

    # ── State handler registration ─────────────────────────────────

    def _register_handlers(self, dispatcher):
        """Register OSC message handlers that populate the state cache."""
        from pythonosc.dispatcher import Dispatcher

        # Transport
        dispatcher.map("/play", self._h_transport_bool, "playing")
        dispatcher.map("/record", self._h_transport_bool, "recording")
        dispatcher.map("/repeat", self._h_transport_bool, "loop")
        dispatcher.map("/click", self._h_transport_bool, "click")
        dispatcher.map("/overdub", self._h_transport_bool, "overdub")
        dispatcher.map("/automationWriteMode", self._h_transport_str, "automation_write_mode")
        dispatcher.map("/tempo/raw", self._h_transport_float, "tempo")
        dispatcher.map("/beat/str", self._h_transport_str, "position")
        dispatcher.map("/time/str", self._h_transport_str, "time_str")
        dispatcher.map("/numerator", self._h_transport_int, "numerator")
        dispatcher.map("/denominator", self._h_transport_int, "denominator")

        # Tracks (1-8 bank)
        for i in range(1, 9):
            prefix = f"/track/{i}"
            dispatcher.map(f"{prefix}/name", self._h_track_str, i, "name")
            dispatcher.map(f"{prefix}/type", self._h_track_str, i, "type")
            dispatcher.map(f"{prefix}/color", self._h_track_str, i, "color")
            dispatcher.map(f"{prefix}/volume", self._h_track_float, i, "volume")
            dispatcher.map(f"{prefix}/volumeStr", self._h_track_str, i, "volume_str")
            dispatcher.map(f"{prefix}/pan", self._h_track_float, i, "pan")
            dispatcher.map(f"{prefix}/panStr", self._h_track_str, i, "pan_str")
            dispatcher.map(f"{prefix}/mute", self._h_track_bool, i, "mute")
            dispatcher.map(f"{prefix}/solo", self._h_track_bool, i, "solo")
            dispatcher.map(f"{prefix}/recarm", self._h_track_bool, i, "recarm")
            dispatcher.map(f"{prefix}/monitor", self._h_track_str, i, "monitor")
            dispatcher.map(f"{prefix}/selected", self._h_track_bool, i, "selected")
            dispatcher.map(f"{prefix}/exists", self._h_track_bool, i, "exists")
            dispatcher.map(f"{prefix}/VUvalue", self._h_track_float, i, "vu")

            # Sends (1-8)
            for s in range(1, 9):
                dispatcher.map(
                    f"{prefix}/send/{s}/volume",
                    self._h_track_send_float, i, s, "volume",
                )
                dispatcher.map(
                    f"{prefix}/send/{s}/name",
                    self._h_track_send_str, i, s, "name",
                )

            # Clips (1-8)
            for c in range(1, 9):
                dispatcher.map(
                    f"{prefix}/clip/{c}/name",
                    self._h_clip_str, i, c, "name",
                )
                dispatcher.map(
                    f"{prefix}/clip/{c}/color",
                    self._h_clip_str, i, c, "color",
                )
                dispatcher.map(
                    f"{prefix}/clip/{c}/isPlaying",
                    self._h_clip_bool, i, c, "playing",
                )
                dispatcher.map(
                    f"{prefix}/clip/{c}/isRecording",
                    self._h_clip_bool, i, c, "recording",
                )
                dispatcher.map(
                    f"{prefix}/clip/{c}/isQueued",
                    self._h_clip_bool, i, c, "queued",
                )
                dispatcher.map(
                    f"{prefix}/clip/{c}/hasContent",
                    self._h_clip_bool, i, c, "has_content",
                )

        # Master track
        dispatcher.map("/master/volume", self._h_master_float, "volume")
        dispatcher.map("/master/volumeStr", self._h_master_str, "volume_str")
        dispatcher.map("/master/pan", self._h_master_float, "pan")
        dispatcher.map("/master/mute", self._h_master_bool, "mute")
        dispatcher.map("/master/solo", self._h_master_bool, "solo")
        dispatcher.map("/master/VUvalue", self._h_master_float, "vu")

        # Scenes (1-8)
        for i in range(1, 9):
            dispatcher.map(f"/scene/{i}/name", self._h_scene_str, i, "name")
            dispatcher.map(f"/scene/{i}/color", self._h_scene_str, i, "color")
            dispatcher.map(f"/scene/{i}/exists", self._h_scene_bool, i, "exists")

        # Device
        dispatcher.map("/device/name", self._h_device_str, "name")
        dispatcher.map("/device/bypass", self._h_device_bool, "bypass")
        dispatcher.map("/device/page/name", self._h_device_str, "page_name")
        for i in range(1, 9):
            dispatcher.map(f"/device/param/{i}/name", self._h_device_param_str, i, "name")
            dispatcher.map(f"/device/param/{i}/value", self._h_device_param_float, i, "value")
            dispatcher.map(f"/device/param/{i}/valueStr", self._h_device_param_str, i, "value_str")
            dispatcher.map(f"/device/param/{i}/exists", self._h_device_param_bool, i, "exists")

        # Browser
        dispatcher.map("/browser/isActive", self._h_simple_set, "browser", "active")

        # Project
        dispatcher.map("/project/name", self._h_simple_set, "project", "name")
        dispatcher.map("/project/engine", self._h_simple_set, "project", "engine")

        # Layout
        dispatcher.map("/layout", self._h_layout)

        # Catch-all for unhandled messages (debug)
        dispatcher.set_default_handler(self._h_default)

    # ── Handler methods ────────────────────────────────────────────

    def _h_transport_bool(self, address, *args):
        key = args[0]  # handler data
        val = bool(args[1]) if len(args) > 1 else False
        self.state.set("transport", key, val)

    def _h_transport_float(self, address, *args):
        key = args[0]
        val = float(args[1]) if len(args) > 1 else 0.0
        self.state.set("transport", key, val)

    def _h_transport_int(self, address, *args):
        key = args[0]
        val = int(args[1]) if len(args) > 1 else 0
        self.state.set("transport", key, val)

    def _h_transport_str(self, address, *args):
        key = args[0]
        val = str(args[1]) if len(args) > 1 else ""
        self.state.set("transport", key, val)

    def _h_track_str(self, address, *args):
        track_num, key = args[0], args[1]
        val = str(args[2]) if len(args) > 2 else ""
        self._ensure_track(track_num)
        self.state.set("tracks", track_num, key, val)

    def _h_track_float(self, address, *args):
        track_num, key = args[0], args[1]
        val = float(args[2]) if len(args) > 2 else 0.0
        self._ensure_track(track_num)
        self.state.set("tracks", track_num, key, val)

    def _h_track_bool(self, address, *args):
        track_num, key = args[0], args[1]
        val = bool(args[2]) if len(args) > 2 else False
        self._ensure_track(track_num)
        self.state.set("tracks", track_num, key, val)

    def _h_track_send_float(self, address, *args):
        track_num, send_num, key = args[0], args[1], args[2]
        val = float(args[3]) if len(args) > 3 else 0.0
        self._ensure_track(track_num)
        sends = self.state.get("tracks", track_num, "sends") or {}
        if send_num not in sends:
            sends[send_num] = {}
        sends[send_num][key] = val
        self.state.set("tracks", track_num, "sends", sends)

    def _h_track_send_str(self, address, *args):
        track_num, send_num, key = args[0], args[1], args[2]
        val = str(args[3]) if len(args) > 3 else ""
        self._ensure_track(track_num)
        sends = self.state.get("tracks", track_num, "sends") or {}
        if send_num not in sends:
            sends[send_num] = {}
        sends[send_num][key] = val
        self.state.set("tracks", track_num, "sends", sends)

    def _h_clip_str(self, address, *args):
        track_num, clip_num, key = args[0], args[1], args[2]
        val = str(args[3]) if len(args) > 3 else ""
        self._ensure_clip(track_num, clip_num)
        self.state.set("tracks", track_num, "clips", clip_num, key, val)

    def _h_clip_bool(self, address, *args):
        track_num, clip_num, key = args[0], args[1], args[2]
        val = bool(args[3]) if len(args) > 3 else False
        self._ensure_clip(track_num, clip_num)
        self.state.set("tracks", track_num, "clips", clip_num, key, val)

    def _h_master_float(self, address, *args):
        key = args[0]
        val = float(args[1]) if len(args) > 1 else 0.0
        self.state.set("master", key, val)

    def _h_master_str(self, address, *args):
        key = args[0]
        val = str(args[1]) if len(args) > 1 else ""
        self.state.set("master", key, val)

    def _h_master_bool(self, address, *args):
        key = args[0]
        val = bool(args[1]) if len(args) > 1 else False
        self.state.set("master", key, val)

    def _h_scene_str(self, address, *args):
        scene_num, key = args[0], args[1]
        val = str(args[2]) if len(args) > 2 else ""
        self._ensure_scene(scene_num)
        self.state.set("scenes", scene_num, key, val)

    def _h_scene_bool(self, address, *args):
        scene_num, key = args[0], args[1]
        val = bool(args[2]) if len(args) > 2 else False
        self._ensure_scene(scene_num)
        self.state.set("scenes", scene_num, key, val)

    def _h_device_str(self, address, *args):
        key = args[0]
        val = str(args[1]) if len(args) > 1 else ""
        self.state.set("device", key, val)

    def _h_device_bool(self, address, *args):
        key = args[0]
        val = bool(args[1]) if len(args) > 1 else False
        self.state.set("device", key, val)

    def _h_device_param_str(self, address, *args):
        param_num, key = args[0], args[1]
        val = str(args[2]) if len(args) > 2 else ""
        params = self.state.get("device", "params") or {}
        if param_num not in params:
            params[param_num] = {}
        params[param_num][key] = val
        self.state.set("device", "params", params)

    def _h_device_param_float(self, address, *args):
        param_num, key = args[0], args[1]
        val = float(args[2]) if len(args) > 2 else 0.0
        params = self.state.get("device", "params") or {}
        if param_num not in params:
            params[param_num] = {}
        params[param_num][key] = val
        self.state.set("device", "params", params)

    def _h_device_param_bool(self, address, *args):
        param_num, key = args[0], args[1]
        val = bool(args[2]) if len(args) > 2 else False
        params = self.state.get("device", "params") or {}
        if param_num not in params:
            params[param_num] = {}
        params[param_num][key] = val
        self.state.set("device", "params", params)

    def _h_simple_set(self, address, *args):
        section, key = args[0], args[1]
        val = args[2] if len(args) > 2 else None
        self.state.set(section, key, val)

    def _h_layout(self, address, *args):
        val = str(args[0]) if args else "arrange"
        self.state.set("layout", val)

    def _h_default(self, address, *args):
        """Default handler for unregistered addresses — just update timestamp."""
        self.state._last_update = time.time()

    # ── Helpers ────────────────────────────────────────────────────

    def _ensure_track(self, num: int):
        tracks = self.state.get("tracks") or {}
        if num not in tracks:
            self.state.set("tracks", num, {
                "name": "", "type": "", "volume": 0.0, "pan": 0.5,
                "mute": False, "solo": False, "recarm": False,
                "exists": False, "selected": False, "sends": {}, "clips": {},
            })

    def _ensure_clip(self, track_num: int, clip_num: int):
        self._ensure_track(track_num)
        clips = self.state.get("tracks", track_num, "clips") or {}
        if clip_num not in clips:
            clips[clip_num] = {
                "name": "", "playing": False, "recording": False,
                "queued": False, "has_content": False,
            }
            self.state.set("tracks", track_num, "clips", clips)

    def _ensure_scene(self, num: int):
        scenes = self.state.get("scenes") or {}
        if num not in scenes:
            self.state.set("scenes", num, {
                "name": "", "exists": False,
            })


def check_bitwig_reachable(host: str = "127.0.0.1", port: int = 8000) -> bool:
    """Quick check if the Bitwig OSC port is reachable (UDP is connectionless,
    so this just verifies the port isn't obviously blocked)."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.5)
        # Send a minimal ping — DrivenByMoss will respond with state
        sock.sendto(b"/ping\x00\x00\x00,\x00\x00\x00", (host, port))
        sock.close()
        return True
    except (socket.error, OSError):
        return False
