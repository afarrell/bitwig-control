"""Device/plugin control for Bitwig Studio.

Navigate devices on the selected track, control parameters, toggle bypass.
Parameters are shown in pages of 8 via DrivenByMoss.
"""

from cli_anything.bitwig.core.session import Session


def _validate_param(num: int):
    if not 1 <= num <= 8:
        raise ValueError(f"Parameter number must be 1-8, got {num}")


def status(session: Session) -> dict:
    """Get current device info from cache."""
    d = session.get_state("device") or {}
    params = d.get("params", {})
    param_list = []
    for i in range(1, 9):
        p = params.get(i, {})
        if p.get("exists", True) and p.get("name"):
            param_list.append({
                "index": i,
                "name": p.get("name", ""),
                "value": round(p.get("value", 0.0), 4),
                "value_str": p.get("value_str", ""),
            })
    return {
        "name": d.get("name", "(none)"),
        "bypass": d.get("bypass", False),
        "page": d.get("page_name", ""),
        "parameters": param_list,
    }


def set_param(session: Session, num: int, value: float) -> dict:
    """Set a device parameter value (0.0 to 1.0)."""
    _validate_param(num)
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"Parameter value must be 0.0-1.0, got {value}")
    session.send(f"/device/param/{num}/value", float(value))
    return {"action": "set_param", "param": num, "value": value}


def toggle_bypass(session: Session) -> dict:
    """Toggle device bypass."""
    session.send("/device/bypass", 1)
    return {"action": "toggle_bypass"}


def toggle_window(session: Session) -> dict:
    """Toggle device plugin window visibility."""
    session.send("/device/window", 1)
    return {"action": "toggle_window"}


def navigate(session: Session, direction: int) -> dict:
    """Navigate to next (+1) or previous (-1) device."""
    addr = "/device/+" if direction > 0 else "/device/-"
    session.send(addr, 1)
    return {"action": "navigate_device", "direction": "next" if direction > 0 else "prev"}


def navigate_page(session: Session, direction: int) -> dict:
    """Navigate to next (+1) or previous (-1) parameter page."""
    addr = "/device/page/+" if direction > 0 else "/device/page/-"
    session.send(addr, 1)
    return {"action": "navigate_page", "direction": "next" if direction > 0 else "prev"}
