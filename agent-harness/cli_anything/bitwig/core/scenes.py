"""Scene management for Bitwig Studio.

Launch scenes and navigate the scene bank.
"""

from cli_anything.bitwig.core.session import Session


def _validate_scene(num: int):
    if not 1 <= num <= 8:
        raise ValueError(f"Scene must be 1-8 (within current bank), got {num}")


def launch(session: Session, num: int) -> dict:
    """Launch a scene."""
    _validate_scene(num)
    session.send(f"/scene/{num}/launch", 1)
    return {"action": "launch_scene", "scene": num}


def list_scenes(session: Session) -> dict:
    """List scenes in the current bank."""
    scenes_data = session.get_state("scenes") or {}
    scenes = []
    for i in range(1, 9):
        s = scenes_data.get(i, {})
        if s.get("exists", False) or s.get("name"):
            scenes.append({
                "bank_index": i,
                "absolute_index": session._scene_bank_offset + i,
                "name": s.get("name", ""),
                "exists": s.get("exists", False),
            })
    return {
        "bank_offset": session._scene_bank_offset,
        "scenes": scenes,
        "count": len(scenes),
    }


def scroll_bank(session: Session, direction: int) -> dict:
    """Scroll the scene bank forward (+1) or backward (-1)."""
    return session.scroll_scenes(direction)
