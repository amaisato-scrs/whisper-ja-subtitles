# /Users/sato/Scripts/Whisper/bin/join_check_en.sh
#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 -r RUN_DIR -s SLUG"
}

RUN_DIR="" ; SLUG=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -r) RUN_DIR="$2"; shift 2 ;;
    -s) SLUG="$2"; shift 2 ;;
    *) usage; exit 1 ;;
  esac
done

[[ -n "$RUN_DIR" && -n "$SLUG" ]] || { usage; exit 1; }

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "${ROOT_DIR}/env.sh"

"$PYTHON" "${ROOT_DIR}/tools/srt_join_and_check.py" \
  --ja "${RUN_DIR}/final/${SLUG}_ja.srt" \
  --en-dir "${RUN_DIR}/chunks_ja" \
  --report "${RUN_DIR}/srt_en/${SLUG}_join_report.txt" \
  --out "${RUN_DIR}/final/${SLUG}_en.srt"

echo "[join_check_en] out=${RUN_DIR}/final/${SLUG}_en.srt"
