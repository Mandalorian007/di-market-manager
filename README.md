# DI Market Manager

Automated Diablo Immortal marketplace gem price scanner. Launches the game via BlueStacks Air, navigates to the marketplace, OCRs gem prices, and logs structured price data to stdout. Runs on an hourly loop.

Built for a Mac Mini running BlueStacks Air (Android emulator).

## Requirements

### System

| Requirement | Details |
|---|---|
| OS | macOS |
| Python | 3.11+ |
| Display | Accessible via pyautogui (native macOS display) |
| Tesseract OCR | `tesseract` via Homebrew |
| BlueStacks Air | Installed and logged in |
| Game | Diablo Immortal installed in BlueStacks |

### Install Tesseract

```bash
brew install tesseract
```

Verify: `tesseract --version`

### Python Dependencies

Managed by uv. All pinned in `pyproject.toml`:

- `pyautogui` — screenshot capture, mouse/keyboard automation
- `opencv-python` — template matching
- `Pillow` — image manipulation
- `pytesseract` — Tesseract OCR Python bindings
- `click` — CLI framework
- `pyyaml` — config file parsing
- `matplotlib` — interactive region capture viewer (setup only)

## Install

```bash
cd di-market-manager

# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project + dependencies
uv sync
```

## Project Structure

```
di-market-manager/
├── pyproject.toml
├── config.yaml              # gem list, timings, templates, regions
├── src/di_market_manager/
│   ├── cli.py               # Click CLI entry point
│   ├── config.py            # YAML config → dataclasses
│   ├── vision.py            # template matching + OCR (Retina-aware)
│   ├── game.py              # game lifecycle (launch, navigate, close via BlueStacks)
│   └── scanner.py           # scan cycle + hourly loop
├── templates/               # PNG templates (auto-populated by setup)
└── debug/                   # OCR failure screenshots (auto-populated)
```

## Setup

Before scanning, you need to capture UI templates and mark price regions. This must be done on the Mac Mini with BlueStacks Air running Diablo Immortal.

### 0. Check Retina Scaling

```bash
uv run di-market setup test-retina
```

Reports physical vs logical resolution. Set `display.retina_scale` in `config.yaml` to match (2 for Retina, 1 for non-Retina).

### 1. Capture Templates and Regions

```bash
uv run di-market setup capture
```

Opens an interactive matplotlib window showing a screenshot of the current screen. Click and drag to mark regions:

- **Templates** — UI elements to locate (app icon, HUD indicator, market header, gem tab, search bar). Saved as cropped PNGs in `templates/`.
- **Regions** — pixel areas to OCR (price column, individual price rows). Saved as coordinates in `config.yaml`.

For each marked rectangle, you'll be prompted in the terminal:
```
Region (83x32) at (512,384). Name (or Enter to skip): di_app_icon
Type — [t]emplate or [r]egion? (default: t): t
Saved template: di_app_icon.png (83x32)
```

**Required templates** (names must match what `game.py` expects):

| Template Name | What to Capture |
|---|---|
| `bluestacks_home` | BlueStacks home/launcher screen is visible |
| `di_app_icon` | Diablo Immortal app icon on BlueStacks home |
| `in_game_hud` | Any always-visible HUD element (health globe, minimap corner) |
| `market_button` | The button/icon that opens the marketplace |
| `market_header` | The marketplace window header |
| `gem_tab` | The gem category tab in the marketplace |
| `market_search_bar` | The search input field |

**Required regions** (type `r` when prompted):

| Region Name | What to Mark |
|---|---|
| `price_column` | The full column area containing listing prices |
| `price_row_1` | First listing's price (for per-row OCR) |
| `price_row_2` | Second listing's price |
| ... | As many rows as visible |

### 2. Validate Templates

```bash
uv run di-market setup test
```

Takes a fresh screenshot and reports match confidence for each template, plus OCR results for each region:

```
Matching templates...
  di_app_icon                    ✓ found (0.92) at (512, 384)
  market_header                  ✗ not found (best: 0.61)

Testing OCR on regions...
  price_row_1                    ✓ OCR: "1,234"
```

Re-run `setup capture` for any template that doesn't match. Adjust `confidence` values in `config.yaml` if a template matches correctly but below the default 0.85 threshold.

### 3. Record Navigation Flow (Optional)

```bash
uv run di-market setup record-flow --interval 2
```

Records screenshots + mouse positions as you manually navigate the game UI. Outputs to `recordings/<timestamp>/`. Useful for understanding the exact click sequence needed — reference this when tuning `game.py` navigation functions.

