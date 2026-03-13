# DI Market Manager

Automated Diablo Immortal marketplace gem price scanner. Launches the game via Battle.net, navigates to the marketplace, OCRs gem prices, and logs structured price data to stdout. Runs on an hourly loop.

Built for a headless-ish AWS Lightsail instance (1024x768) where Battle.net auto-starts on boot.

## Requirements

### System

| Requirement | Details |
|---|---|
| OS | Linux (Lightsail) or macOS |
| Python | 3.11+ |
| Display | 1024x768, accessible via pyautogui (X11/Xvfb or native) |
| Tesseract OCR | `tesseract-ocr` system package |
| Battle.net | Running and logged in (auto-start on boot) |
| Game | Diablo Immortal installed, Play button visible in Battle.net |

### Install Tesseract

**Ubuntu/Debian (Lightsail):**
```bash
sudo apt update && sudo apt install -y tesseract-ocr
```

**macOS:**
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
# Clone and enter project
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
│   ├── vision.py            # template matching + OCR
│   ├── game.py              # game lifecycle (launch, navigate, close)
│   └── scanner.py           # scan cycle + hourly loop
├── templates/               # PNG templates (auto-populated by setup)
└── debug/                   # OCR failure screenshots (auto-populated)
```

## Setup (Run on Lightsail)

Before scanning, you need to capture UI templates and mark price regions. This must be done on the machine where the game runs, at the actual screen resolution.

### 1. Capture Templates and Regions

```bash
uv run di-market setup capture
```

Opens an interactive matplotlib window showing a screenshot of the current screen. Click and drag to mark regions:

- **Templates** — UI elements to locate (Play button, HUD indicator, market header, gem tab, search bar). Saved as cropped PNGs in `templates/`.
- **Regions** — pixel areas to OCR (price column, individual price rows). Saved as coordinates in `config.yaml`.

For each marked rectangle, you'll be prompted in the terminal:
```
Region (83x32) at (512,384). Name (or Enter to skip): battlenet_play_button
Type — [t]emplate or [r]egion? (default: t): t
Saved template: battlenet_play_button.png (83x32)
```

**Required templates** (names must match what `game.py` expects):

| Template Name | What to Capture |
|---|---|
| `battlenet_play_button` | The Play button in Battle.net launcher |
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
  battlenet_play_button        ✓ found (0.92) at (512, 384)
  market_header                ✗ not found (best: 0.61)

Testing OCR on regions...
  price_row_1                  ✓ OCR: "1,234"
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
  window_title: "Diablo Immortal"
  process_name: "DiabloImmortal.exe"      # used by pkill/taskkill to force-close

gems:
  normal:
    - { name: Tourmaline, slug: tourmaline }
    # ...
  legendary:
    - { name: Blood-Soaked Jade, slug: blood-soaked-jade, stars: 5 }

templates:                                  # auto-populated by setup capture
  battlenet_play_button:
    file: "templates/battlenet_play_button.png"
    confidence: 0.9                         # match threshold (0.0–1.0)

regions:                                    # auto-populated by setup capture
  price_row_1: { x: 400, y: 200, w: 100, h: 60 }

timing:
  click_delay: [0.3, 0.8]                  # random delay range between clicks (seconds)
  page_load_wait: [1.5, 3.0]               # random delay range after page loads
  scan_interval_minutes: 60                 # loop interval
  max_retries: 3                            # retries per operation before giving up
```

## Error Handling

- **Template not found** — retries up to `max_retries`, then ESC spam to clear UI, then force-kill and raise
- **OCR failure** — logs error, saves debug screenshot to `debug/`, skips that listing, continues
- **Game crash/disconnect** — detected by template timeout, force-kills game, restarts cycle
- **3 consecutive full-cycle failures** — exits with code 1

## Troubleshooting

**`setup capture` window doesn't open:**
Needs a display. On Lightsail, connect via VNC/RDP or run with `DISPLAY=:0` if using Xvfb.

**Template confidence too low:**
Re-capture with `setup capture`. Avoid capturing regions that change (animations, dynamic text). Crop tightly to the static UI element. Lower the `confidence` value in `config.yaml` if the element has minor rendering variance.

**OCR returns garbage:**
Check `debug/` screenshots. The OCR pipeline expects light text on dark background (or vice versa). If the price region has complex backgrounds, you may need to adjust the preprocessing in `vision.py` (`ocr_region` function — threshold method, scale factor).

**`tesseract` not found:**
Ensure `tesseract-ocr` is installed system-wide and on PATH. Verify with `tesseract --version`.

**pyautogui can't take screenshots:**
On Linux, requires X11. If running headless, set up Xvfb:
```bash
sudo apt install -y xvfb
Xvfb :99 -screen 0 1024x768x24 &
export DISPLAY=:99
```
