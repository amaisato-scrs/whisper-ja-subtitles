# /Users/sato/Scripts/Whisper/bin/full_pipeline.sh
#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<USAGE
Usage: $0 -i INPUT.wav [-p PROMPT] [-b BASENAME] [--date YYYYMMDD] [--take NN]
USAGE
}

# --- 引数 ---
INPUT=""
PROMPT=""
BASENAME=""
DATE_TAG=""
TAKE_TAG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -i) INPUT="${2:-}"; shift 2 ;;
    -p) PROMPT="${2:-}"; shift 2 ;;
    -b) BASENAME="${2:-}"; shift 2 ;;
    --date) DATE_TAG="${2:-}"; shift 2 ;;
    --take) TAKE_TAG="${2:-}"; shift 2 ;;
    *) usage; exit 1 ;;
  esac
done

[[ -f "$INPUT" ]] || { echo "INPUT not found: $INPUT" >&2; exit 1; }

# --- パス/環境 ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
# shellcheck disable=SC1091
source "${ROOT_DIR}/env.sh"
# shellcheck disable=SC1090
source "${ROOT_DIR}/bin/lib_notify.sh"

# --- slug 生成 ---
NAME="${BASENAME:-$(basename "$INPUT")}"
NAME="${NAME%.*}"
SLUG="$("$PYTHON" "${ROOT_DIR}/tools/slugify.py" "$NAME")"
if [[ -n "$DATE_TAG" ]]; then SLUG="${SLUG}_${DATE_TAG}"; fi
if [[ -n "$TAKE_TAG" ]]; then SLUG="${SLUG}_$(printf "%02d" "$TAKE_TAG")"; fi

# --- 出力場所 ---
RUN_DIR="${WORKSPACE_ROOT}/Runs/${SLUG}"
mkdir -p "${RUN_DIR}/"{input,asr,srt_ja,chunks_ja,srt_en,final,logs}

# --- ログ tee ---
LOG="${RUN_DIR}/logs/pipeline.log"
exec > >(tee -a "$LOG") 2>&1

echo "[pipeline] SLUG=${SLUG}"
echo "[pipeline] RUN_DIR=${RUN_DIR}"
cp -f "$INPUT" "${RUN_DIR}/input/"

# --- 進捗開始 ---
progress_start "開始…"
notify "開始: $(basename "$INPUT")" "${SLUG}" "Whisper Pipeline"

# 1) ASR + アライン（WhisperX, CPU固定）
progress_update 5 "ASR 準備中"
"$PYTHON" "${ROOT_DIR}/tools/transcribe_from_wav.py" \
  --input "$INPUT" \
  --run-dir "$RUN_DIR" \
  --slug "$SLUG"
progress_update 40 "アライン完了"

# 2) 日本語セグメント生成（高精度版）
ALIGNED_JSON="${RUN_DIR}/asr/aligned.json"  # transcribe で作る固定名シンボリックリンク
"$PYTHON" "${ROOT_DIR}/tools/segment_ja.py" \
  "$ALIGNED_JSON" \
  -o "${RUN_DIR}/srt_ja/${SLUG}_ja-JP_seg.srt"

# 2.5) 構造修復（フラグメント救済・短尺補正／用語置換なし）
"$PYTHON" "${ROOT_DIR}/tools/srt_repair_fragments_ja.py" \
  "${RUN_DIR}/srt_ja/${SLUG}_ja-JP_seg.srt" \
  -o "${RUN_DIR}/srt_ja/${SLUG}_ja-JP_seg.srt"
progress_update 60 "フラグメント修復"

# 3) 整形（丸め・オーバーラップ解消・リードイン/アウト・折返し）
"$PYTHON" "${ROOT_DIR}/tools/srt_lint_polish.py" \
  "${RUN_DIR}/srt_ja/${SLUG}_ja-JP_seg.srt" \
  -o "${RUN_DIR}/srt_ja/${SLUG}_ja_clean.srt"
cp -f "${RUN_DIR}/srt_ja/${SLUG}_ja_clean.srt" "${RUN_DIR}/final/${SLUG}_ja.srt"
progress_update 75 "JA 整形"

# 4) チャンク分割（翻訳用 JA_*.srt）
"$PYTHON" "${ROOT_DIR}/tools/srt_chunker.py" \
  --in "${RUN_DIR}/final/${SLUG}_ja.srt" \
  --dir "${RUN_DIR}/chunks_ja" \
  --chunk-size "${CFG_CHUNK_SIZE}"
progress_update 85 "翻訳チャンク生成"

# 4.5) 翻訳依頼の通知
notify "ChatGPT で JA_*.srt → EN_*.srt に翻訳し、同フォルダへ保存してください" "Runs/${SLUG}/chunks_ja" "Whisper Pipeline"

# 5) EN 結合・チェック（JA 時刻を正とする）
bash "${ROOT_DIR}/bin/join_check_en.sh" -r "${RUN_DIR}" -s "${SLUG}"
progress_update 95 "EN 結合"

# 完了
progress_end
echo "[pipeline] done"
