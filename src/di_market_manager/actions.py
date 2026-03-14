from __future__ import annotations

import subprocess
import time
import urllib.request
import urllib.error
from datetime import datetime

import cv2
import numpy as np
import pyautogui

from di_market_manager.config import Config
from di_market_manager.session import Session
from di_market_manager.vision import (
    find_template_score,
    take_screenshot_pil,
    wait_for_template,
)


# ---------------------------------------------------------------------------
# Single Operations
# ---------------------------------------------------------------------------


def click(s: Session, target: str) -> dict:
    """Find template on screen and click its center."""
    score, pos = find_template_score(target, config=s.config)
    tdef = s.config.templates[target]
    if pos is None or score < tdef.confidence:
        result = {"action": "click", "target": target, "success": False, "score": round(score, 3)}
        s.record(**result)
        return result
    pyautogui.click(pos[0], pos[1])
    result = {"action": "click", "target": target, "success": True, "position": list(pos)}
    s.record(**result)
    return result


def click_coords(s: Session, x: int, y: int) -> dict:
    """Click raw coordinates."""
    pyautogui.click(x, y)
    result = {"action": "click", "target": f"{x},{y}", "success": True, "position": [x, y]}
    s.record(**result)
    return result


def check(s: Session, template: str) -> dict:
    """Check if a template is visible on screen."""
    score, pos = find_template_score(template, config=s.config)
    tdef = s.config.templates[template]
    visible = score >= tdef.confidence
    result: dict = {"action": "check", "target": template, "visible": visible, "score": round(score, 3)}
    if visible and pos:
        result["position"] = list(pos)
    s.record(**result)
    return result


def wait_seconds(s: Session, seconds: float) -> dict:
    """Sleep for N seconds."""
    time.sleep(seconds)
    result = {"action": "wait", "seconds": seconds}
    s.record(**result)
    return result


def wait_for(s: Session, template: str, timeout: float = 20) -> dict:
    """Block until template appears on screen."""
    start = time.time()
    try:
        pos = wait_for_template(template, timeout=timeout, config=s.config)
        elapsed = round(time.time() - start, 1)
        result = {
            "action": "wait-for",
            "target": template,
            "found": True,
            "position": list(pos),
            "elapsed": elapsed,
        }
    except TimeoutError:
        elapsed = round(time.time() - start, 1)
        result = {"action": "wait-for", "target": template, "found": False, "elapsed": elapsed}
    s.record(**result)
    return result


def press(s: Session, key: str) -> dict:
    """Press a keyboard key."""
    pyautogui.press(key)
    result = {"action": "press", "key": key, "success": True}
    s.record(**result)
    return result


def snapshot(s: Session, name: str | None = None) -> dict:
    """Take screenshot and score all templates."""
    pil_img = take_screenshot_pil()
    screenshot_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    scores = {}
    visible = []
    for tname, tdef in s.config.templates.items():
        score, _ = find_template_score(tname, screenshot=screenshot_bgr, config=s.config)
        scores[tname] = round(score, 3)
        if score >= tdef.confidence:
            visible.append(tname)

    snapshots_dir = s.config.project_dir / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{ts}.png" if name else f"{ts}.png"
    path = snapshots_dir / filename
    pil_img.save(str(path))

    result = {
        "action": "snapshot",
        "path": str(path),
        "visible": visible,
        "scores": scores,
    }
    s.record(**result)
    return result


def is_running(s: Session) -> dict:
    """Check if BlueStacks process is running."""
    running = _is_process_running(s.config.process_name)
    result = {"action": "status", "process": s.config.process_name, "running": running}
    s.record(**result)
    return result


def launch_app(s: Session) -> dict:
    """Open BlueStacks."""
    subprocess.Popen(["open", "-a", s.config.window_title])
    result = {"action": "launch", "app": s.config.window_title, "success": True}
    s.record(**result)
    return result


def kill_process(s: Session) -> dict:
    """Force kill BlueStacks."""
    _kill_process(s.config)
    result = {"action": "kill", "process": s.config.process_name, "success": True}
    s.record(**result)
    return result


# ---------------------------------------------------------------------------
# Composite Operations
# ---------------------------------------------------------------------------


