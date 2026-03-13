from __future__ import annotations

import random
import subprocess
import time

import pyautogui

from di_market_manager.config import Config
from di_market_manager.vision import click_template, find_template, wait_for_template


def _random_delay(delay_range: tuple[float, float]) -> None:
    time.sleep(random.uniform(*delay_range))


def _do_and_wait(
    action: callable,
    expected_template: str,
    step_name: str,
    config: Config,
) -> tuple[int, int]:
    """Perform an action, then wait for the expected UI state to appear."""
    action()
    _random_delay(config.timing.click_delay)
    pos = wait_for_template(
        expected_template,
        timeout=config.get_timeout(step_name),
        config=config,
    )
    _random_delay(config.timing.page_load_wait)
    return pos


# ---------------------------------------------------------------------------
# Launch
# ---------------------------------------------------------------------------

def is_process_running(process_name: str) -> bool:
    """Check if a process is running on macOS."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", process_name],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def ensure_bluestacks_running(config: Config) -> None:
    """Ensure BlueStacks Air is running. Launch it if not."""
    if is_process_running(config.process_name):
        return

    subprocess.Popen(["open", "-a", config.window_title])
    wait_for_template(
        "bluestacks_home",
        timeout=config.get_timeout("launch_bluestacks"),
        config=config,
    )
    _random_delay(config.timing.page_load_wait)


def launch_game(config: Config) -> None:
    """Full launch sequence: BlueStacks → DI app → in-game."""
    ensure_bluestacks_running(config)

    # Already in game?
    if find_template("in_game_hud", config=config) is not None:
        return

    # Click the DI app icon on BlueStacks home
    click_template(
        "di_app_icon",
        timeout=config.get_timeout("wait_for_home"),
        config=config,
    )
    _random_delay(config.timing.click_delay)

    # Wait for game to fully load — this is the slow step
    wait_for_template(
        "in_game_hud",
        timeout=config.get_timeout("launch_di_app"),
        config=config,
    )
    _random_delay(config.timing.page_load_wait)


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

def navigate_to_market(config: Config) -> None:
    """From in-game, open the marketplace and navigate to the gem tab."""
    click_template(
        "market_button",
        timeout=config.get_timeout("navigate_to_market"),
        config=config,
    )
    _random_delay(config.timing.click_delay)

    wait_for_template(
        "market_header",
        timeout=config.get_timeout("navigate_to_market"),
        config=config,
    )
    _random_delay(config.timing.click_delay)

    click_template(
        "gem_tab",
        timeout=config.get_timeout("navigate_to_market"),
        config=config,
    )
    _random_delay(config.timing.page_load_wait)


def _select_all_text(config: Config, pos: tuple[int, int] | None) -> None:
    """Select all text in the current input field using the configured method."""
    method = config.select_all_method
    if method == "triple_click" and pos:
        pyautogui.click(pos[0], pos[1], clicks=3, interval=0.1)
    elif method == "command_a":
        pyautogui.hotkey("command", "a")
    elif method == "long_press" and pos:
        pyautogui.mouseDown(pos[0], pos[1])
        time.sleep(1.0)
        pyautogui.mouseUp()
        _random_delay((0.3, 0.5))
        # Attempt to click a "Select All" popup if one appears
        try:
            click_template("select_all_popup", timeout=3, config=config)
        except TimeoutError:
            pass
    else:
        # Fallback: triple-click at current position
        if pos:
            pyautogui.click(pos[0], pos[1], clicks=3, interval=0.1)
    _random_delay((0.2, 0.4))


def search_gem(config: Config, gem_name: str) -> None:
    """Search for a specific gem in the marketplace search bar."""
    pos = click_template(
        "market_search_bar",
        timeout=config.get_timeout("search_gem"),
        config=config,
    )
    _random_delay(config.timing.click_delay)

    # Select any existing text, then type over it
    _select_all_text(config, pos)
    pyautogui.typewrite(gem_name, interval=0.05)
    _random_delay(config.timing.click_delay)

    pyautogui.press("enter")
    _random_delay(config.timing.page_load_wait)


# ---------------------------------------------------------------------------
# Close / Kill
# ---------------------------------------------------------------------------

def press_back_until_clear(config: Config, max_presses: int = 5) -> None:
    """Press Back repeatedly to close any open menus/dialogs.

    BlueStacks maps Escape → Android Back by default.
    """
    for _ in range(max_presses):
        pyautogui.press("escape")
        time.sleep(0.5)


def close_game(config: Config) -> None:
    """Close DI and kill BlueStacks so next cycle starts clean."""
    press_back_until_clear(config)
    _random_delay(config.timing.click_delay)
    kill_game_process(config)
    _random_delay(config.timing.page_load_wait)


def kill_game_process(config: Config) -> None:
    """Force-kill BlueStacks via macOS process management."""
    try:
        subprocess.run(
            ["pkill", "-f", config.process_name],
            capture_output=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    # Graceful quit via osascript as fallback
    try:
        subprocess.run(
            ["osascript", "-e", f'tell application "{config.window_title}" to quit'],
            capture_output=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
