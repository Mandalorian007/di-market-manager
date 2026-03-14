# DI Market Manager

Automated Diablo Immortal marketplace tool. Scans gem prices via the in-game Bulk Buy feature, building toward a fully automated snipe-and-flip arbitrage system.

**Phase 1 (current):** Price scanning — query gem supply at price tiers, log structured data, report to Discord.
**Phase 2 (planned):** Arbitrage — buy underpriced gems and relist at market rate (the marketplace takes a 15% cut on every sale, so profitable flips require ≥17.65% spreads).

Runs on a Mac Mini with BlueStacks Air (Android emulator). An LLM agent supervises workflows by calling CLI primitives and reading screenshots visually (no OCR for decision-making).

## How It Works

The CLI (`dimm`) exposes atomic UI primitives — click, check, wait, snapshot, numpad — that an agent chains together to navigate the game. Every command returns JSON to stdout.

**Bulk Buy as a query engine:** Set Price Limit to a target (e.g., 150 platinum), set Purchase Limit to 9999, and the game caps the count at actual supply. The agent snapshots the result and reads the count visually.

```
market_button → services_button → gem_tab → gem_citrine → bulk_buy_button
→ numpad price 150 → numpad purchase 9999 → snapshot → read result
→ repeat per gem/price point
```

The scan workflow (`workflows/scan_gem_prices.md`) drives the agent through all gems and price tiers, then publishes a formatted report to Discord via `dimm notify scan-report`.

## Quick Start

```bash
# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
cd di-market-manager
uv sync

# Verify
uv run dimm locations    # list all known templates and locations
uv run dimm status       # is BlueStacks running?
```

macOS requires Screen Recording permission for your terminal (System Settings → Privacy & Security → Screen Recording).

## CLI Reference

Every command prints JSON to stdout. Exit code 0 = success, 1 = failure.

### Primitives

```bash
dimm click market_button              # find template on screen, click it
dimm click gem_citrine                # click a named location (fixed coordinates)
dimm click --xy 500,300               # click raw coordinates
dimm check market_header              # is template visible? → {visible, score}
dimm wait 5                           # sleep N seconds
dimm wait-for market_header           # block until template appears
dimm press escape                     # press keyboard key
dimm snapshot                         # screenshot + score all templates
dimm snapshot --name "after_market"   # named snapshot
dimm status                           # is BlueStacks running?
dimm launch                           # open BlueStacks
dimm kill                             # force kill BlueStacks
```

### Composites

```bash
dimm click-verify market_button market_header             # click + wait + verify
dimm click-verify market_button market_header --delay 5   # custom delay
dimm numpad price 250                                     # open + clear + type + confirm
dimm numpad purchase 9999                                 # same for purchase field
```

### Notifications

```bash
dimm notify raw '<json payload>'      # send raw Discord webhook payload
dimm notify scan-report '<json>'      # send validated market scan report
```

The `scan-report` command validates the data structure, builds a formatted Discord embed with a fixed-width table, and posts it to the configured webhook.

Expected format:

```bash
dimm notify scan-report '{
  "gems": {
    "citrine":    {"400": <count>, "160": <count>, "140": <count>, "120": <count>, "100": <count>, "80": <count>, "50": <count>},
    "topaz":      {"400": <count>, "160": <count>, "140": <count>, "120": <count>, "100": <count>, "80": <count>, "50": <count>},
    "sapphire":   {"400": <count>, "160": <count>, "140": <count>, "120": <count>, "100": <count>, "80": <count>, "50": <count>},
    "aquamarine": {"400": <count>, "160": <count>, "140": <count>, "120": <count>, "100": <count>, "80": <count>, "50": <count>}
  },
  "errors": ["<description of any errors corrected during the scan>"]
}'
```

- Gem names and tier keys are validated against known constants
- Tier values must be non-negative integers
- A count of 1 is automatically normalized to 0 (UI display bug)
- Counts of 9999 (the query cap) display as "10K+"

### Discovery

```bash
dimm locations                        # list all template and location names
dimm regions                          # list all region names from config
dimm workflows                        # list workflow prompt files
```

### Setup

```bash
dimm setup capture                    # interactive template/region marking tool
dimm setup test                       # validate templates against current screen
dimm setup test-retina                # check Retina scaling factor
dimm setup record-flow                # record manual navigation (screenshots + mouse)
```

