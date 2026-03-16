# Build A macOS App Bundle With A Custom Icon

## 1) Choose your icon image
- Use a square PNG/JPG (recommended: 1024x1024).
- Place it at `assets/app_icon.png`, or pass a custom image path to the script.

## 2) Build the app
From the project folder:

```bash
chmod +x ./scripts/build_mac_app.sh
./scripts/build_mac_app.sh assets/app_icon.png "Wellness Reminder"
```

Arguments:
- Argument 1: icon image path (PNG/JPG)
- Argument 2: app name (optional, defaults to `Wellness Reminder`)
- Argument 3: `--install` to copy directly into `/Applications`

Example with install:

```bash
./scripts/build_mac_app.sh assets/app_icon.png "Wellness Reminder" --install
```

## 3) Open and pin it
- Open `dist/Wellness Reminder.app` (or `/Applications/Wellness Reminder.app` if installed).
- Right-click its Dock icon and choose Options -> Keep in Dock.

## Notes
- The script auto-installs PyInstaller if missing.
- The icon is converted to a macOS `.icns` file during build.
- Runtime window icon support is built into the app and loads from `assets/app_icon.png` when available.
