#!/usr/bin/env zsh
set -euo pipefail

LABEL="com.aneesh.wellnessreminder.autostart"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl bootout "gui/$(id -u)" "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl disable "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
rm -f "$PLIST_PATH"

echo "Startup disabled."
echo "Removed: $PLIST_PATH"
