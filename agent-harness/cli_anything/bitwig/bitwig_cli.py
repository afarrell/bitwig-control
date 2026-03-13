"""cli-anything-bitwig: CLI harness for controlling Bitwig Studio via OSC.

Uses DrivenByMoss OSC protocol to send commands to a running Bitwig instance
and receive state updates. Supports one-shot commands and interactive REPL.
"""

import functools
import json
import sys
from typing import Optional

import click

from cli_anything.bitwig.core.session import Session

# ── Global state ───────────────────────────────────────────────────────

_json_output: bool = False
_repl_mode: bool = False
_session: Optional[Session] = None


def get_session() -> Session:
    """Get or create the global session (lazy init)."""
    global _session
    if _session is None:
        _session = Session.load_config()
    return _session


def get_connected_session(timeout: float = 3.0) -> Session:
    """Get session, auto-connecting if needed. For one-shot CLI commands."""
    sess = get_session()
    if not sess.connected:
        sess.connect(timeout=timeout)
    return sess


# ── Output helpers ─────────────────────────────────────────────────────

def output(data: dict, message: str = ""):
    """Dual-mode output: JSON for agents, human-readable for terminals."""
    if _json_output:
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        if message:
            click.echo(message)
        _print_dict(data)


def _print_dict(d: dict, indent: int = 2):
    """Pretty-print a dict for human consumption."""
    for key, val in d.items():
        prefix = " " * indent
        if isinstance(val, dict):
            click.echo(f"{prefix}{key}:")
            _print_dict(val, indent + 2)
        elif isinstance(val, list):
            click.echo(f"{prefix}{key}: [{len(val)} items]")
            for i, item in enumerate(val):
                if isinstance(item, dict):
                    click.echo(f"{prefix}  [{i}]:")
                    _print_dict(item, indent + 4)
                else:
                    click.echo(f"{prefix}  [{i}]: {item}")
        else:
            click.echo(f"{prefix}{key}: {val}")


# ── Error handling ─────────────────────────────────────────────────────

