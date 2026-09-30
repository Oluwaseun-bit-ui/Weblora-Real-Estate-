#!/bin/bash
# Installs (or re-installs) a macOS launchd job that runs nightly-sync.sh at
# 02:00 every day. If the Mac is asleep at 02:00 it runs when it wakes; if it
# is switched off, that night is skipped. Uninstall with:
#   launchctl bootout gui/$(id -u)/com.weblora.nightly-sync && rm ~/Library/LaunchAgents/com.weblora.nightly-sync.plist
set -euo pipefail
LABEL="com.weblora.nightly-sync"
SCRIPT="$(cd "$(dirname "$0")" && pwd)/nightly-sync.sh"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG="$HOME/Library/Logs/weblora-nightly-sync.log"

mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
chmod +x "$SCRIPT"
cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>$SCRIPT</string></array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>2</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict>
</plist>
PLIST

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Installed $LABEL: runs daily at 02:00. Log: $LOG"
echo "Run it now with: launchctl kickstart gui/$(id -u)/$LABEL"
