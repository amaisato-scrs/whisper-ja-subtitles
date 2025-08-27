# /Users/sato/Scripts/Whisper/bin/lib_notify.sh
#!/usr/bin/env bash
set -euo pipefail

: "${WHISPER_HOME:?source ./env.sh してください}"
STATUS_FILE="${WHISPER_HOME}/_status.txt"

# 文字列を AppleScript 用にエスケープ
_escape_as() {
  local s=$1
  # \ と " をエスケープ
  s=${s//\\/\\\\}; s=${s//\"/\\\"}
  printf '%s' "$s"
}

notify() {
  local msg="${1:-}"
  local subtitle="${2:-}"
  local title="${3:-Whisper Pipeline}"
  local msgE subtitleE titleE
  msgE=$(_escape_as "$msg"); subtitleE=$(_escape_as "$subtitle"); titleE=$(_escape_as "$title")
  /usr/bin/osascript -e "display notification \"${msgE}\" with title \"${titleE}\" subtitle \"${subtitleE}\" sound name \"Glass\"" || true
}

# 状態ファイルへ原子的に書き込み
_write_status() {
  local pct="${1:-0}" desc="${2:-}" extra="${3:-}"
  local tmp
  tmp="$(mktemp "${STATUS_FILE}.XXXX")"
  {
    echo "PERCENT=${pct}"
    echo "DESC=${desc}"
    echo "EXTRA=${extra}"
    echo "UPDATED=$(date +%s)"
  } >"$tmp"
  mv -f "$tmp" "$STATUS_FILE"
}

progress_start() {
  local desc="${1:-開始}"
  _write_status "0" "$desc" ""
}

# pct 変化時のみ通知（スパム防止）
progress_update() {
  local pct="${1:?}"
  local desc="${2:-}"
  local extra="${3:-}"
  local last=999
  if [[ -f "$STATUS_FILE" ]]; then
    # shellcheck disable=SC1090
    source <(grep -E '^(PERCENT|DESC|EXTRA)=' "$STATUS_FILE" | sed 's/\r$//')
    last="${PERCENT:-999}"
  fi
  _write_status "$pct" "$desc" "$extra"
  if [[ "$pct" != "$last" ]]; then
    notify "${desc:-進行中} (${pct}%)" "" "Whisper Pipeline"
  fi
}

progress_end() {
  _write_status "100" "完了" ""
  notify "処理が完了しました" "" "Whisper Pipeline"
}