### Validation

Unknown templates and locations are rejected at invocation:

```
$ dimm click foo_bar
{"error": "'foo_bar' is not a known template. Available: market_button, gem_tab, ..."}
```

## Setup

### 1. Check Retina Scaling

```bash
uv run dimm setup test-retina
```

Set `display.retina_scale` in `config.yaml` to match (2 for Retina, 1 for non-Retina).

### 2. Capture Templates and Regions

```bash
uv run dimm setup capture
```

Opens a matplotlib window with a screenshot. Click-drag to mark UI elements:
- **Templates** — buttons, headers, icons to locate via template matching. Saved as PNGs in `templates/`.
- **Regions** — pixel areas for numpad grids. Saved as coordinates in config.
- **Locations** — fixed coordinate click targets (e.g., gem positions). Added manually to `config.yaml`.

### 3. Validate

```bash
uv run dimm setup test
```

Reports match confidence for every template. Re-capture any that score below threshold.

## Config

`config.yaml` defines all valid targets, display settings, gems, and timing:

- **`templates:`** — UI elements matched by image (file path + confidence threshold)
- **`locations:`** — named click targets at fixed coordinates (e.g., `gem_citrine: {x: 847, y: 440}`)
- **`regions:`** — rectangular areas for numpad grids
- **`gems:`** — normal and legendary gem definitions
- **`timing:`** — click delays, page load waits, scan intervals
- **`step_timeouts:`** — per-step timeout limits for workflow phases
- **`display:`** — Retina scaling factor

## Development

### Tooling

- **uv** for dependency management and virtual environments
- **Python 3.11+**
- **hatchling** build backend

```bash
uv sync              # install/update all dependencies
uv run dimm ...      # run CLI commands
```

### Dependencies

| Package | Purpose |
|---------|---------|
| `pyautogui` | Screenshots, mouse/keyboard automation |
| `opencv-python` | Template matching (TM_CCOEFF_NORMED) |
| `Pillow` | Image manipulation |
| `click` | CLI framework |
| `pyyaml` | Config parsing |
| `matplotlib` | Interactive capture tool (setup only) |

### Project Structure

```
di-market-manager/
├── pyproject.toml
├── config.yaml                  # templates, locations, regions, gems, timing
├── src/di_market_manager/
│   ├── cli.py                   # CLI commands (the public interface)
│   ├── actions.py               # primitive implementations + notifications
│   ├── session.py               # Session (config + template cache + action log)
│   ├── config.py                # YAML config → dataclasses
│   └── vision.py                # template matching engine (Retina-aware)
├── templates/                   # PNG templates (tracked in repo)
├── workflows/                   # agent prompt files
│   └── scan_gem_prices.md       # bulk buy price scanning workflow
└── snapshots/                   # screenshots from dimm snapshot
```

### Capturing New Templates

When running via an LLM agent (Claude Code), `dimm setup capture` requires piped stdin since the agent terminal doesn't support interactive `input()`. Pipe the template name and type before launching:

```bash
# 1. Focus BlueStacks so the screenshot captures the game
open -a BlueStacks

# 2. Run capture with the template name and type piped via stdin
#    "t" = template, "r" = region
echo -e "my_button_name\nt" | dimm setup capture
```

The matplotlib window will open with a screenshot. Draw a rectangle around the UI element, then close the window. The piped name and type are consumed automatically — no manual typing needed.

To capture multiple templates, run the command once per template with the game navigated to the correct screen each time.

### Design Principles

**CLI as DSL.** Every UI interaction is a CLI command with validated arguments. The agent calls `dimm click market_button`, not a Python function. This makes workflows inspectable, replayable, and tool-agnostic.

**Config as truth.** `config.yaml` defines all valid templates, locations, and regions. The CLI validates against it — unknown targets are rejected before any screen interaction happens.

**Structured output.** Every command returns JSON. The agent parses results; humans pipe to `jq`.

**Agent as supervisor.** The LLM agent reads screenshots visually (multimodal) and decides what to do next. The CLI primitives are its tools. Error recovery is the agent's job, not hardcoded retry loops.

**No OCR.** The agent reads game state from screenshots directly — no Tesseract, no text parsing. Template matching locates UI elements; the agent interprets everything else visually.
