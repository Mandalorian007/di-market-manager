from __future__ import annotations

import sys
import time
from datetime import datetime

from di_market_manager.config import Config, GemDef
from di_market_manager.game import (
    close_game,
    kill_game_process,
    launch_game,
    navigate_to_market,
    press_esc_until_clear,
    search_gem,
)
from di_market_manager.vision import load_templates, ocr_price


def log(tag: str, **fields: object) -> None:
    """Print a structured log line to stdout."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parts = " ".join(f"{k}={v}" for k, v in fields.items())
    print(f"{ts} [{tag}] {parts}", flush=True)


def scan_gem_prices(config: Config, gem: GemDef) -> list[dict]:
    """Scan prices for a single gem. Returns list of price records."""
    prices = []
    # Look for price regions — these are named like price_row_1, price_row_2, etc.
    # or use a generic price_column region with listing_row_height
    price_column = config.regions.get("price_column")
    row_height_region = config.regions.get("listing_row_height")
    row_height = 60  # default

    if row_height_region:
        row_height = row_height_region.h  # use h field as row height value

    # Check for individual row regions first
    row_regions = sorted(
        [(name, r) for name, r in config.regions.items() if name.startswith("price_row_")],
        key=lambda x: x[0],
    )

    if row_regions:
        for i, (name, region) in enumerate(row_regions, 1):
            raw_text = None
            price = ocr_price(
                region.as_tuple(),
                debug_dir=config.debug_dir,
                debug_label=f"{gem.slug}_row{i}",
            )
            if price is not None:
                record = {
                    "gem": gem.slug,
                    "category": gem.category,
                    "price": price,
                    "position": i,
                    "page": 1,
                }
                if gem.stars:
                    record["stars"] = gem.stars
                prices.append(record)
                log("PRICE", **record)
            else:
                log("ERROR", type="ocr_failed", gem=gem.slug, region=region.as_tuple(),
                    saved=f"debug/{gem.slug}_row{i}_*.png")
    elif price_column:
        # Derive rows from price_column + row_height
        num_rows = price_column.h // row_height
        for i in range(num_rows):
            region = (
                price_column.x,
                price_column.y + i * row_height,
                price_column.w,
                row_height,
            )
            price = ocr_price(
                region,
                debug_dir=config.debug_dir,
                debug_label=f"{gem.slug}_row{i+1}",
            )
            if price is not None:
                record = {
                    "gem": gem.slug,
                    "category": gem.category,
                    "price": price,
                    "position": i + 1,
                    "page": 1,
                }
                if gem.stars:
                    record["stars"] = gem.stars
                prices.append(record)
                log("PRICE", **record)
            else:
                log("ERROR", type="ocr_failed", gem=gem.slug, region=region,
                    saved=f"debug/{gem.slug}_row{i+1}_*.png")

    return prices


def scan_all_gems(config: Config, gem_filter: str | None = None) -> dict:
    """Scan all gems (or a single gem). Returns summary dict."""
    gems_to_scan = config.gems
    if gem_filter:
        gems_to_scan = [g for g in config.gems if g.slug == gem_filter]
        if not gems_to_scan:
            log("ERROR", type="gem_not_found", slug=gem_filter)
            return {"gems_scanned": 0, "gems_failed": 0}

    total_scanned = 0
    total_failed = 0

    for gem in gems_to_scan:
        try:
            search_gem(config, gem.name)
            prices = scan_gem_prices(config, gem)
            if prices:
                total_scanned += 1
            else:
                total_failed += 1
        except (TimeoutError, Exception) as e:
            log("ERROR", type="scan_failed", gem=gem.slug, error=str(e))
            total_failed += 1

    return {"gems_scanned": total_scanned, "gems_failed": total_failed}


def run_scan_cycle(
    config: Config,
    gem_filter: str | None = None,
    skip_launch: bool = False,
    skip_close: bool = False,
) -> dict:
    """One full scan cycle. Returns summary or raises on unrecoverable error."""
    start = time.time()
    log("SCAN", event="cycle_start")

    load_templates(config)

    try:
        if not skip_launch:
            launch_game(config)

        navigate_to_market(config)
        summary = scan_all_gems(config, gem_filter=gem_filter)

        if not skip_close:
            close_game(config)
    except TimeoutError as e:
        log("ERROR", type="timeout", error=str(e))
        # Try recovery
        try:
            press_esc_until_clear()
            kill_game_process(config)
        except Exception:
            pass
        raise
    except Exception as e:
        log("ERROR", type="unexpected", error=str(e))
        try:
            kill_game_process(config)
        except Exception:
            pass
        raise

    duration = int(time.time() - start)
    log("SCAN", event="cycle_end", duration=f"{duration}s", **summary)
    return summary


def run_hourly_loop(config: Config, immediate: bool = False) -> None:
    """Run scan cycles on the configured interval. Exits after 3 consecutive failures."""
    consecutive_failures = 0
    max_consecutive_failures = 3
    interval = config.timing.scan_interval_minutes * 60

    if not immediate:
        log("SCHEDULER", event="waiting", next_scan_in=f"{config.timing.scan_interval_minutes}m")
        time.sleep(interval)

    while True:
        try:
            run_scan_cycle(config)
            consecutive_failures = 0
        except Exception as e:
            consecutive_failures += 1
            log("ERROR", type="cycle_failed", consecutive=consecutive_failures, error=str(e))
            if consecutive_failures >= max_consecutive_failures:
                log("FATAL", event="too_many_failures",
                    message=f"{max_consecutive_failures} consecutive failures, exiting")
                sys.exit(1)

        log("SCHEDULER", event="waiting", next_scan_in=f"{config.timing.scan_interval_minutes}m")
        time.sleep(interval)
