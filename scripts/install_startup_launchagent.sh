#!/usr/bin/env zsh
set -euo pipefail

APP_PATH="${1:-/Applications/Wellness Reminder.app}"
LABEL="com.aneesh.wellnessreminder.autostart"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"

if [[ ! -d "$APP_PATH" ]]; then
  echo "App not found at: $APP_PATH"
  echo "Install the app first, or pass the app bundle path as argument 1."
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/open</string>
    <string>-a</string>
    <string>$APP_PATH</string>
    <string>--args</string>
    <string>--background</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>LimitLoadToSessionType</key>
  <array>
    <string>Aqua</string>
  </array>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)" "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
launchctl enable "gui/$(id -u)/$LABEL"

echo "Startup enabled."
echo "LaunchAgent: $PLIST_PATH"
