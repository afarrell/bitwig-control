"""Clip launcher control for Bitwig Studio.

Launch, stop, record, and inspect clips in the launcher grid.
Clips are addressed by (track, slot) within the current bank window (1-8 each).
"""

from cli_anything.bitwig.core.session import Session


def _validate_clip_addr(track: int, slot: int):
    if not 1 <= track <= 8:
        raise ValueError(f"Track must be 1-8, got {track}")
    if not 1 <= slot <= 8:
        raise ValueError(f"Slot must be 1-8, got {slot}")


def launch(session: Session, track: int, slot: int) -> dict:
    """Launch a clip."""
    _validate_clip_addr(track, slot)
    session.send(f"/track/{track}/clip/{slot}/launch", 1)
    return {"action": "launch_clip", "track": track, "slot": slot}


def stop(session: Session, track: int) -> dict:
    """Stop clips on a track."""
    if not 1 <= track <= 8:
        raise ValueError(f"Track must be 1-8, got {track}")
    session.send(f"/track/{track}/clip/stop", 1)
    return {"action": "stop_clips", "track": track}


def stop_all(session: Session) -> dict:
    """Stop all clips."""
    for i in range(1, 9):
        session.send(f"/track/{i}/clip/stop", 1)
    return {"action": "stop_all_clips"}


def record(session: Session, track: int, slot: int) -> dict:
    """Record into a clip slot."""
    _validate_clip_addr(track, slot)
    session.send(f"/track/{track}/clip/{slot}/record", 1)
    return {"action": "record_clip", "track": track, "slot": slot}


def list_clips(session: Session, track: int) -> dict:
    """List clips for a track in the current bank."""
    if not 1 <= track <= 8:
        raise ValueError(f"Track must be 1-8, got {track}")

    track_data = (session.get_state("tracks") or {}).get(track, {})
    clips_data = track_data.get("clips", {})
    clips = []
    for i in range(1, 9):
        c = clips_data.get(i, {})
        clips.append({
            "slot": i,
            "name": c.get("name", ""),
            "has_content": c.get("has_content", False),
            "playing": c.get("playing", False),
            "recording": c.get("recording", False),
            "queued": c.get("queued", False),
        })
    return {
        "track": track,
        "track_name": track_data.get("name", ""),
        "clips": clips,
    }


def grid(session: Session) -> dict:
    """Get the full clip launcher grid (8x8) from cache."""
    tracks_data = session.get_state("tracks") or {}
    grid_data = []
    for t in range(1, 9):
        td = tracks_data.get(t, {})
        if not td.get("exists", False) and not td.get("name"):
            continue
        clips = []
        for c in range(1, 9):
            cd = td.get("clips", {}).get(c, {})
            clips.append({
                "slot": c,
                "name": cd.get("name", ""),
                "has_content": cd.get("has_content", False),
                "playing": cd.get("playing", False),
                "recording": cd.get("recording", False),
                "queued": cd.get("queued", False),
            })
        grid_data.append({
            "track": t,
            "track_name": td.get("name", ""),
            "clips": clips,
        })
    return {"grid": grid_data}
