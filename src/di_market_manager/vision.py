from __future__ import annotations

import time

import cv2
import numpy as np
import pyautogui
from PIL import Image

from di_market_manager.config import Config

# Cache of loaded template images (name → numpy array)
_template_cache: dict[str, np.ndarray] = {}

# Active config reference for Retina scaling
_active_config: Config | None = None


def load_templates(config: Config) -> None:
    """Pre-load all template images into cache."""
    global _active_config
    _active_config = config
    _template_cache.clear()
    for name, tdef in config.templates.items():
        path = config.project_dir / tdef.file
        if path.exists():
            img = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if img is not None:
                _template_cache[name] = img


def _retina_scale(config: Config | None = None) -> int:
    """Get the Retina scale factor from config."""
    cfg = config or _active_config
    if cfg:
        return cfg.display.retina_scale
    return 1


def take_screenshot() -> np.ndarray:
    """Take a full screenshot and return as BGR numpy array (for OpenCV)."""
    pil_img = pyautogui.screenshot()
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def take_screenshot_pil() -> Image.Image:
    """Take a full screenshot and return as PIL Image."""
    return pyautogui.screenshot()


def find_template(
    name: str,
    confidence: float = 0.85,
    screenshot: np.ndarray | None = None,
    config: Config | None = None,
) -> tuple[int, int] | None:
    """Find template on screen. Returns center (x, y) in logical coordinates, or None."""
    if name not in _template_cache:
        return None

    template = _template_cache[name]

    # Use per-template confidence from config if available
    if config and name in config.templates:
        confidence = config.templates[name].confidence

    if screenshot is None:
        screenshot = take_screenshot()

    result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val >= confidence:
        h, w = template.shape[:2]
        # Physical pixel coordinates
        cx = max_loc[0] + w // 2
        cy = max_loc[1] + h // 2
        # Convert to logical coordinates for pyautogui
        scale = _retina_scale(config)
        return (cx // scale, cy // scale)
    return None


def find_template_score(
    name: str,
    screenshot: np.ndarray | None = None,
    config: Config | None = None,
) -> tuple[float, tuple[int, int] | None]:
    """Find template and return (best_score, center_in_logical_coords_or_None)."""
    if name not in _template_cache:
        return (0.0, None)

    template = _template_cache[name]
    if screenshot is None:
        screenshot = take_screenshot()

    result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    h, w = template.shape[:2]
    cx = max_loc[0] + w // 2
    cy = max_loc[1] + h // 2
    scale = _retina_scale(config)
    return (max_val, (cx // scale, cy // scale))


def find_all_templates(
    name: str,
    confidence: float = 0.85,
    screenshot: np.ndarray | None = None,
    config: Config | None = None,
) -> list[tuple[int, int]]:
    """Find all instances of a template. Returns list of center (x, y) in logical coordinates."""
    if name not in _template_cache:
        return []

    template = _template_cache[name]
    if screenshot is None:
        screenshot = take_screenshot()

    result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    locations = np.where(result >= confidence)

    h, w = template.shape[:2]
    scale = _retina_scale(config)
    points = []
    for pt in zip(*locations[::-1]):
        cx = (pt[0] + w // 2) // scale
        cy = (pt[1] + h // 2) // scale
        points.append((cx, cy))

    # Deduplicate nearby points (within 10 logical pixels)
    if not points:
        return []

    filtered = [points[0]]
    for p in points[1:]:
        if all(abs(p[0] - f[0]) > 10 or abs(p[1] - f[1]) > 10 for f in filtered):
            filtered.append(p)

    return filtered


def wait_for_template(
    name: str,
    timeout: float = 20,
    poll_interval: float | None = None,
    confidence: float = 0.85,
    config: Config | None = None,
) -> tuple[int, int]:
    """Poll until template appears. Raises TimeoutError.

    Uses config.timing.poll_interval if poll_interval is not specified.
    """
    if poll_interval is None:
        cfg = config or _active_config
        poll_interval = cfg.timing.poll_interval if cfg else 0.75

    deadline = time.time() + timeout
    while time.time() < deadline:
        pos = find_template(name, confidence=confidence, config=config)
        if pos is not None:
            return pos
        time.sleep(poll_interval)
    raise TimeoutError(f"Template '{name}' not found within {timeout}s")


def click_template(
    name: str,
    timeout: float = 20,
    confidence: float = 0.85,
    config: Config | None = None,
) -> tuple[int, int]:
    """Find template, click its center. Returns logical position clicked."""
    pos = wait_for_template(name, timeout=timeout, confidence=confidence, config=config)
    pyautogui.click(pos[0], pos[1])
    return pos


