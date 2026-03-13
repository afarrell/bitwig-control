"""Browser control for Bitwig Studio.

Navigate the device/preset browser, select and commit results.
"""

from cli_anything.bitwig.core.session import Session


def open_presets(session: Session) -> dict:
    """Open the preset browser."""
    session.send("/browser/preset", 1)
    return {"action": "open_preset_browser"}


def open_devices(session: Session) -> dict:
    """Open the device browser."""
    session.send("/browser/device", 1)
    return {"action": "open_device_browser"}


def commit(session: Session) -> dict:
    """Confirm the current browser selection."""
    session.send("/browser/commit", 1)
    return {"action": "browser_commit"}


def cancel(session: Session) -> dict:
    """Cancel and close the browser."""
    session.send("/browser/cancel", 1)
    return {"action": "browser_cancel"}


def navigate_result(session: Session, direction: int) -> dict:
    """Navigate browser results: next (+1) or previous (-1)."""
    addr = "/browser/result/+" if direction > 0 else "/browser/result/-"
    session.send(addr, 1)
    return {"action": "navigate_result", "direction": "next" if direction > 0 else "prev"}


def navigate_filter(session: Session, column: int, direction: int) -> dict:
    """Navigate a browser filter column (1-6)."""
    if not 1 <= column <= 6:
        raise ValueError(f"Filter column must be 1-6, got {column}")
    addr = f"/browser/filter/{column}/+" if direction > 0 else f"/browser/filter/{column}/-"
    session.send(addr, 1)
    return {
        "action": "navigate_filter",
        "column": column,
        "direction": "next" if direction > 0 else "prev",
    }


def status(session: Session) -> dict:
    """Get browser state from cache."""
    b = session.get_state("browser") or {}
    return {
        "active": b.get("active", False),
    }
