# /Users/sato/Scripts/Whisper/bin/inbox_run_once.sh
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# 環境読み込み
# shellcheck disable=SC1091
source ./env.sh
# shellcheck disable=SC1090
source ./bin/lib_notify.sh

# *.wav のグロブが 0 件でもエラーにしない
shopt -s nullglob

# Inbox の WAV を配列に収集（スペース安全）
WAVS=( "${WORKSPACE_ROOT}/Inbox/"*.wav )

# 空なら通知して終了
if ((${#WAVS[@]} == 0)); then
  notify "Inbox は空です" "" "Whisper Inbox"
  exit 0
fi

# 名前順に **確実に** ソート（ロケール固定）
IFS=$'\n' WAVS=( $(printf '%s\n' "${WAVS[@]}" | LC_ALL=C sort) )
unset IFS

notify "Inbox の WAV を処理開始（${#WAVS[@]} 本）" "" "Whisper Inbox"

for wav in "${WAVS[@]}"; do
  echo "[inbox] processing: ${wav}"
  if bash bin/full_pipeline.sh -i "${wav}"; then
    mv -f "${wav}" "${WORKSPACE_ROOT}/Done/$(basename "$wav")"
  else
    if [[ "${CFG_KEEP_ON_FAIL:-1}" -eq 1 ]]; then
      echo "[inbox] keep on fail: ${wav}"
    else
      mv -f "${wav}" "${WORKSPACE_ROOT}/Fail/$(basename "$wav")"
    fi
  fi
  sleep "${CFG_BATCH_SLEEP:-0}"
done

notify "Inbox の処理が完了しました" "" "Whisper Inbox"
