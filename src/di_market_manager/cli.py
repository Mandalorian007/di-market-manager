from __future__ import annotations

import json
import sys

import click

from di_market_manager.config import Config, Region, TemplateDef, load_config, save_config


def _make_session():
    """Load config and create a Session. Deferred import to keep CLI startup fast."""
    from di_market_manager.session import Session

    return Session(load_config())


def _output(data: dict, success_key: str | None = None) -> None:
    """Print JSON to stdout and exit with appropriate code."""
    click.echo(json.dumps(data))
    if success_key is not None and not data.get(success_key, True):
        sys.exit(1)


def _validate_template(config: Config, name: str) -> None:
    """Validate that a template name exists in config."""
    if name not in config.templates:
        available = ", ".join(sorted(config.templates.keys()))
        click.echo(
            json.dumps({"error": f"'{name}' is not a known template. Available: {available}"}),
            err=True,
        )
        sys.exit(1)


def _validate_region(config: Config, name: str) -> None:
    """Validate that a region name exists in config."""
    if name not in config.regions:
        available = ", ".join(sorted(config.regions.keys()))
        click.echo(
            json.dumps({"error": f"'{name}' is not a known region. Available: {available}"}),
            err=True,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------


@click.group()
def cli() -> None:
    """dimm — CLI primitives for Diablo Immortal marketplace automation."""
    pass


# ---------------------------------------------------------------------------
# Single operations
# ---------------------------------------------------------------------------


@cli.command("click")
@click.argument("target", required=False)
@click.option("--xy", default=None, help="Raw coordinates as x,y")
def cmd_click(target: str | None, xy: str | None) -> None:
    """Click a template or raw coordinates."""
    from di_market_manager import actions

    s = _make_session()

    if xy:
        parts = xy.split(",")
        if len(parts) != 2:
            click.echo(json.dumps({"error": "Invalid --xy format. Use: --xy x,y"}), err=True)
            sys.exit(1)
        x, y = int(parts[0]), int(parts[1])
        _output(actions.click_coords(s, x, y))
    elif target and target in s.config.locations:
        loc = s.config.locations[target]
        _output(actions.click_coords(s, loc.x, loc.y))
    elif target:
        _validate_template(s.config, target)
        _output(actions.click(s, target), success_key="success")
    else:
        click.echo(json.dumps({"error": "Provide a template name, location name, or --xy x,y"}), err=True)
        sys.exit(1)


@cli.command("check")
@click.argument("template")
def cmd_check(template: str) -> None:
    """Check if a template is visible on screen."""
    from di_market_manager import actions

    s = _make_session()
    _validate_template(s.config, template)
    _output(actions.check(s, template))


@cli.command("wait")
@click.argument("seconds", type=float)
def cmd_wait(seconds: float) -> None:
    """Sleep for N seconds."""
    from di_market_manager import actions

    s = _make_session()
    _output(actions.wait_seconds(s, seconds))


@cli.command("wait-for")
@click.argument("template")
@click.option("--timeout", default=20.0, help="Max seconds to wait")
def cmd_wait_for(template: str, timeout: float) -> None:
    """Block until a template appears on screen."""
    from di_market_manager import actions

    s = _make_session()
    _validate_template(s.config, template)
    result = actions.wait_for(s, template, timeout=timeout)
    _output(result, success_key="found")


@cli.command("press")
@click.argument("key")
def cmd_press(key: str) -> None:
    """Press a keyboard key."""
    from di_market_manager import actions

    s = _make_session()
    _output(actions.press(s, key))


@cli.command("snapshot")
@click.option("--name", default=None, help="Optional snapshot name")
def cmd_snapshot(name: str | None) -> None:
    """Take a screenshot and score all templates."""
    from di_market_manager import actions

    s = _make_session()
    _output(actions.snapshot(s, name=name))


@cli.command("status")
def cmd_status() -> None:
    """Check if BlueStacks is running."""
    from di_market_manager import actions

    s = _make_session()
    _output(actions.is_running(s))


@cli.command("launch")
def cmd_launch() -> None:
    """Open BlueStacks."""
    from di_market_manager import actions

    s = _make_session()
    _output(actions.launch_app(s))


@cli.command("kill")
def cmd_kill() -> None:
    """Force kill BlueStacks."""
    from di_market_manager import actions

    s = _make_session()
    _output(actions.kill_process(s))


# ---------------------------------------------------------------------------
# Composite operations
# ---------------------------------------------------------------------------


@cli.command("click-verify")
@click.argument("target")
@click.argument("verify_template")
@click.option("--delay", default=None, type=float, help="Seconds to wait before verifying")
def cmd_click_verify(target: str, verify_template: str, delay: float | None) -> None:
    """Click a target, then verify another template appeared."""
    from di_market_manager import actions

    s = _make_session()
    _validate_template(s.config, target)
    _validate_template(s.config, verify_template)
    _output(actions.click_verify(s, target, verify_template, delay=delay), success_key="success")


@cli.command("numpad")
@click.argument("field", type=click.Choice(["price", "purchase"]))
@click.argument("value", type=int)
def cmd_numpad(field: str, value: int) -> None:
    """Enter a value on the numpad (open + clear + type + confirm)."""
    from di_market_manager import actions

    s = _make_session()
    _output(actions.numpad_enter(s, field, value), success_key="success")


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


@cli.group("notify")
def cmd_notify() -> None:
    """Send Discord notifications."""
    pass


@cmd_notify.command("raw")
@click.argument("payload_json")
def cmd_notify_raw(payload_json: str) -> None:
    """Send a raw Discord webhook payload. PAYLOAD_JSON is the full JSON body."""
    from di_market_manager import actions

    s = _make_session()
    _output(actions.notify_discord(s, payload_json), success_key="success")


@cmd_notify.command("scan-report")
@click.argument("report_json")
def cmd_notify_scan_report(report_json: str) -> None:
    """Send a market scan report. REPORT_JSON is the scan data structure.

    Expected format:
    {"gems": {"citrine": {"400": N, "160": N, "140": N, "120": N, "100": N, "80": N, "50": N}, ...}, "errors": [...]}

    A count of 1 is automatically treated as 0 (UI display bug).
    """
    from di_market_manager import actions

    s = _make_session()
    _output(actions.notify_scan_report(s, report_json), success_key="success")


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


@cli.command("locations")
def cmd_locations() -> None:
    """List all valid template and location names from config."""
    config = load_config()
    templates = sorted(config.templates.keys())
    locations = {name: [loc.x, loc.y] for name, loc in sorted(config.locations.items())}
    _output({"templates": templates, "locations": locations, "count": len(templates) + len(locations)})


@cli.command("regions")
def cmd_regions() -> None:
    """List all valid region names from config."""
    config = load_config()
    regions = {name: r.as_tuple() for name, r in sorted(config.regions.items())}
    _output({"regions": regions, "count": len(regions)})


@cli.command("workflows")
def cmd_workflows() -> None:
    """List available workflow files."""
    config = load_config()
    workflows_dir = config.project_dir / "workflows"
    if workflows_dir.is_dir():
        files = sorted(p.name for p in workflows_dir.glob("*.md"))
    else:
        files = []
    _output({"workflows": files, "count": len(files)})


# ---------------------------------------------------------------------------
# Setup subcommands
# ---------------------------------------------------------------------------


@cli.group()
def setup() -> None:
    """Setup tools for template capture and validation."""
    pass


@setup.command("capture")
def setup_capture() -> None:
    """Interactive screenshot marking tool — capture templates and regions."""
    import matplotlib
    matplotlib.use("MacOSX")
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    import numpy as np

    from di_market_manager.vision import take_screenshot_pil

    config = load_config()
    config.templates_dir.mkdir(parents=True, exist_ok=True)

    click.echo("[screenshot taken]")
    screenshot = take_screenshot_pil()
    img_array = np.array(screenshot)

    marked_regions: list[dict] = []
    current_rect: dict = {}

    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    ax.imshow(img_array)
    ax.set_title("Click and drag to mark regions. Close window when done.")
    ax.axis("off")

    rect_artist = None

    def on_press(event):
        nonlocal rect_artist
        if event.inaxes != ax or event.button != 1:
            return
        current_rect["x0"] = int(event.xdata)
        current_rect["y0"] = int(event.ydata)
        current_rect["x1"] = None
        current_rect["y1"] = None
        if rect_artist is not None:
            rect_artist.remove()
        rect_artist = patches.Rectangle(
            (current_rect["x0"], current_rect["y0"]), 0, 0,
            linewidth=2, edgecolor="lime", facecolor="none",
        )
        ax.add_patch(rect_artist)

    def on_motion(event):
        nonlocal rect_artist
        if event.inaxes != ax or "x0" not in current_rect or current_rect.get("x1") is not None:
            return
        if rect_artist is None:
            return
        w = int(event.xdata) - current_rect["x0"]
        h = int(event.ydata) - current_rect["y0"]
        rect_artist.set_width(w)
        rect_artist.set_height(h)
        fig.canvas.draw_idle()

    def on_release(event):
        if event.inaxes != ax or event.button != 1 or "x0" not in current_rect:
            return
        current_rect["x1"] = int(event.xdata)
        current_rect["y1"] = int(event.ydata)

        x0 = min(current_rect["x0"], current_rect["x1"])
        y0 = min(current_rect["y0"], current_rect["y1"])
        x1 = max(current_rect["x0"], current_rect["x1"])
        y1 = max(current_rect["y0"], current_rect["y1"])
        w = x1 - x0
        h = y1 - y0

        if w < 5 or h < 5:
            return

        plt.pause(0.1)
        name = input(f"  Region ({w}x{h}) at ({x0},{y0}). Name (or Enter to skip): ").strip()
        if not name:
            return

        region_type = input(f"  Type — [t]emplate or [r]egion? (default: t): ").strip().lower()
        is_region = region_type.startswith("r")

        if is_region:
            config.regions[name] = Region(x=x0, y=y0, w=w, h=h)
            click.echo(f"  Saved region: {name} ({x0},{y0},{w},{h})")
        else:
            cropped = screenshot.crop((x0, y0, x1, y1))
            template_path = config.templates_dir / f"{name}.png"
            cropped.save(str(template_path))
            config.templates[name] = TemplateDef(
                name=name,
                file=f"templates/{name}.png",
                confidence=0.85,
            )
            click.echo(f"  Saved template: {name}.png ({w}x{h})")

        marked_regions.append({"name": name, "x": x0, "y": y0, "w": w, "h": h})
        ax.text(x0, y0 - 5, name, color="lime", fontsize=8, fontweight="bold")
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect("button_press_event", on_press)
    fig.canvas.mpl_connect("motion_notify_event", on_motion)
    fig.canvas.mpl_connect("button_release_event", on_release)

    plt.tight_layout()
    plt.show()

    if marked_regions:
        save_config(config)
        click.echo(f"\nSaved {len(marked_regions)} region(s) to config.yaml")
    else:
        click.echo("\nNo regions marked.")


@setup.command("test")
def setup_test() -> None:
    """Validate captured templates against current screen."""
    from di_market_manager.vision import (
        find_template_score,
        load_templates,
        take_screenshot,
    )

    config = load_config()

    if not config.templates:
        click.echo("No templates configured. Run `dimm setup capture` first.")
        return

    load_templates(config)
    click.echo("[screenshot taken]")
    screenshot = take_screenshot()

    click.echo("Matching templates...")
    for name, tdef in config.templates.items():
        score, pos = find_template_score(name, screenshot=screenshot, config=config)
        if score >= tdef.confidence:
            click.echo(f"  {name:30s} \u2713 found ({score:.2f}) at {pos}")
        else:
            click.echo(f"  {name:30s} \u2717 not found (best: {score:.2f})")


@setup.command("test-retina")
def setup_test_retina() -> None:
    """Test Retina display scaling — reports logical vs physical resolution."""
    import pyautogui

    from di_market_manager.vision import take_screenshot_pil

    screenshot = take_screenshot_pil()
    physical_w, physical_h = screenshot.size
    logical_w, logical_h = pyautogui.size()
    detected_scale = physical_w // logical_w if logical_w else 1

    click.echo(f"Physical resolution: {physical_w}x{physical_h}")
    click.echo(f"Logical resolution:  {logical_w}x{logical_h}")
    click.echo(f"Detected scale:      {detected_scale}x")
    click.echo(f"\nSet display.retina_scale: {detected_scale} in config.yaml")


@setup.command("record-flow")
@click.option("--interval", default=2.0, help="Screenshot interval in seconds")
def setup_record_flow(interval: float) -> None:
    """Record manual UI navigation flow — screenshots + mouse positions."""
    import json
    import time
    from datetime import datetime

    import pyautogui

    from di_market_manager.vision import take_screenshot_pil

    config = load_config()
    output_dir = config.project_dir / "recordings"
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = output_dir / ts
    session_dir.mkdir()

    click.echo("Recording flow. Perform actions in the game.")
    click.echo("Press Ctrl+C to stop recording.\n")

    steps = []
    step_num = 0

    try:
        last_pos = None
        while True:
            pos = pyautogui.position()
            screenshot = take_screenshot_pil()

            clicked = last_pos is not None and (
                abs(pos[0] - last_pos[0]) > 2 or abs(pos[1] - last_pos[1]) > 2
            )

            step_num += 1
            img_name = f"step_{step_num:03d}.png"
            screenshot.save(str(session_dir / img_name))

            step = {
                "step": step_num,
                "screenshot": img_name,
                "mouse_x": pos[0],
                "mouse_y": pos[1],
                "position_changed": clicked,
                "timestamp": datetime.now().isoformat(),
            }
            steps.append(step)

            click.echo(f"  Step {step_num}: mouse=({pos[0]},{pos[1]}) {'(moved)' if clicked else ''}")
            last_pos = pos
            time.sleep(interval)

    except KeyboardInterrupt:
        click.echo(f"\n\nRecording stopped. {len(steps)} steps captured.")

    flow_file = session_dir / "flow.json"
    with open(flow_file, "w") as f:
        json.dump(steps, f, indent=2)

    click.echo(f"Saved to: {session_dir}")