def handle_error(f):
    """Decorator: catch exceptions and format as JSON or human errors."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except (ValueError, IndexError) as e:
            _emit_error(str(e), "validation_error")
        except FileNotFoundError as e:
            _emit_error(str(e), "file_not_found")
        except RuntimeError as e:
            _emit_error(str(e), "runtime_error")
        except ConnectionError as e:
            _emit_error(str(e), "connection_error")
        except Exception as e:
            _emit_error(str(e), type(e).__name__)
    return wrapper


def _emit_error(message: str, error_type: str):
    if _json_output:
        click.echo(json.dumps({"error": message, "type": error_type}))
    else:
        click.echo(f"Error: {message}", err=True)
    if not _repl_mode:
        sys.exit(1)


# ── CLI root ───────────────────────────────────────────────────────────

@click.group(invoke_without_command=True)
@click.option("--json", "use_json", is_flag=True, help="Output as JSON (for agents)")
@click.option("--host", default=None, help="Bitwig OSC host (default: 127.0.0.1)")
@click.option("--send-port", default=None, type=int, help="OSC send port (default: 8000)")
@click.option("--receive-port", default=None, type=int, help="OSC receive port (default: 9000)")
@click.pass_context
def cli(ctx, use_json, host, send_port, receive_port):
    """cli-anything-bitwig: Control Bitwig Studio from the command line.

    Communicates with a running Bitwig instance via OSC (DrivenByMoss).
    Requires Bitwig Studio running with DrivenByMoss OSC controller configured.
    """
    global _json_output, _session
    _json_output = use_json

    # Apply connection overrides
    sess = get_session()
    if host:
        sess.host = host
    if send_port:
        sess.send_port = send_port
    if receive_port:
        sess.receive_port = receive_port

    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)
    elif ctx.invoked_subcommand not in ("connect", "disconnect", "status", "repl"):
        # Auto-connect for commands that need a live session
        if not sess.connected:
            try:
                sess.connect(timeout=3.0)
            except Exception:
                pass  # Let the command itself handle the error


# ── Connect command ────────────────────────────────────────────────────

@cli.command()
@click.option("--timeout", default=3.0, help="Connection timeout in seconds")
@handle_error
def connect(timeout):
    """Connect to Bitwig Studio via OSC."""
    sess = get_session()
    result = sess.connect(timeout=timeout)
    output(result, "Connected to Bitwig Studio")


@cli.command()
@handle_error
def disconnect():
    """Disconnect from Bitwig Studio."""
    sess = get_session()
    result = sess.disconnect()
    output(result, "Disconnected")


@cli.command(name="status")
@handle_error
def connection_status():
    """Show connection status."""
    sess = get_session()
    result = sess.status()
    output(result, "Connection Status")


@cli.command(name="state")
@handle_error
def full_state():
    """Dump the full cached Bitwig state (for debugging)."""
    sess = get_session()
    result = sess.full_state()
    output(result, "Full Bitwig State")


# ── Transport commands ─────────────────────────────────────────────────

@cli.group()
def transport():
    """Transport controls: play, stop, record, tempo, loop."""
    pass


@transport.command()
@handle_error
def play():
    """Start playback."""
    from cli_anything.bitwig.core.transport import play as _play
    result = _play(get_session())
    output(result, "Playing")


@transport.command()
@handle_error
def stop():
    """Stop playback."""
    from cli_anything.bitwig.core.transport import stop as _stop
    result = _stop(get_session())
    output(result, "Stopped")


@transport.command()
@handle_error
def record():
    """Toggle recording."""
    from cli_anything.bitwig.core.transport import record as _record
    result = _record(get_session())
    output(result, "Record toggled")


@transport.command()
@handle_error
def restart():
    """Restart playback from beginning."""
    from cli_anything.bitwig.core.transport import restart as _restart
    result = _restart(get_session())
    output(result, "Restarted")


@transport.command()
@handle_error
def loop():
    """Toggle loop mode."""
    from cli_anything.bitwig.core.transport import toggle_loop
    result = toggle_loop(get_session())
    output(result, "Loop toggled")


@transport.command(name="click")
@handle_error
def click_cmd():
    """Toggle metronome click."""
    from cli_anything.bitwig.core.transport import toggle_click
    result = toggle_click(get_session())
    output(result, "Click toggled")


@transport.command()
@handle_error
def overdub():
    """Toggle overdub mode."""
    from cli_anything.bitwig.core.transport import toggle_overdub
    result = toggle_overdub(get_session())
    output(result, "Overdub toggled")


@transport.command()
@click.argument("bpm", type=float)
@handle_error
def tempo(bpm):
    """Set tempo in BPM (20-666)."""
    from cli_anything.bitwig.core.transport import set_tempo
    result = set_tempo(get_session(), bpm)
    output(result, f"Tempo set to {bpm} BPM")


@transport.command()
@handle_error
def tap():
    """Tap tempo."""
    from cli_anything.bitwig.core.transport import tap_tempo
    result = tap_tempo(get_session())
    output(result, "Tap tempo registered")


@transport.command()
@click.argument("beats", type=float)
@handle_error
def position(beats):
    """Set playback position in beats."""
    from cli_anything.bitwig.core.transport import set_position
    result = set_position(get_session(), beats)
    output(result, f"Position set to beat {beats}")


@transport.command(name="status")
@handle_error
def transport_status():
    """Show transport state."""
    from cli_anything.bitwig.core.transport import status as _status
    result = _status(get_session())
    output(result, "Transport Status")


# ── Track commands ─────────────────────────────────────────────────────

@cli.group()
def track():
    """Track controls: volume, pan, mute, solo, arm, sends."""
    pass


@track.command(name="list")
@handle_error
def track_list():
    """List tracks in the current bank."""
    from cli_anything.bitwig.core.tracks import list_tracks
    result = list_tracks(get_session())
    output(result, "Tracks")


@track.command()
@click.argument("num", type=int)
@handle_error
def info(num):
    """Get info for a track (1-8 in bank)."""
    from cli_anything.bitwig.core.tracks import get_track
    result = get_track(get_session(), num)
    output(result, f"Track {num}")


@track.command()
@click.argument("num", type=int)
@handle_error
def select(num):
    """Select a track (1-8 in bank)."""
    from cli_anything.bitwig.core.tracks import select as _select
    result = _select(get_session(), num)
    output(result, f"Selected track {num}")


@track.command()
@click.argument("num", type=int)
@click.argument("value", type=float)
@handle_error
def volume(num, value):
    """Set track volume (0.0-1.0)."""
    from cli_anything.bitwig.core.tracks import set_volume
    result = set_volume(get_session(), num, value)
    output(result, f"Track {num} volume set to {value}")


@track.command()
@click.argument("num", type=int)
@click.argument("value", type=float)
@handle_error
def pan(num, value):
    """Set track pan (0.0=L, 0.5=C, 1.0=R)."""
    from cli_anything.bitwig.core.tracks import set_pan
    result = set_pan(get_session(), num, value)
    output(result, f"Track {num} pan set to {value}")


@track.command()
@click.argument("num", type=int)
@handle_error
def mute(num):
    """Toggle track mute."""
    from cli_anything.bitwig.core.tracks import toggle_mute
    result = toggle_mute(get_session(), num)
    output(result, f"Track {num} mute toggled")


@track.command()
@click.argument("num", type=int)
@handle_error
def solo(num):
    """Toggle track solo."""
    from cli_anything.bitwig.core.tracks import toggle_solo
    result = toggle_solo(get_session(), num)
    output(result, f"Track {num} solo toggled")


@track.command()
@click.argument("num", type=int)
@handle_error
def arm(num):
    """Toggle track record arm."""
    from cli_anything.bitwig.core.tracks import toggle_arm
    result = toggle_arm(get_session(), num)
    output(result, f"Track {num} arm toggled")


@track.command()
@click.argument("track_num", type=int)
@click.argument("send_num", type=int)
@click.argument("value", type=float)
@handle_error
def send(track_num, send_num, value):
    """Set send level: track send value (0.0-1.0)."""
    from cli_anything.bitwig.core.tracks import set_send
    result = set_send(get_session(), track_num, send_num, value)
    output(result, f"Track {track_num} send {send_num} set to {value}")


@track.group(name="add")
def track_add():
    """Add a new track."""
    pass


@track_add.command(name="audio")
@handle_error
def add_audio():
    """Add a new audio track."""
    from cli_anything.bitwig.core.tracks import add_audio_track
    result = add_audio_track(get_session())
    output(result, "Audio track added")


@track_add.command(name="instrument")
@handle_error
def add_instrument():
    """Add a new instrument track."""
    from cli_anything.bitwig.core.tracks import add_instrument_track
    result = add_instrument_track(get_session())
    output(result, "Instrument track added")


@track_add.command(name="effect")
@handle_error
def add_effect():
    """Add a new effect track."""
    from cli_anything.bitwig.core.tracks import add_effect_track
    result = add_effect_track(get_session())
    output(result, "Effect track added")


@track.command(name="bank")
@click.argument("direction", type=click.Choice(["+", "-"]))
@handle_error
def track_bank(direction):
    """Scroll track bank: + (forward) or - (backward)."""
    from cli_anything.bitwig.core.tracks import scroll_bank
    d = 1 if direction == "+" else -1
    result = scroll_bank(get_session(), d)
    output(result, f"Track bank scrolled {'forward' if d > 0 else 'backward'}")


# ── Clip commands ──────────────────────────────────────────────────────

@cli.group()
def clip():
    """Clip launcher: launch, stop, record, list clips."""
    pass


@clip.command()
@click.argument("track_num", type=int)
@click.argument("slot_num", type=int)
@handle_error
def launch(track_num, slot_num):
    """Launch a clip: track slot."""
    from cli_anything.bitwig.core.clips import launch as _launch
    result = _launch(get_session(), track_num, slot_num)
    output(result, f"Clip launched: track {track_num}, slot {slot_num}")


@clip.command(name="stop")
@click.argument("track_num", type=int)
@handle_error
def clip_stop(track_num):
    """Stop clips on a track."""
    from cli_anything.bitwig.core.clips import stop as _stop
    result = _stop(get_session(), track_num)
    output(result, f"Clips stopped on track {track_num}")


@clip.command(name="stop-all")
@handle_error
def clip_stop_all():
    """Stop all clips."""
    from cli_anything.bitwig.core.clips import stop_all
    result = stop_all(get_session())
    output(result, "All clips stopped")


@clip.command(name="record")
@click.argument("track_num", type=int)
@click.argument("slot_num", type=int)
@handle_error
def clip_record(track_num, slot_num):
    """Record into a clip slot."""
    from cli_anything.bitwig.core.clips import record as _record
    result = _record(get_session(), track_num, slot_num)
    output(result, f"Recording into track {track_num}, slot {slot_num}")


@clip.command(name="list")
@click.argument("track_num", type=int)
@handle_error
def clip_list(track_num):
    """List clips for a track."""
    from cli_anything.bitwig.core.clips import list_clips
    result = list_clips(get_session(), track_num)
    output(result, f"Clips on track {track_num}")


@clip.command(name="grid")
@handle_error
def clip_grid():
    """Show the full clip launcher grid (8x8)."""
    from cli_anything.bitwig.core.clips import grid
    result = grid(get_session())
    output(result, "Clip Launcher Grid")


# ── Scene commands ─────────────────────────────────────────────────────

@cli.group()
def scene():
    """Scene controls: launch, list, navigate."""
    pass


@scene.command()
@click.argument("num", type=int)
@handle_error
def launch(num):
    """Launch a scene (1-8 in bank)."""
    from cli_anything.bitwig.core.scenes import launch as _launch
    result = _launch(get_session(), num)
    output(result, f"Scene {num} launched")


@scene.command(name="list")
@handle_error
def scene_list():
    """List scenes in the current bank."""
    from cli_anything.bitwig.core.scenes import list_scenes
    result = list_scenes(get_session())
    output(result, "Scenes")


@scene.command(name="bank")
@click.argument("direction", type=click.Choice(["+", "-"]))
@handle_error
def scene_bank(direction):
    """Scroll scene bank: + or -."""
    from cli_anything.bitwig.core.scenes import scroll_bank
    d = 1 if direction == "+" else -1
    result = scroll_bank(get_session(), d)
    output(result, f"Scene bank scrolled {'forward' if d > 0 else 'backward'}")


# ── Device commands ────────────────────────────────────────────────────

@cli.group()
def device():
    """Device/plugin controls: parameters, bypass, window, navigate."""
    pass


@device.command(name="status")
@handle_error
def device_status():
    """Show current device and parameters."""
    from cli_anything.bitwig.core.devices import status as _status
    result = _status(get_session())
    output(result, "Device")


@device.command()
@click.argument("num", type=int)
@click.argument("value", type=float)
@handle_error
def param(num, value):
    """Set a device parameter (1-8, value 0.0-1.0)."""
    from cli_anything.bitwig.core.devices import set_param
    result = set_param(get_session(), num, value)
    output(result, f"Parameter {num} set to {value}")


@device.command()
@handle_error
def bypass():
    """Toggle device bypass."""
    from cli_anything.bitwig.core.devices import toggle_bypass
    result = toggle_bypass(get_session())
    output(result, "Bypass toggled")


@device.command()
@handle_error
def window():
    """Toggle device plugin window."""
    from cli_anything.bitwig.core.devices import toggle_window
    result = toggle_window(get_session())
    output(result, "Window toggled")


@device.command(name="next")
@handle_error
def device_next():
    """Navigate to next device."""
    from cli_anything.bitwig.core.devices import navigate
    result = navigate(get_session(), 1)
    output(result, "Navigated to next device")


@device.command(name="prev")
@handle_error
def device_prev():
    """Navigate to previous device."""
    from cli_anything.bitwig.core.devices import navigate
    result = navigate(get_session(), -1)
    output(result, "Navigated to previous device")


@device.command(name="page-next")
@handle_error
def device_page_next():
    """Navigate to next parameter page."""
    from cli_anything.bitwig.core.devices import navigate_page
    result = navigate_page(get_session(), 1)
    output(result, "Navigated to next parameter page")


@device.command(name="page-prev")
@handle_error
def device_page_prev():
    """Navigate to previous parameter page."""
    from cli_anything.bitwig.core.devices import navigate_page
    result = navigate_page(get_session(), -1)
    output(result, "Navigated to previous parameter page")


# ── Mixer commands ─────────────────────────────────────────────────────

@cli.group()
def mixer():
    """Mixer: master volume/pan, mixer status."""
    pass


@mixer.command(name="status")
@handle_error
def mixer_status():
    """Show full mixer status."""
    from cli_anything.bitwig.core.mixer import status as _status
    result = _status(get_session())
    output(result, "Mixer Status")


@mixer.command(name="master-volume")
@click.argument("value", type=float)
@handle_error
def master_volume(value):
    """Set master volume (0.0-1.0)."""
    from cli_anything.bitwig.core.mixer import set_master_volume
    result = set_master_volume(get_session(), value)
    output(result, f"Master volume set to {value}")


@mixer.command(name="master-pan")
@click.argument("value", type=float)
@handle_error
def master_pan(value):
    """Set master pan (0.0=L, 0.5=C, 1.0=R)."""
    from cli_anything.bitwig.core.mixer import set_master_pan
    result = set_master_pan(get_session(), value)
    output(result, f"Master pan set to {value}")


@mixer.command(name="master-mute")
@handle_error
def master_mute():
    """Toggle master mute."""
    from cli_anything.bitwig.core.mixer import toggle_master_mute
    result = toggle_master_mute(get_session())
    output(result, "Master mute toggled")


# ── Browser commands ───────────────────────────────────────────────────

@cli.group()
def browser():
    """Device/preset browser: open, navigate, commit."""
    pass


@browser.command(name="preset")
@handle_error
def browser_preset():
    """Open preset browser."""
    from cli_anything.bitwig.core.browser import open_presets
    result = open_presets(get_session())
    output(result, "Preset browser opened")


@browser.command(name="device")
@handle_error
def browser_device():
    """Open device browser."""
    from cli_anything.bitwig.core.browser import open_devices
    result = open_devices(get_session())
    output(result, "Device browser opened")


@browser.command()
@handle_error
def commit():
    """Confirm browser selection."""
    from cli_anything.bitwig.core.browser import commit as _commit
    result = _commit(get_session())
    output(result, "Browser selection confirmed")


@browser.command()
@handle_error
def cancel():
    """Cancel and close browser."""
    from cli_anything.bitwig.core.browser import cancel as _cancel
    result = _cancel(get_session())
    output(result, "Browser cancelled")


@browser.command(name="next")
@handle_error
def browser_next():
    """Navigate to next browser result."""
    from cli_anything.bitwig.core.browser import navigate_result
    result = navigate_result(get_session(), 1)
    output(result, "Next result")


@browser.command(name="prev")
@handle_error
def browser_prev():
    """Navigate to previous browser result."""
    from cli_anything.bitwig.core.browser import navigate_result
    result = navigate_result(get_session(), -1)
    output(result, "Previous result")


@browser.command(name="status")
@handle_error
def browser_status():
    """Show browser state."""
    from cli_anything.bitwig.core.browser import status as _status
    result = _status(get_session())
    output(result, "Browser Status")


# ── Project commands ───────────────────────────────────────────────────

@cli.group()
def project():
    """Project: save, undo, redo, layout."""
    pass


@project.command()
@handle_error
def save():
    """Save the current project."""
    from cli_anything.bitwig.core.project import save as _save
    result = _save(get_session())
    output(result, "Project saved")


@project.command(name="status")
@handle_error
def project_status():
    """Show project info."""
    from cli_anything.bitwig.core.project import status as _status
    result = _status(get_session())
    output(result, "Project")


@project.command()
@click.argument("layout", type=click.Choice(["arrange", "mix", "edit"]))
@handle_error
def layout(layout):
    """Switch layout: arrange, mix, or edit."""
    from cli_anything.bitwig.core.project import set_layout
    result = set_layout(get_session(), layout)
    output(result, f"Layout switched to {layout}")


@project.command()
@handle_error
def engine():
    """Toggle audio engine on/off."""
    from cli_anything.bitwig.core.project import toggle_engine
    result = toggle_engine(get_session())
    output(result, "Audio engine toggled")


# ── Top-level undo/redo ────────────────────────────────────────────────

@cli.command()
@handle_error
def undo():
    """Undo last action."""
    from cli_anything.bitwig.core.project import undo as _undo
    result = _undo(get_session())
    output(result, "Undone")


@cli.command()
@handle_error
def redo():
    """Redo last undone action."""
    from cli_anything.bitwig.core.project import redo as _redo
    result = _redo(get_session())
    output(result, "Redone")


# ── REPL ───────────────────────────────────────────────────────────────

@cli.command()
@handle_error
def repl():
    """Start interactive REPL mode (default when no subcommand given)."""
    global _repl_mode
    _repl_mode = True

    from cli_anything.bitwig.utils.repl_skin import ReplSkin

    skin = ReplSkin("bitwig", version="1.0.0")
    skin.print_banner()

    # Auto-connect on REPL start
    sess = get_session()
    try:
        result = sess.connect()
        if result.get("status") == "connected":
            skin.success(f"Connected to Bitwig at {sess.host}:{sess.send_port}")
        elif result.get("status") == "already_connected":
            skin.info("Already connected")
    except RuntimeError as e:
        skin.warning(str(e))
        skin.hint("Use 'connect' to retry when Bitwig is ready")

    pt_session = skin.create_prompt_session()

    while True:
        try:
            # Build prompt context from state
            project_name = ""
            if sess.connected:
                project_name = sess.get_state("project", "name") or "connected"

            line = skin.get_input(
                pt_session,
                project_name=project_name,
                context="" if project_name else "disconnected",
            )
        except (EOFError, KeyboardInterrupt):
            break

        if not line:
            continue
        if line in ("quit", "exit", "q"):
            break
        if line == "help":
            _repl_help(skin)
            continue

        # Parse and re-invoke through Click
        args = line.split()
        try:
            cli.main(args, standalone_mode=False)
        except SystemExit:
            pass
        except Exception as e:
            skin.error(str(e))

    # Clean up
    if sess.connected:
        sess.disconnect()
    skin.print_goodbye()


def _repl_help(skin):
    """Show REPL help."""
    skin.help({
        "connect": "Connect to Bitwig Studio",
        "disconnect": "Disconnect from Bitwig",
        "status": "Show connection status",
        "transport play|stop|record": "Transport controls",
        "transport tempo <bpm>": "Set tempo",
        "transport loop|click": "Toggle loop/metronome",
        "transport status": "Show transport state",
        "track list": "List tracks in bank",
        "track volume <n> <val>": "Set track volume (0-1)",
        "track pan <n> <val>": "Set track pan (0-1)",
        "track mute|solo|arm <n>": "Toggle track state",
        "track send <t> <s> <val>": "Set send level",
        "track add audio|instrument|effect": "Add track",
        "track bank +|-": "Scroll track bank",
        "clip launch <t> <s>": "Launch clip",
        "clip stop <t>": "Stop clips on track",
        "clip grid": "Show clip launcher grid",
        "scene launch <n>": "Launch scene",
        "scene list": "List scenes",
        "device status": "Show device info",
        "device param <n> <val>": "Set device parameter",
        "device bypass|window": "Toggle bypass/window",
        "device next|prev": "Navigate devices",
        "mixer status": "Show mixer",
        "mixer master-volume <val>": "Set master volume",
        "browser preset|device": "Open browser",
        "browser next|prev|commit|cancel": "Navigate browser",
        "project save": "Save project",
        "project layout arrange|mix|edit": "Switch layout",
        "undo / redo": "Undo/redo",
        "state": "Dump full state (debug)",
        "quit": "Exit REPL",
    })


# ── Entry point ────────────────────────────────────────────────────────

def main():
    cli()


if __name__ == "__main__":
    main()
