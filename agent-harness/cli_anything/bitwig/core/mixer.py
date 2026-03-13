"""Mixer operations for Bitwig Studio.

High-level mixer view combining track and master state.
"""

from cli_anything.bitwig.core.session import Session


def status(session: Session) -> dict:
    """Get full mixer status — all tracks + master."""
    tracks_data = session.get_state("tracks") or {}
    master_data = session.get_state("master") or {}

    tracks = []
    for i in range(1, 9):
        t = tracks_data.get(i, {})
        if t.get("exists", False) or t.get("name"):
            tracks.append({
                "index": i,
                "name": t.get("name", ""),
                "volume": round(t.get("volume", 0.0), 3),
                "volume_str": t.get("volume_str", ""),
                "pan": round(t.get("pan", 0.5), 3),
                "pan_str": t.get("pan_str", ""),
                "mute": t.get("mute", False),
                "solo": t.get("solo", False),
                "recarm": t.get("recarm", False),
                "vu": round(t.get("vu", 0.0), 3),
            })

    return {
        "bank_offset": session._bank_offset,
        "tracks": tracks,
        "master": {
            "volume": round(master_data.get("volume", 1.0), 3),
            "volume_str": master_data.get("volume_str", ""),
            "pan": round(master_data.get("pan", 0.5), 3),
            "mute": master_data.get("mute", False),
            "vu": round(master_data.get("vu", 0.0), 3),
        },
    }


def set_master_volume(session: Session, value: float) -> dict:
    """Set master track volume (0.0 to 1.0)."""
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"Volume must be 0.0-1.0, got {value}")
    session.send("/master/volume", float(value))
    return {"action": "set_master_volume", "volume": value}


def set_master_pan(session: Session, value: float) -> dict:
    """Set master track pan (0.0=L, 0.5=C, 1.0=R)."""
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"Pan must be 0.0-1.0, got {value}")
    session.send("/master/pan", float(value))
    return {"action": "set_master_pan", "pan": value}


def toggle_master_mute(session: Session) -> dict:
    """Toggle master track mute."""
    session.send("/master/mute", 1)
    return {"action": "toggle_master_mute"}
