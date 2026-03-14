# Scan Gem Prices via Bulk Buy

## Goal
Query current gem prices on the Diablo Immortal marketplace using the Bulk Buy feature as a query engine. Produce a summary table of supply at seven price tiers for each gem.

## Agent Behavior
Follow the workflow steps in order. After each command, verify the expected result before moving on. If something breaks — a click misses, a template isn't found, the UI is in an unexpected state — **intervene immediately**:

1. Take a `snapshot` and read it visually to understand what went wrong.
2. Use primitives (`press escape`, `click`, `check`, `wait`) to recover.
3. Resume the workflow from the appropriate step.

Do not blindly retry failed commands. Diagnose first, then act. Track every error you correct so you can report them at the end.

## Final Report
When the workflow is complete, present a **Market Scan Report** table:

| Gem | ≤400 | ≤160 | ≤140 | ≤120 | ≤100 | ≤80 | ≤50 |
|-----|------|------|------|------|------|-----|-----|
| Citrine | | | | | | | |
| Topaz | | | | | | | |
| Sapphire | | | | | | | |
| Aquamarine | | | | | | | |

Fill each cell with the purchase count read from the Bulk Buy dialog at that price tier.

**Count of 1 = 0.** The game UI shows a count of 1 when there are actually zero gems available. Always record 1 as 0 in your report. The `dimm notify scan-report` command also applies this correction automatically.

If the result shows "NONE", record 0.

Also include an **Errors Corrected** section listing every issue encountered and how it was resolved. If none, report "None."

## How Bulk Buy Works as a Query Engine
- Set **Price Limit** to a target platinum amount
- Set **Purchase Limit** to 9999 (max)
- The game caps the purchase count at the actual number of gems available at ≤ that price
- Take a snapshot → read the purchase count visually

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
| `dimm notify scan-report '<json>'` | Send scan report to Discord |
| `dimm notify raw '<json>'` | Send raw JSON payload to Discord |

All commands return JSON to stdout.

## Gems to Scan
`gem_citrine`, `gem_topaz`, `gem_sapphire`, `gem_aquamarine`

## Price Tiers to Query
`[400, 160, 140, 120, 100, 80, 50]`

Scan in descending order (400 first, 50 last) for each gem.

## Workflow Steps

### 0. Focus BlueStacks
Before any UI interaction, bring BlueStacks to the foreground:
```bash
open -a BlueStacks                   # focus the emulator window
```
Do this at the start of the workflow and again any time focus may have shifted (e.g., after a long wait or terminal interaction).

When the workflow is complete, refocus the terminal so the user sees the results:
```bash
open -a Terminal                     # return focus to the user
```

### 1. Launch (if needed)
```bash
dimm status                          # check if running
dimm launch                          # open BlueStacks if not running
dimm wait 20                         # wait for boot
dimm click bluestacks_home_button    # reveal app tiles
dimm click di_app_icon               # launch DI
dimm wait 30                         # DI load time
```

**Tap to Play — requires login delay:**
```bash
dimm wait-for tap_to_play            # wait for title screen
dimm wait 4                          # IMPORTANT: auto-login needs time to complete
dimm click tap_to_play               # now safe to tap
```

```bash
dimm click enter_world
dimm wait-for in_game_hud --timeout 180
```

### 2. Navigate to Market
```bash
dimm click market_button             # opens NPC dialog
dimm wait 3
dimm click services_button           # NPC dialog → Market UI
dimm wait-for gem_tab --timeout 30   # market UI loaded
dimm click gem_tab                   # gem tab = gem marketplace; selects normal gems listing
dimm wait 2
```

### 3. Scan Each Gem
For each gem in order (`gem_citrine`, `gem_topaz`, `gem_sapphire`, `gem_aquamarine`):

#### 3a. Select the gem and open Bulk Buy
```bash
dimm click <gem_name>                # select the gem (coordinate-based location)
dimm wait 2
dimm click bulk_buy_button           # open Bulk Buy dialog
dimm wait 2
```

#### 3b. Query price tiers (with early exit)
Scan tiers in descending order: `[400, 160, 140, 120, 100, 80, 50]`.

For each price:
```bash
dimm numpad price <N>                # set price ceiling
dimm numpad purchase 9999            # set max purchase (game caps at available)
dimm snapshot --name "<gem>_<price>" # capture result
```
**Read the snapshot visually** — record the purchase count shown. If "NONE", record 0. If the count is 1, record 0 (UI display bug).

**Early exit:** If a tier returns 0 or 1 (i.e., zero supply), skip all remaining lower tiers for this gem and record 0 for each. There cannot be supply at a lower price if there is none at a higher one.

#### 3c. Return to gem listing
After all seven price queries for a gem, a single escape exits all the way to the HUD. Then re-enter the market:
```bash
dimm press escape                    # exit Bulk Buy + market → back to HUD
dimm wait 2
dimm wait-for in_game_hud            # verify back on main screen
dimm click market_button             # re-open NPC dialog
dimm wait 3
dimm click services_button           # NPC dialog → Market UI
dimm wait-for gem_tab --timeout 30   # market UI loaded
dimm click gem_tab                   # select normal gems listing
dimm wait 2
```
**Important:** Use only one escape — it exits all the way to the HUD. A second escape from the HUD opens the quit dialog.

### 4. Exit
```bash
dimm press escape                    # close market
dimm wait-for in_game_hud            # verify back on main screen
dimm press escape                    # open quit dialog
dimm wait-for exit_ok_button         # wait for quit dialog to appear
dimm click exit_ok_button            # confirm exit
```

### 5. Post Results to Discord
After presenting the Final Report table, post the results using the scan report command. Pass a clean data structure — the command handles all Discord formatting and normalizes counts of 1 to 0 automatically:
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
Replace `<count>` with integer values read during the scan. Use an empty array `[]` for errors if none occurred. Counts of 9999 (the query cap) display as "10K+" automatically.

## Error Recovery
- If a `click` fails (template not found), take a `snapshot` and read it visually to assess current screen state.
- If the UI is in an unexpected state, use `dimm press escape` to back out, then re-navigate.
- If completely lost, `dimm kill` and restart the flow.
- Use `dimm check <template>` to verify expected UI state before proceeding.
- Always diagnose before retrying — understand *why* something failed.
