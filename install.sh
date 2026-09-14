#!/usr/bin/env bash
# =============================================================================
# Hypr Tweaker - Installation Script
# https://github.com/iballz/hypr-tweaker
# =============================================================================

set -e

# Detect user vs system installation
if [[ $EUID -eq 0 ]]; then
    PREFIX="/usr"
    BIN_DIR="$PREFIX/bin"
    SHARE_DIR="$PREFIX/share/hypr-tweaker"
    APP_DIR="$PREFIX/share/applications"
    ICON_DIR="$PREFIX/share/icons/hicolor/scalable/apps"
    MODE="system-wide"
else
    PREFIX="$HOME/.local"
    BIN_DIR="$PREFIX/bin"
    SHARE_DIR="$PREFIX/share/hypr-tweaker"
    APP_DIR="$PREFIX/share/applications"
    ICON_DIR="$PREFIX/share/icons/hicolor/scalable/apps"
    MODE="user ($USER)"
fi

echo "==> Installing Hypr Tweaker ($MODE mode)..."

# Ensure directories exist
mkdir -p "$BIN_DIR" "$SHARE_DIR/src" "$APP_DIR" "$ICON_DIR"

# Copy application source files
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
cp -f "$SCRIPT_DIR/src/"*.py "$SHARE_DIR/src/"

# Install executable wrapper
cp -f "$SCRIPT_DIR/bin/hypr-tweaker" "$BIN_DIR/hypr-tweaker"
chmod +x "$BIN_DIR/hypr-tweaker"
chmod +x "$SHARE_DIR/src/"*.py

# Provide legacy alias symlink for caelestia-hypr-tweaker if not conflicting
ln -sf "$BIN_DIR/hypr-tweaker" "$BIN_DIR/caelestia-hypr-tweaker"

# Install desktop entry
cp -f "$SCRIPT_DIR/hypr-tweaker.desktop" "$APP_DIR/hypr-tweaker.desktop"

# Install icon
if [[ -f "$SCRIPT_DIR/assets/hypr-tweaker.svg" ]]; then
    cp -f "$SCRIPT_DIR/assets/hypr-tweaker.svg" "$ICON_DIR/hypr-tweaker.svg"
fi

# Update desktop and icon databases if available
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APP_DIR" 2>/dev/null || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$(dirname "$ICON_DIR")" 2>/dev/null || true
fi

echo ""
echo "✓ Hypr Tweaker successfully installed!"
echo "  • Executable: $BIN_DIR/hypr-tweaker"
echo "  • Desktop:    $APP_DIR/hypr-tweaker.desktop"
echo "  • Icon:       $ICON_DIR/hypr-tweaker.svg"
echo ""
echo "You can launch it from your application menu or run:"
echo "    hypr-tweaker"
echo ""
