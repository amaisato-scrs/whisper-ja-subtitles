# /Users/sato/Scripts/Whisper/bin/ja_from_audio.sh
#!/usr/bin/env bash
set -euo pipefail

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  # 直接実行時のみ env.sh を読む（他のシェルから source されても安全）
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  if [ -f "$ROOT/env.sh" ]; then
    # shellcheck disable=SC1090
    source "$ROOT/env.sh"
  fi
fi

usage() {
  echo "Usage: $(basename "$0") /abs/path/to/input.wav [--merge]" >&2
  exit 1
}

[[ $# -ge 1 ]] || usage
IN="$1"; shift || true
DO_MERGE=0
[[ "${1:-}" == "--merge" ]] && DO_MERGE=1

ts="$(date +%Y%m%d-%H%M%S)"
SLUG="run_${ts}"
RUN_DIR="$WORKSPACE_ROOT/Runs/$SLUG"
mkdir -p "$RUN_DIR"/{asr,srt_ja,final}

echo "[run] SLUG=$SLUG"
echo "[run] IN=$IN"

# 1) ASR (WhisperX)
"$PYTHON" -m whisperx "$IN" \
  --model large-v2 --language ja --device cpu \
  --compute_type int8 \
  --output_dir "$RUN_DIR/asr" --output_format srt

ASR_SRT="$(ls "$RUN_DIR/asr"/*.srt | head -n1)"
echo "[asr] $ASR_SRT"

# 2) 体裁整形（丸め/重なり解消/2行化）
CLEAN="$RUN_DIR/srt_ja/${SLUG}_clean.srt"
"$PYTHON" tools/srt_lint_polish.py "$ASR_SRT" \
  -o "$CLEAN" \
  --lead-in 0.12 --lead-out 0.18 --hysteresis 0.06 \
  --min-dur 1.0 --max-cps 17 --max-chars 42

# 3) 言語的後処理（フィラー除去 + 文境界補正：既定は安全に no-merge）
REFINE="$RUN_DIR/srt_ja/${SLUG}_refine.srt"
if [ $DO_MERGE -eq 1 ]; then
  "$PYTHON" tools/srt_refine_ja.py "$CLEAN" -o "$REFINE"
else
  "$PYTHON" tools/srt_refine_ja.py "$CLEAN" -o "$REFINE" --no-merge
fi

# 4) 仕上げの体裁
FINAL="$RUN_DIR/final/${SLUG}_ja.final.srt"
"$PYTHON" tools/srt_lint_polish.py "$REFINE" \
  -o "$FINAL" \
  --lead-in 0.15 --lead-out 0.22 --hysteresis 0.06 \
  --min-dur 1.0 --max-cps 17 --max-chars 42

echo "[done] $FINAL"