def click_verify(s: Session, target: str, verify_template: str, delay: float | None = None) -> dict:
    """Click target, wait, then check verify_template."""
    click_result = click(s, target)
    if not click_result["success"]:
        return {
            "action": "click-verify",
            "target": target,
            "success": False,
            "click": click_result,
        }

    wait_time = delay if delay is not None else 2.0
    time.sleep(wait_time)

    verify_result = check(s, verify_template)
    result = {
        "action": "click-verify",
        "target": target,
        "position": click_result.get("position"),
        "verify": {
            "target": verify_template,
            "visible": verify_result["visible"],
            "score": verify_result["score"],
        },
        "success": verify_result["visible"],
    }
    s.record(**result)
    return result


# Numpad constants (ported from game.py)
_NUMPAD_KEYS: dict[str, tuple[int, int]] = {
    "1": (0, 0), "2": (0, 1), "3": (0, 2),
    "4": (1, 0), "5": (1, 1), "6": (1, 2),
    "7": (2, 0), "8": (2, 1), "9": (2, 2),
    "bksp": (3, 0), "0": (3, 1), "confirm": (3, 2),
}

_KEY_DELAY = 1.0  # seconds between numpad taps
_TITLE_OFFSET_Y = 40  # logical pixels below title center to hit input field

_NUMPAD_FIELDS = {
    "price": ("price_limit_title", "numpad_price"),
    "purchase": ("purchase_limit_title", "numpad_purchase"),
}


def _numpad_tap(key: str, region_name: str, config: Config) -> None:
    """Tap a single key on the numpad."""
    region = config.regions[region_name]
    scale = config.display.retina_scale
    col_w = region.w / 3
    row_h = region.h / 4
    row, col = _NUMPAD_KEYS[key]
    cx = (region.x + int(col_w * col + col_w / 2)) // scale
    cy = (region.y + int(row_h * row + row_h / 2)) // scale
    pyautogui.click(cx, cy)
    time.sleep(_KEY_DELAY)


def numpad_enter(s: Session, field: str, value: int) -> dict:
    """Open numpad, clear, type digits, confirm.

    field: "price" or "purchase"
    """
    template, region = _NUMPAD_FIELDS[field]

    # Find and click the input field (below the title)
    score, pos = find_template_score(template, config=s.config)
    if pos is None:
        result = {
            "action": "numpad",
            "field": field,
            "value": value,
            "success": False,
            "error": f"Cannot find {template}",
        }
        s.record(**result)
        return result

    pyautogui.click(pos[0], pos[1] + _TITLE_OFFSET_Y)
    time.sleep(1.5)

    # Clear existing value (4 backspaces)
    for _ in range(4):
        _numpad_tap("bksp", region, s.config)

    # Type digits
    for ch in str(value):
        _numpad_tap(ch, region, s.config)

    # Confirm
    _numpad_tap("confirm", region, s.config)
    time.sleep(1.0)

    result = {"action": "numpad", "field": field, "value": value, "success": True}
    s.record(**result)
    return result


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1482416854621487147/1h-xXAcPVduX_RXxluQ4J5VZmBgcOLDIBmWHA-Jr9iXwTvlcVRNTYCY8rIORoOJ_PqXa"


def notify_discord(s: Session, payload_json: str) -> dict:
    """POST a JSON payload to the Discord webhook."""
    try:
        req = urllib.request.Request(
            DISCORD_WEBHOOK_URL,
            data=payload_json.encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "dimm/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
    except urllib.error.HTTPError as exc:
        # Discord returns 204 No Content on success; urllib treats non-200 as error
        if 200 <= exc.code < 300:
            status = exc.code
        else:
            result = {"action": "notify", "success": False, "error": str(exc), "status": exc.code}
            s.record(**result)
            return result
    except (urllib.error.URLError, OSError) as exc:
        result = {"action": "notify", "success": False, "error": str(exc)}
        s.record(**result)
        return result

    result = {"action": "notify", "success": True, "status": status}
    s.record(**result)
    return result


# ---------------------------------------------------------------------------
# Internal helpers (ported from game.py)
# ---------------------------------------------------------------------------


def _is_process_running(process_name: str) -> bool:
    try:
        result = subprocess.run(["pgrep", "-f", process_name], capture_output=True, timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _kill_process(config: Config) -> None:
    try:
        subprocess.run(["pkill", "-f", config.process_name], capture_output=True, timeout=10)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    try:
        subprocess.run(
            ["osascript", "-e", f'tell application "{config.window_title}" to quit'],
            capture_output=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
