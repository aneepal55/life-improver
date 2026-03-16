#!/usr/bin/env zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ICON_SOURCE="${1:-$ROOT_DIR/assets/app_icon.png}"
APP_NAME="${2:-Wellness Reminder}"
INSTALL_FLAG="${3:-}"

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

if [[ ! -f "$ICON_SOURCE" ]]; then
  echo "Icon file not found: $ICON_SOURCE"
  echo "Pass a PNG/JPG path as argument 1, or place a file at assets/app_icon.png"
  exit 1
fi

for cmd in sips iconutil; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required macOS tool: $cmd"
    exit 1
  fi
done

if ! "$PYTHON_BIN" -c "import PyInstaller" >/dev/null 2>&1; then
  echo "Installing PyInstaller..."
  "$PYTHON_BIN" -m pip install pyinstaller
fi

ICONSET_DIR="$ROOT_DIR/build/AppIcon.iconset"
ICNS_PATH="$ROOT_DIR/build/AppIcon.icns"
mkdir -p "$ICONSET_DIR"
rm -f "$ICONSET_DIR"/*(N)

resize_icon() {
  local size="$1"
  local output_name="$2"
  sips -z "$size" "$size" "$ICON_SOURCE" -s format png --out "$ICONSET_DIR/$output_name" >/dev/null
}

resize_icon 16 icon_16x16.png
resize_icon 32 icon_16x16@2x.png
resize_icon 32 icon_32x32.png
resize_icon 64 icon_32x32@2x.png
resize_icon 128 icon_128x128.png
resize_icon 256 icon_128x128@2x.png
resize_icon 256 icon_256x256.png
resize_icon 512 icon_256x256@2x.png
resize_icon 512 icon_512x512.png
resize_icon 1024 icon_512x512@2x.png

iconutil -c icns "$ICONSET_DIR" -o "$ICNS_PATH"

echo "Building app bundle..."
"$PYTHON_BIN" -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "$APP_NAME" \
  --icon "$ICNS_PATH" \
  "$ROOT_DIR/health_app.py"

APP_BUNDLE="$ROOT_DIR/dist/$APP_NAME.app"
if [[ ! -d "$APP_BUNDLE" ]]; then
  echo "Build completed but app bundle was not found at: $APP_BUNDLE"
  exit 1
fi

if [[ "$INSTALL_FLAG" == "--install" ]]; then
  echo "Copying app to /Applications..."
  ditto "$APP_BUNDLE" "/Applications/$APP_NAME.app"
  echo "Installed: /Applications/$APP_NAME.app"
fi

echo "Done. App bundle: $APP_BUNDLE"
echo "You can now open it from Finder, Spotlight, or pin it in the Dock."