## Usage

### Single Scan

```bash
# Full cycle: launch game → navigate → scan all gems → close game
uv run di-market scan

# Scan one gem only
uv run di-market scan --gem tourmaline

# Game is already open and in the marketplace
uv run di-market scan --skip-launch --skip-close
```

### Hourly Loop

```bash
# Wait one interval, then scan every 60 minutes
uv run di-market start

# Scan immediately on start, then every 60 minutes
uv run di-market start --immediate
```

Pipe to a log file:
```bash
uv run di-market start --immediate 2>&1 | tee market.log
```

### Custom Config Path

```bash
uv run di-market --config /path/to/config.yaml scan
```

## Output Format

All output is structured log lines on stdout:

```
2026-03-12 14:00:05 [SCAN] event=cycle_start
2026-03-12 14:01:12 [PRICE] gem=tourmaline category=normal price=1234 position=1 page=1
2026-03-12 14:01:25 [PRICE] gem=blood-soaked-jade category=legendary stars=5 price=128000 position=1 page=1
2026-03-12 14:03:30 [SCAN] event=cycle_end duration=145s gems_scanned=8 gems_failed=0
2026-03-12 14:03:30 [ERROR] type=ocr_failed gem=topaz region=(400,300,80,20) saved=debug/topaz_*.png
```

## Config Reference

`config.yaml` — edit directly or let `setup capture` populate the `templates` and `regions` sections.

```yaml
game:
  process_name: "BlueStacks"
  window_title: "BlueStacks"
  app_package: "com.blizzard.diab"
  select_all_method: "triple_click"     # triple_click, command_a, or long_press

display:
  retina_scale: 2                       # 1 for non-Retina, 2 for Retina

gems:
  normal:
    - { name: Tourmaline, slug: tourmaline }
    # ...
  legendary:
    - { name: Blood-Soaked Jade, slug: blood-soaked-jade, stars: 5 }

templates:                               # auto-populated by setup capture
  di_app_icon:
    file: "templates/di_app_icon.png"
    confidence: 0.85

regions:                                 # auto-populated by setup capture
  price_row_1: { x: 400, y: 200, w: 100, h: 60 }

timing:
  click_delay: [0.5, 1.5]              # random delay range between clicks (seconds)
  page_load_wait: [3.0, 8.0]           # random delay range after page loads
  scan_interval_minutes: 60
  max_retries: 3
  timeout_multiplier: 1.0              # scales all step timeouts globally
  poll_interval: 0.75                  # seconds between template polls

step_timeouts:                          # per-step timeouts (seconds, pre-multiplier)
  launch_bluestacks: 60
  wait_for_home: 120
  launch_di_app: 180
  navigate_to_market: 30
  search_gem: 15
  default: 20
```

## Error Handling

- **Template not found** — retries up to `max_retries`, then Back-press spam to clear UI, then force-kill and raise
- **OCR failure** — logs error, saves debug screenshot to `debug/`, skips that listing, continues
- **Game crash/disconnect** — detected by template timeout, force-kills BlueStacks, restarts cycle
- **3 consecutive full-cycle failures** — exits with code 1

## Troubleshooting

**Retina scaling issues (clicks land in wrong place):**
Run `uv run di-market setup test-retina` and set `display.retina_scale` in `config.yaml` to match the detected scale.

**Template confidence too low:**
Re-capture with `setup capture`. Avoid capturing regions that change (animations, dynamic text). Crop tightly to the static UI element. Lower the `confidence` value in `config.yaml` if the element has minor rendering variance.

**OCR returns garbage:**
Check `debug/` screenshots. The OCR pipeline expects light text on dark background (or vice versa). If the price region has complex backgrounds, adjust the preprocessing in `vision.py` (`ocr_region` function — threshold method, scale factor).

**`tesseract` not found:**
Ensure Tesseract is installed via Homebrew and on PATH. Verify with `tesseract --version`.

**pyautogui can't take screenshots:**
macOS requires screen recording permission. Grant it in System Settings → Privacy & Security → Screen Recording for your terminal app.

**Keyboard input not reaching BlueStacks:**
Ensure BlueStacks is the focused window. If `pyautogui.typewrite()` doesn't work, try changing `select_all_method` in config. As a last resort, character input may need to be slowed down (increase the `interval` parameter in `typewrite`).

**BlueStacks is sluggish:**
Increase `timeout_multiplier` in `config.yaml` (e.g. 1.5 or 2.0) to globally scale all wait timeouts without editing each step.
