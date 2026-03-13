from __future__ import annotations

import random
import subprocess
import time

import pyautogui

from di_market_manager.config import Config
from di_market_manager.vision import click_template, wait_for_template


def _random_delay(delay_range: tuple[float, float]) -> None:
    time.sleep(random.uniform(*delay_range))


def launch_game(config: Config) -> None:
    """Battle.net is already running (auto-starts on boot). Click Play and wait for HUD."""
    click_template("battlenet_play_button", timeout=30, config=config)
    _random_delay(config.timing.page_load_wait)
    # Game takes a long time to load
    wait_for_template("in_game_hud", timeout=180, config=config)
    _random_delay(config.timing.page_load_wait)


def navigate_to_market(config: Config) -> None:
    """From in-game, open the marketplace and navigate to the gem tab."""
    click_template("market_button", timeout=10, config=config)
    _random_delay(config.timing.page_load_wait)
    wait_for_template("market_header", timeout=15, config=config)
    _random_delay(config.timing.click_delay)

    click_template("gem_tab", timeout=10, config=config)
    _random_delay(config.timing.page_load_wait)


def search_gem(config: Config, gem_name: str) -> None:
    """Search for a specific gem in the marketplace search bar."""
    click_template("market_search_bar", timeout=10, config=config)
    _random_delay(config.timing.click_delay)

    # Clear existing text and type gem name
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyautogui.typewrite(gem_name, interval=0.05)
    _random_delay(config.timing.click_delay)

    pyautogui.press("enter")
    _random_delay(config.timing.page_load_wait)


def press_esc_until_clear(max_presses: int = 5) -> None:
    """Press ESC repeatedly to close any open menus/dialogs."""
    for _ in range(max_presses):
        pyautogui.press("escape")
        time.sleep(0.3)


def close_game(config: Config) -> None:
    """Logout and kill DI process so Battle.net returns to Play screen."""
    press_esc_until_clear()
    time.sleep(1)
    kill_game_process(config)
    # Wait for Battle.net to show Play button again
    time.sleep(5)


def kill_game_process(config: Config) -> None:
    """Force-kill the game process."""
    try:
        subprocess.run(
            ["pkill", "-f", config.process_name],
            capture_output=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    # Also try taskkill on Windows/Wine
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", config.process_name],
            capture_output=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass


def is_game_running(config: Config) -> bool:
    """Check if the game process is currently running."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", config.process_name],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
