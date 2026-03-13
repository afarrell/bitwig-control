"""Track management for Bitwig Studio.

Volume, pan, mute, solo, arm, sends, bank navigation, and track info.
DrivenByMoss uses 1-indexed track numbers within an 8-track bank window.
"""

from cli_anything.bitwig.core.session import Session


def _validate_track(num: int):
    """Validate track number is in bank range (1-8)."""
    if not 1 <= num <= 8:
        raise ValueError(
            f"Track number must be 1-8 (within current bank), got {num}. "
            f"Use 'track bank +' to scroll to more tracks."
        )


def _validate_send(num: int):
    if not 1 <= num <= 8:
        raise ValueError(f"Send number must be 1-8, got {num}")


def list_tracks(session: Session) -> dict:
    """List all tracks in the current bank."""
    tracks_data = session.get_state("tracks") or {}
    tracks = []
    for i in range(1, 9):
        t = tracks_data.get(i, {})
        if t.get("exists", False) or t.get("name"):
            tracks.append({
                "bank_index": i,
                "absolute_index": session._bank_offset + i,
                "name": t.get("name", ""),
                "type": t.get("type", ""),
                "volume": round(t.get("volume", 0.0), 3),
                "volume_str": t.get("volume_str", ""),
                "pan": round(t.get("pan", 0.5), 3),
                "pan_str": t.get("pan_str", ""),
                "mute": t.get("mute", False),
                "solo": t.get("solo", False),
                "recarm": t.get("recarm", False),
                "selected": t.get("selected", False),
            })
    return {
        "bank_offset": session._bank_offset,
        "tracks": tracks,
        "count": len(tracks),
    }


def get_track(session: Session, num: int) -> dict:
    """Get info for a specific track in the current bank."""
    _validate_track(num)
    t = (session.get_state("tracks") or {}).get(num, {})
    return {
        "bank_index": num,
        "absolute_index": session._bank_offset + num,
        "name": t.get("name", ""),
        "type": t.get("type", ""),
        "volume": round(t.get("volume", 0.0), 3),
        "volume_str": t.get("volume_str", ""),
        "pan": round(t.get("pan", 0.5), 3),
        "pan_str": t.get("pan_str", ""),
        "mute": t.get("mute", False),
        "solo": t.get("solo", False),
        "recarm": t.get("recarm", False),
        "selected": t.get("selected", False),
        "monitor": t.get("monitor", ""),
        "vu": round(t.get("vu", 0.0), 3),
        "sends": t.get("sends", {}),
        "exists": t.get("exists", False),
    }


def select(session: Session, num: int) -> dict:
    """Select a track."""
    _validate_track(num)
    session.send(f"/track/{num}/select", 1)
    return {"action": "select", "track": num}


def set_volume(session: Session, num: int, value: float) -> dict:
    """Set track volume (0.0 to 1.0)."""
    _validate_track(num)
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"Volume must be 0.0-1.0, got {value}")
    session.send(f"/track/{num}/volume", float(value))
    return {"action": "set_volume", "track": num, "volume": value}


def set_pan(session: Session, num: int, value: float) -> dict:
    """Set track pan (0.0=left, 0.5=center, 1.0=right)."""
    _validate_track(num)
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"Pan must be 0.0-1.0 (0.5=center), got {value}")
    session.send(f"/track/{num}/pan", float(value))
    return {"action": "set_pan", "track": num, "pan": value}


def toggle_mute(session: Session, num: int) -> dict:
    """Toggle track mute."""
    _validate_track(num)
    session.send(f"/track/{num}/mute", 1)
    return {"action": "toggle_mute", "track": num}


def set_mute(session: Session, num: int, state: bool) -> dict:
    """Set track mute on or off."""
    _validate_track(num)
    session.send(f"/track/{num}/mute", 1 if state else 0)
    return {"action": "set_mute", "track": num, "mute": state}


def toggle_solo(session: Session, num: int) -> dict:
    """Toggle track solo."""
    _validate_track(num)
    session.send(f"/track/{num}/solo", 1)
    return {"action": "toggle_solo", "track": num}


def set_solo(session: Session, num: int, state: bool) -> dict:
    """Set track solo on or off."""
    _validate_track(num)
    session.send(f"/track/{num}/solo", 1 if state else 0)
    return {"action": "set_solo", "track": num, "solo": state}


def toggle_arm(session: Session, num: int) -> dict:
    """Toggle track record arm."""
    _validate_track(num)
    session.send(f"/track/{num}/recarm", 1)
    return {"action": "toggle_arm", "track": num}


def set_arm(session: Session, num: int, state: bool) -> dict:
    """Set track record arm on or off."""
    _validate_track(num)
    session.send(f"/track/{num}/recarm", 1 if state else 0)
    return {"action": "set_arm", "track": num, "recarm": state}


def set_send(session: Session, track_num: int, send_num: int, value: float) -> dict:
    """Set send level for a track."""
    _validate_track(track_num)
    _validate_send(send_num)
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"Send value must be 0.0-1.0, got {value}")
    session.send(f"/track/{track_num}/send/{send_num}/volume", float(value))
    return {"action": "set_send", "track": track_num, "send": send_num, "volume": value}


def add_audio_track(session: Session) -> dict:
    """Add a new audio track."""
    session.send("/track/add/audio", 1)
    return {"action": "add_track", "type": "audio"}


def add_instrument_track(session: Session) -> dict:
    """Add a new instrument track."""
    session.send("/track/add/instrument", 1)
    return {"action": "add_track", "type": "instrument"}


def add_effect_track(session: Session) -> dict:
    """Add a new effect track."""
    session.send("/track/add/effect", 1)
    return {"action": "add_track", "type": "effect"}


def scroll_bank(session: Session, direction: int) -> dict:
    """Scroll the track bank forward (+1) or backward (-1)."""
    return session.scroll_tracks(direction)
