#!/bin/bash
# cc-token-stats installer
# Usage: curl -fsSL https://raw.githubusercontent.com/echowonderfulworld/cc-token-stats/main/install.sh | bash
set -euo pipefail

REPO="https://raw.githubusercontent.com/echowonderfulworld/cc-token-stats/main"
PLUGIN_NAME="cc-token-stats.5m.py"

echo "cc-token-stats installer"
echo ""

# ─── 1. Check Claude Code ───
CLAUDE_DIR="$HOME/.claude"
if [ ! -d "$CLAUDE_DIR" ]; then
    echo "Claude Code config not found at $CLAUDE_DIR"
    echo "   Install Claude Code first: https://claude.ai/download"
    echo ""
    if [ -e /dev/tty ]; then
        read -p "Continue anyway? (y/N) " -n 1 -r < /dev/tty
    else
        REPLY="y"
    fi
    echo ""
    [[ $REPLY =~ ^[Yy]$ ]] || exit 1
fi
if [ -d "$CLAUDE_DIR/projects" ]; then
    echo "* Claude Code data found"
else
    echo "* Claude Code installed (stats will appear after first session)"
fi

# ─── 2. Check/Install SwiftBar ───
if [ -d "/Applications/SwiftBar.app" ]; then
    echo "* SwiftBar already installed"
else
    echo "Installing SwiftBar..."
    if command -v brew &>/dev/null; then
        brew install --cask swiftbar
    else
        echo ""
        echo "SwiftBar is required. Install options:"
        echo "  1. Install Homebrew first: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        echo "     Then: brew install --cask swiftbar"
        echo "  2. Download: https://github.com/swiftbar/SwiftBar/releases"
        echo ""
        echo "Then run this script again."
        exit 1
    fi
fi

# ─── 3. Find/Create plugin directory ───
PLUGIN_DIR=$(defaults read com.ameba.SwiftBar PluginDirectory 2>/dev/null || echo "")
if [ -z "$PLUGIN_DIR" ]; then
    PLUGIN_DIR="$HOME/Library/Application Support/SwiftBar/plugins"
    mkdir -p "$PLUGIN_DIR"
fi
echo "* Plugin directory: $PLUGIN_DIR"

# ─── 4. Download plugin ───
echo "Downloading plugin..."
curl -fsSL "$REPO/$PLUGIN_NAME" -o "$PLUGIN_DIR/$PLUGIN_NAME"
chmod +x "$PLUGIN_DIR/$PLUGIN_NAME"
echo "* Plugin installed"

# ─── 5. Create config ───
CONFIG_DIR="$HOME/.config/cc-token-stats"
CONFIG_FILE="$CONFIG_DIR/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    mkdir -p "$CONFIG_DIR"

    # Interactive subscription picker
    SUB_PRICE=0
    SUB_LABEL=""
    echo ""
    echo "What's your Claude subscription?"
    echo "   1) Pro (\$20/mo)"
    echo "   2) Max 5x (\$100/mo)"
    echo "   3) Max 20x (\$200/mo)"
    echo "   4) Team (\$30/mo)"
    echo "   5) API only / Skip"
    echo ""
    if [ -e /dev/tty ]; then
        read -p "Choose [1-5, default 5]: " -n 1 -r SUB_CHOICE < /dev/tty
    else
        SUB_CHOICE="5"
    fi
    echo ""
    case "$SUB_CHOICE" in
        1) SUB_PRICE=20;  SUB_LABEL="Pro" ;;
        2) SUB_PRICE=100; SUB_LABEL="Max" ;;
        3) SUB_PRICE=200; SUB_LABEL="Max" ;;
        4) SUB_PRICE=30;  SUB_LABEL="Team" ;;
        *) SUB_PRICE=0;   SUB_LABEL="" ;;
    esac
    [ "$SUB_PRICE" -gt 0 ] 2>/dev/null && echo "* $SUB_LABEL \$$SUB_PRICE/mo" || echo "* Skipped (edit config.json later)"

    cat > "$CONFIG_FILE" << CFGEOF
{
  "claude_dir": "$HOME/.claude",
  "sync_mode": "auto",
  "sync_repo": "",
  "subscription": $SUB_PRICE,
  "subscription_label": "$SUB_LABEL",
  "language": "auto",
  "machine_labels": {},
  "menu_bar_icon": "sfSymbol=sparkles.rectangle.stack"
}
CFGEOF
    echo "* Config created: $CONFIG_FILE"

    ICLOUD_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs"
    [ -d "$ICLOUD_DIR" ] && echo "* iCloud Drive detected — multi-machine sync enabled"
else
    echo "* Config exists: $CONFIG_FILE"
fi

# ─── 6. Launch SwiftBar ───
if ! defaults read com.ameba.SwiftBar PluginDirectory &>/dev/null; then
    defaults write com.ameba.SwiftBar PluginDirectory -string "$PLUGIN_DIR"
fi
if ! pgrep -q SwiftBar; then
    echo "Launching SwiftBar..."
    open -a SwiftBar
    sleep 2
fi

echo ""
echo "Done! cc-token-stats is now in your menu bar."
echo ""
echo "   Config: $CONFIG_FILE"
echo "   Plugin: $PLUGIN_DIR/$PLUGIN_NAME"
echo "   Repo:   https://github.com/echowonderfulworld/cc-token-stats"
