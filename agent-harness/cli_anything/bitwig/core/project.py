"""Project-level operations for Bitwig Studio.

Save, undo/redo, layout switching, and global actions.
"""

from cli_anything.bitwig.core.session import Session


def save(session: Session) -> dict:
    """Save the current project."""
    session.send("/project/save", 1)
    return {"action": "save_project"}


def undo(session: Session) -> dict:
    """Undo the last action."""
    session.send("/undo", 1)
    return {"action": "undo"}


def redo(session: Session) -> dict:
    """Redo the last undone action."""
    session.send("/redo", 1)
    return {"action": "redo"}


def set_layout(session: Session, layout: str) -> dict:
    """Switch layout: 'arrange', 'mix', or 'edit'."""
    valid = ("arrange", "mix", "edit")
    if layout not in valid:
        raise ValueError(f"Layout must be one of {valid}, got '{layout}'")
    session.send(f"/layout/{layout}", 1)
    return {"action": "set_layout", "layout": layout}


def status(session: Session) -> dict:
    """Get project-level info from cache."""
    p = session.get_state("project") or {}
    return {
        "name": p.get("name", ""),
        "engine": p.get("engine", True),
        "layout": session.get_state("layout") or "arrange",
    }


def toggle_engine(session: Session) -> dict:
    """Toggle the audio engine on/off."""
    session.send("/project/engine", 1)
    return {"action": "toggle_engine"}
