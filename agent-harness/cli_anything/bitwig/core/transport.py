"""Transport control for Bitwig Studio.

Play, stop, record, tempo, loop, metronome, position, automation mode.
"""

from cli_anything.bitwig.core.session import Session


def play(session: Session) -> dict:
    """Start playback."""
    session.send("/play", 1)
    return {"action": "play", "sent": True}


def stop(session: Session) -> dict:
    """Stop playback."""
    session.send("/stop", 1)
    return {"action": "stop", "sent": True}


def record(session: Session) -> dict:
    """Toggle recording."""
    session.send("/record", 1)
    return {"action": "record", "sent": True}


def restart(session: Session) -> dict:
    """Restart playback from beginning."""
    session.send("/restart", 1)
    return {"action": "restart", "sent": True}


def toggle_loop(session: Session) -> dict:
    """Toggle loop mode."""
    session.send("/repeat", 1)
    return {"action": "loop_toggle", "sent": True}


def toggle_click(session: Session) -> dict:
    """Toggle metronome click."""
    session.send("/click", 1)
    return {"action": "click_toggle", "sent": True}


def toggle_overdub(session: Session) -> dict:
    """Toggle overdub mode."""
    session.send("/overdub", 1)
    return {"action": "overdub_toggle", "sent": True}


def set_tempo(session: Session, bpm: float) -> dict:
    """Set tempo in BPM."""
    if bpm < 20 or bpm > 666:
        raise ValueError(f"Tempo must be between 20 and 666 BPM, got {bpm}")
    session.send("/tempo/raw", float(bpm))
    return {"action": "set_tempo", "bpm": bpm}


def nudge_tempo(session: Session, direction: int) -> dict:
    """Nudge tempo up (+1) or down (-1)."""
    addr = "/tempo/+" if direction > 0 else "/tempo/-"
    session.send(addr, 1)
    return {"action": "nudge_tempo", "direction": "up" if direction > 0 else "down"}


def tap_tempo(session: Session) -> dict:
    """Tap tempo."""
    session.send("/tempo/tap", 1)
    return {"action": "tap_tempo", "sent": True}


def set_position(session: Session, beats: float) -> dict:
    """Set playback position in beats."""
    if beats < 0:
        raise ValueError(f"Position must be >= 0, got {beats}")
    session.send("/time", float(beats))
    return {"action": "set_position", "beats": beats}


def nudge_position(session: Session, direction: int) -> dict:
    """Nudge position forward (+1) or backward (-1)."""
    addr = "/position/+" if direction > 0 else "/position/-"
    session.send(addr, 1)
    return {"action": "nudge_position", "direction": "forward" if direction > 0 else "backward"}


def status(session: Session) -> dict:
    """Get current transport state from cache."""
    t = session.get_state("transport") or {}
    return {
        "playing": t.get("playing", False),
        "recording": t.get("recording", False),
        "tempo": t.get("tempo", 120.0),
        "position": t.get("position", "1.1.0"),
        "time": t.get("time_str", ""),
        "loop": t.get("loop", False),
        "click": t.get("click", False),
        "overdub": t.get("overdub", False),
        "time_signature": f"{t.get('numerator', 4)}/{t.get('denominator', 4)}",
    }
