# cc-token-status

**Claude Code usage dashboard in your macOS menu bar.**

See costs, plan limits, trends, and multi-machine stats at a glance — all in SwiftBar nested menus. No app to install, no server to run, just a single Python script.

<p align="center">
  <img src=".github/screenshot.png" alt="cc-token-status screenshot" />
</p>

## Features

| Feature | Description |
|---------|-------------|
| **Cost & Token Overview** | API-equivalent cost, session count, total tokens — always visible |
| **Plan Usage Limits** | Official 5h session & 7d weekly quotas with live progress bars from Anthropic API |
| **Subscription ROI** | How much your Pro/Max/Team plan saves vs API pricing |
| **Today at a Glance** | Today's spending, tokens, and message count |
| **Daily Details** | Full cost history by day (newest first, older dates expandable) |
| **Model Breakdown** | Per-model usage (Opus / Sonnet / Haiku) with percentages and cost |
| **Hourly Activity** | Sparkline charts showing which hours you're most active: `▅▇██▇▄` |
| **Project Ranking** | Which projects consume the most tokens |
| **Multi-Machine Sync** | iCloud Drive auto-sync across Macs — zero config |
| **Usage Alerts** | macOS notifications at 80% and 95% plan limits |
| **Settings Menu** | Toggle notifications, launch at login, switch subscription plan |
| **Auto-Update** | Checks GitHub daily, silently downloads new versions |
| **11 Languages** | EN, 中文, ES, FR, PT, DE, RU, 日本語, 한국어, हिन्दी, العربية — auto-detected |
| **Dark & Light Mode** | Adapts color scheme to your macOS appearance |

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/jayson-jia-dev/cc-token-status/main/install.sh | bash
```

The installer will:
1. Check for Claude Code
2. Install [SwiftBar](https://github.com/swiftbar/SwiftBar) if needed (via Homebrew)
3. Download the plugin
4. Ask your subscription tier (for ROI calculation)
5. Detect iCloud Drive for multi-machine sync

## Update

The plugin auto-updates daily. To update manually:

```bash
curl -fsSL https://raw.githubusercontent.com/jayson-jia-dev/cc-token-status/main/install.sh | bash -s -- --update
```

## Plan Usage Limits

Reads your Claude Code OAuth token from the macOS Keychain and queries the Anthropic API to show real-time plan usage:

```
Session ▰▰▱▱▱▱▱▱▱▱   7%  ↻4h5m
Weekly  ▰▰▰▰▰▰▰▱▱▱  67%  ↻3d
Sonnet  ▱▱▱▱▱▱▱▱▱▱   1%  ↻5d
```

- Color-coded: green (<60%) · amber (60–80%) · red (>80%)
- Cached locally (4 min TTL) to respect API rate limits
- Click to see exact reset time

## How It Works

**Token & cost data** — Claude Code writes session logs to `~/.claude/projects/<project>/<session>.jsonl`. Each assistant message includes a `usage` object with `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, and `cache_read_input_tokens`. The plugin scans all JSONL files, aggregates by day/hour/project/model, and calculates API-equivalent cost using official Anthropic pricing.

**Plan limits** — Reads the OAuth access token from macOS Keychain (entry: `Claude Code-credentials`), calls `GET https://api.anthropic.com/api/oauth/usage` to get utilization percentages and reset times.

**Multi-machine sync** — Each machine writes a `token-stats.json` summary to `~/Library/Mobile Documents/com~apple~CloudDocs/cc-token-stats/machines/<hostname>/`. The plugin reads all machines' data and shows a combined view.

**Refresh cycle** — SwiftBar executes the plugin every 5 minutes (configured by the `.5m.` in the filename).

## Pricing

API-equivalent costs use official Anthropic pricing:

| Model | Input | Output | Cache Write | Cache Read |
|-------|-------|--------|-------------|------------|
| Opus 4.5 / 4.6 | $5 | $25 | $10 | $0.50 |
| Sonnet 4.5 / 4.6 | $3 | $15 | $3.75 | $0.30 |
| Haiku 4.5 | $1 | $5 | $1.25 | $0.10 |

*USD per 1M tokens.*

## Configuration

Edit `~/.config/cc-token-stats/config.json`:

```json
{
  "subscription": 100,
  "subscription_label": "Max",
  "language": "auto",
  "sync_mode": "auto",
  "machine_labels": {
    "my-hostname": "Office Mac"
  }
}
```

| Key | Description | Default |
|-----|-------------|---------|
| `subscription` | Monthly plan cost in USD (0 to hide ROI) | `0` |
| `subscription_label` | Plan name: `"Pro"`, `"Max"`, `"Team"` | `""` |
| `language` | `"auto"`, `"en"`, or `"zh"` | `"auto"` |
| `sync_mode` | `"auto"` (iCloud), `"custom"`, or `"off"` | `"auto"` |
| `machine_labels` | Friendly names for hostnames | auto-detect |
| `menu_bar_icon` | SwiftBar SF Symbol | `sfSymbol=sparkles.rectangle.stack` |

## Requirements

- macOS
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview)
- Python 3.8+
- [SwiftBar](https://github.com/swiftbar/SwiftBar) (auto-installed by installer)

## Uninstall

```bash
# Remove plugin and config
rm -f ~/Library/Application\ Support/SwiftBar/plugins/cc-token-stats.5m.py
rm -rf ~/.config/cc-token-stats

# Optional: remove iCloud sync data
rm -rf ~/Library/Mobile\ Documents/com~apple~CloudDocs/cc-token-stats

# Optional: uninstall SwiftBar
brew uninstall --cask swiftbar
```

## License

MIT
