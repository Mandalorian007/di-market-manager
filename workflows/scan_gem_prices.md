# Scan Gem Prices via Bulk Buy

## Goal
Query current gem prices on the Diablo Immortal marketplace using the Bulk Buy feature as a query engine.

## How Bulk Buy Works as a Query Engine
- Set **Price Limit** to a target platinum amount (e.g., 150)
- Set **Purchase Limit** to 9999 (max)
- The game caps the purchase count at the actual number of gems available at ≤ that price
- Take a snapshot → read the purchase count, total cost, and preview listings visually

## Prerequisites
- BlueStacks Air running on macOS with Diablo Immortal installed
- Templates and regions captured in config.yaml
- `dimm` CLI installed and working

## CLI Commands Reference

| Command | Purpose |
|---------|---------|
| `dimm status` | Check if BlueStacks is running |
| `dimm launch` | Open BlueStacks |
| `dimm click <template>` | Find and click a template |
| `dimm click --xy x,y` | Click raw coordinates |
| `dimm check <template>` | Is this template visible? |
| `dimm wait <seconds>` | Sleep N seconds |
| `dimm wait-for <template>` | Block until template appears |
| `dimm press <key>` | Press keyboard key |
| `dimm snapshot` | Screenshot + all template scores |
| `dimm click-verify <target> <verify>` | Click + verify |
| `dimm numpad price <N>` | Set price limit |
| `dimm numpad purchase <N>` | Set purchase limit |
| `dimm locations` | List all template names |
| `dimm kill` | Force kill BlueStacks |

All commands return JSON to stdout.

## Workflow Steps

### 1. Launch (if needed)
```bash
dimm status                          # check if running
dimm launch                          # open BlueStacks if not running
dimm wait 20                         # wait for boot
dimm click bluestacks_home_button    # reveal app tiles
dimm click di_app_icon               # launch DI
dimm wait 30                         # DI load time
dimm click tap_to_play
dimm click enter_world
dimm wait-for in_game_hud --timeout 180
```

### 2. Navigate to Market
```bash
dimm click market_button             # opens NPC dialog
dimm wait 3
dimm click services_button           # NPC dialog → Market UI
dimm wait-for gem_tab --timeout 30   # market UI loaded
dimm click gem_tab                   # ensure gem tab selected
dimm wait 2
```

### 3. Select Gem
Available gem templates: `gem_citrine`, `gem_topaz`, `gem_sapphire`, `gem_aquamarine`

```bash
dimm click gem_citrine               # select the gem
dimm wait 2
dimm click bulk_buy_button           # open Bulk Buy dialog
dimm wait 2
```

### 4. Query Price via Bulk Buy
```bash
dimm numpad price 150                # set price ceiling to 150 platinum
dimm numpad purchase 9999            # set max purchase (game caps at available)
dimm snapshot --name "citrine_150"   # capture result
```

**Read the snapshot visually** to determine:
- How many gems are available at ≤ 150 platinum
- Total cost shown
- Whether result shows "NONE" (0 available)

### 5. Repeat for Other Prices/Gems
Adjust price to scan different price points (e.g., 100, 150, 200, 250).
Press escape to back out, then select next gem.

### 6. Exit
```bash
dimm press escape                    # close bulk buy
dimm wait 2
dimm press escape                    # close market
dimm wait 2
dimm click exit_ok_button            # exit game (if desired)
```

## Error Recovery
- If a `click` fails (template not found), take a `snapshot` to assess current screen state
- If stuck, `dimm press escape` to back out, then re-navigate
- If completely lost, `dimm kill` and restart the flow
- Use `dimm check <template>` to verify expected UI state before proceeding

## Gems to Scan
From config: tourmaline, ruby, sapphire, citrine, topaz, aquamarine (normal gems)
Legendary: blood-soaked-jade (5-star)
