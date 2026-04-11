# cc-token-status

**Claude Code usage dashboard in your macOS menu bar.**

Costs, plan limits, trends, user level — all in one click. No app to install, no server to run, just a single Python script.

<p align="center">
  <img src=".github/demo.gif" width="450" alt="Demo" />
</p>

## Features

| Feature | Description |
|---------|-------------|
| **Plan Usage Limits** | Live 5h session & 7d weekly quotas with progress bars from Anthropic API |
| **Cost & Token Overview** | API-equivalent cost, session count, total tokens |
| **Subscription ROI** | How much your Pro/Max/Team plan saves vs API pricing |
| **User Level** | 🌑→🌒→🌓→🌔→🌕→👑 cultivation rank based on multi-dimension scoring |
| **Today at a Glance** | Today's spending, tokens, and message count |
| **Daily Details** | Full cost history (newest first, older dates expandable) |
| **Model Breakdown** | Per-model usage (Opus / Sonnet / Haiku) with percentages |
| **Hourly Activity** | Sparkline charts: `▅▇██▇▄` shows which hours you're most active |
| **Project Ranking** | Which projects consume the most tokens |
| **Multi-Machine Sync** | iCloud Drive auto-sync across Macs — zero config |
| **Usage Alerts** | macOS notifications at 80% and 95% plan limits |
| **Settings Menu** | Toggle notifications, auto-update, launch at login, switch plan |
| **Auto-Update** | Checks GitHub daily, silently downloads new versions |
| **5 Languages** | EN, 中文, ES, FR, 日本語 — auto-detected from system |
| **Dark & Light Mode** | Adapts color scheme to macOS appearance |

## User Level System

Multi-dimension scoring based on your Claude Code usage maturity:

```
🌑 Lv.1  Starter      练气期
🌒 Lv.2  Planner      筑基期
🌓 Lv.3  Engineer     金丹期
🌔 Lv.4  Integrator   元婴期
🌕 Lv.5  Architect    化神期
👑 Lv.6  Orchestrator 大乘期
```

Scored across 5 dimensions (100 points total):
- **Usage depth** — median session length, activity density
- **Context management** — CLAUDE.md, memory system, rules
- **Tool ecosystem** — MCP servers, plugins (work tools discounted)
- **Automation** — self-built commands, hooks, skills (framework installs weighted at 30%)
- **Scale** — substantial projects, worktrees, tenure

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/jayson-jia-dev/cc-token-status/main/install.sh | bash
```

## Update

Auto-updates daily. Manual update:

```bash
curl -fsSL https://raw.githubusercontent.com/jayson-jia-dev/cc-token-status/main/install.sh | bash -s -- --update
```

## Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/jayson-jia-dev/cc-token-status/main/uninstall.sh | bash
```

## How It Works

- **Token & cost** — scans Claude Code JSONL session logs, calculates API-equivalent cost with official Anthropic pricing
- **Plan limits** — reads OAuth token from macOS Keychain, queries `api.anthropic.com/api/oauth/usage`
- **Multi-machine sync** — writes stats to iCloud Drive, reads other machines' data automatically
- **Refresh** — SwiftBar executes the plugin every 5 minutes

## Pricing

| Model | Input | Output | Cache Write (1h) | Cache Read |
|-------|-------|--------|-----------------|------------|
| Opus 4.5 / 4.6 | $5 | $25 | $10 | $0.50 |
| Sonnet 4.5 / 4.6 | $3 | $15 | $6 | $0.30 |
| Haiku 4.5 | $1 | $5 | $2 | $0.10 |

*USD per 1M tokens. [Official pricing](https://platform.claude.com/docs/en/about-claude/pricing)*

## Configuration

Edit `~/.config/cc-token-stats/config.json` or use the in-app settings menu:

| Key | Description | Default |
|-----|-------------|---------|
| `subscription` | Monthly plan cost in USD | `0` |
| `subscription_label` | `"Pro"`, `"Max"`, `"Team"` | `""` |
| `language` | `"auto"`, `"en"`, `"zh"`, `"es"`, `"fr"`, `"ja"` | `"auto"` |
| `notifications` | Usage limit alerts | `true` |
| `auto_update` | Daily update check | `true` |
| `sync_mode` | `"auto"` / `"off"` | `"auto"` |

## Requirements

- macOS
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview)
- Python 3.8+
- [SwiftBar](https://github.com/swiftbar/SwiftBar) (auto-installed)

## License

MIT
