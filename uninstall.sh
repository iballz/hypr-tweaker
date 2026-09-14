#!/usr/bin/env bash
# =============================================================================
# Hypr Tweaker - Uninstallation Script
# https://github.com/iballz/hypr-tweaker
# =============================================================================

set -e

if [[ $EUID -eq 0 ]]; then
    PREFIX="/usr"
else
    PREFIX="$HOME/.local"
fi

echo "==> Uninstalling Hypr Tweaker from $PREFIX..."

rm -rf "$PREFIX/share/hypr-tweaker"
rm -f "$PREFIX/bin/hypr-tweaker"
rm -f "$PREFIX/bin/caelestia-hypr-tweaker"
rm -f "$PREFIX/share/applications/hypr-tweaker.desktop"
rm -f "$PREFIX/share/icons/hicolor/scalable/apps/hypr-tweaker.svg"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$PREFIX/share/applications" 2>/dev/null || true
fi

echo "✓ Hypr Tweaker uninstalled."
