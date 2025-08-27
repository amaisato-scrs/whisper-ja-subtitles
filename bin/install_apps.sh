# /Users/sato/Scripts/Whisper/bin/install_apps.sh
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p "Apps"
echo "[install_apps] Compile AppleScript apps"

# --- HUD: モダン→失敗でレガシーにフォールバック ---
set +e
osacompile -o "Apps/Whisper HUD.app" "shortcuts/WhisperHUD.applescript"
rc=$?
set -e
if [[ $rc -ne 0 ]]; then
  echo "[install_apps] primary HUD script failed (rc=$rc). Fallback to legacy…"
  osacompile -o "Apps/Whisper HUD.app" "shortcuts/WhisperHUD_legacy.applescript"
fi

# --- Inbox ---
osacompile -o "Apps/Whisper Inbox.app" "shortcuts/WhisperInbox.applescript"

echo "[install_apps] Patch Info.plist (LSUIElement, OSAAppletStayOpen, BundleID)"
/usr/bin/plutil -replace LSUIElement -bool YES "Apps/Whisper HUD.app/Contents/Info.plist"
/usr/bin/plutil -replace OSAAppletStayOpen -bool YES "Apps/Whisper HUD.app/Contents/Info.plist"
/usr/bin/plutil -replace CFBundleIdentifier -string "com.sato.whisper.hud" "Apps/Whisper HUD.app/Contents/Info.plist"

/usr/bin/plutil -replace LSUIElement -bool YES "Apps/Whisper Inbox.app/Contents/Info.plist"
/usr/bin/plutil -replace CFBundleIdentifier -string "com.sato.whisper.inbox" "Apps/Whisper Inbox.app/Contents/Info.plist"

echo "[install_apps] Fix permissions & quarantine"
/bin/chmod +x "Apps/Whisper HUD.app/Contents/MacOS/"* 2>/dev/null || true
/bin/chmod +x "Apps/Whisper Inbox.app/Contents/MacOS/"* 2>/dev/null || true

# 絶対パスを使って隔離属性を徹底解除（再帰）
APP_HUD="$PWD/Apps/Whisper HUD.app"
APP_INBOX="$PWD/Apps/Whisper Inbox.app"
/usr/bin/xattr -dr com.apple.quarantine "$APP_HUD" || true
/usr/bin/xattr -dr com.apple.quarantine "$APP_INBOX" || true

echo "[install_apps] Re-register with LaunchServices (lsregister)"
LSREG="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
/usr/bin/env "$LSREG" -f "$APP_HUD" >/dev/null 2>&1 || true
/usr/bin/env "$LSREG" -f "$APP_INBOX" >/dev/null 2>&1 || true

echo "[install_apps] Warm start HUD once (then quit)"
# 既存の幽霊インスタンスを掃除してからウォーム起動→即終了
/usr/bin/pkill -f "Whisper HUD.app" 2>/dev/null || true
/usr/bin/open -gj -n "$APP_HUD" || true
# 起動を待ってから終了（失敗しても続行）
/bin/sleep 0.5
/usr/bin/osascript -e 'tell application id "com.sato.whisper.hud" to quit' || true

echo "done"
