from __future__ import annotations

import sys
from pathlib import Path

import click

from di_market_manager.config import Config, Region, TemplateDef, load_config, save_config


def _resolve_config(config_path: str | None) -> Config:
    if config_path:
        return load_config(config_path)
    return load_config()


@click.group()
@click.option("--config", "config_path", default=None, help="Path to config.yaml")
@click.pass_context
def cli(ctx: click.Context, config_path: str | None) -> None:
    """DI Market Manager — Diablo Immortal marketplace price scanner (BlueStacks Air on macOS)."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path


@cli.group()
@click.pass_context
def setup(ctx: click.Context) -> None:
    """Setup tools for template capture and validation."""
    pass


@setup.command("capture")
@click.pass_context
def setup_capture(ctx: click.Context) -> None:
    """Interactive screenshot marking tool — capture templates and regions."""
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    import numpy as np

    from di_market_manager.vision import take_screenshot_pil

    config = _resolve_config(ctx.obj["config_path"])
    config.templates_dir.mkdir(parents=True, exist_ok=True)

    click.echo("[screenshot taken]")
    screenshot = take_screenshot_pil()
    img_array = np.array(screenshot)

    # State for interactive marking
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
        # Start drawing rectangle
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

        # Normalize coordinates (handle dragging in any direction)
        x0 = min(current_rect["x0"], current_rect["x1"])
        y0 = min(current_rect["y0"], current_rect["y1"])
        x1 = max(current_rect["x0"], current_rect["x1"])
        y1 = max(current_rect["y0"], current_rect["y1"])
        w = x1 - x0
        h = y1 - y0

        if w < 5 or h < 5:
            # Too small — ignore accidental clicks
            return

        # Prompt for name in terminal
        plt.pause(0.1)
        name = input(f"  Region ({w}x{h}) at ({x0},{y0}). Name (or Enter to skip): ").strip()
        if not name:
            return

        # Determine type
        region_type = input(f"  Type — [t]emplate or [r]egion? (default: t): ").strip().lower()
        is_region = region_type.startswith("r")

        if is_region:
            # Save as named region in config
            config.regions[name] = Region(x=x0, y=y0, w=w, h=h)
            click.echo(f"  Saved region: {name} ({x0},{y0},{w},{h})")
        else:
            # Crop and save as template
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

        # Draw label on the plot
        ax.text(x0, y0 - 5, name, color="lime", fontsize=8, fontweight="bold")
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect("button_press_event", on_press)
    fig.canvas.mpl_connect("motion_notify_event", on_motion)
    fig.canvas.mpl_connect("button_release_event", on_release)

    plt.tight_layout()
    plt.show()

    # Save config after window closes
    if marked_regions:
        save_config(config)
        click.echo(f"\nSaved {len(marked_regions)} region(s) to config.yaml")
    else:
        click.echo("\nNo regions marked.")


@setup.command("test")
@click.pass_context
def setup_test(ctx: click.Context) -> None:
    """Validate captured templates against current screen."""
    from di_market_manager.vision import (
        find_template_score,
        load_templates,
        ocr_region,
        take_screenshot,
    )

    config = _resolve_config(ctx.obj["config_path"])

    if not config.templates:
        click.echo("No templates configured. Run `di-market setup capture` first.")
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

    if config.regions:
        click.echo("\nTesting OCR on regions...")
        for name, region in config.regions.items():
            text = ocr_region(region.as_tuple())
            if text:
                click.echo(f"  {name:30s} \u2713 OCR: \"{text}\"")
            else:
                click.echo(f"  {name:30s} \u2717 OCR failed (empty)")


@setup.command("test-retina")
@click.pass_context
def setup_test_retina(ctx: click.Context) -> None:
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
@click.pass_context
def setup_record_flow(ctx: click.Context, interval: float) -> None:
    """Record manual UI navigation flow — screenshots + mouse positions."""
    import json
    import time
    from datetime import datetime

    import pyautogui

    from di_market_manager.vision import take_screenshot_pil

    config = _resolve_config(ctx.obj["config_path"])
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

            # Detect clicks by position changes (simple heuristic)
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

    # Save flow data
    flow_file = session_dir / "flow.json"
    with open(flow_file, "w") as f:
        json.dump(steps, f, indent=2)

    click.echo(f"Saved to: {session_dir}")


@cli.command("scan")
@click.option("--gem", default=None, help="Scan only this gem (by slug)")
@click.option("--skip-launch", is_flag=True, help="Skip game launch (already running)")
@click.option("--skip-close", is_flag=True, help="Don't close game after scan")
@click.pass_context
def scan(ctx: click.Context, gem: str | None, skip_launch: bool, skip_close: bool) -> None:
    """Run a single scan cycle."""
    from di_market_manager.scanner import run_scan_cycle

    config = _resolve_config(ctx.obj["config_path"])
    try:
        run_scan_cycle(config, gem_filter=gem, skip_launch=skip_launch, skip_close=skip_close)
    except Exception as e:
        click.echo(f"Scan failed: {e}", err=True)
        sys.exit(1)


@cli.command("start")
@click.option("--immediate", is_flag=True, help="Run first scan immediately instead of waiting")
@click.pass_context
def start(ctx: click.Context, immediate: bool) -> None:
    """Start hourly scan loop."""
    from di_market_manager.scanner import run_hourly_loop

    config = _resolve_config(ctx.obj["config_path"])
    click.echo(f"Starting hourly scan loop (interval: {config.timing.scan_interval_minutes}m)")
    run_hourly_loop(config, immediate=immediate)
