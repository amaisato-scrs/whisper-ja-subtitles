#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 /path/to/audio.(wav|m4a|mp3)"
  exit 1
fi

AUDIO="$1"
source "$(dirname "$0")/../env.sh"

SLUG="run_$(date +%Y%m%d-%H%M%S)"
RUN_DIR="${WORKSPACE_ROOT}/Runs/${SLUG}"
mkdir -p "${RUN_DIR}/asr" "${RUN_DIR}/srt_ja" "${RUN_DIR}/final"

# 1) transcribe
"$PYTHON" -m whisperx "$AUDIO" \
  --model large-v2 --language ja --device cpu \
  --compute_type int8 --output_dir "${RUN_DIR}/asr" --output_format srt

# 2) polish
"$PYTHON" tools/srt_lint_polish.py \
  "${RUN_DIR}/asr/"*.srt \
  -o "${RUN_DIR}/srt_ja/${SLUG}_clean.srt" \
  --lead-in 0.15 --lead-out 0.22 --hysteresis 0.06 \
  --min-dur 1.0 --max-cps 17 --max-chars 42

# 3) refine（Sudachiあり）
"$PYTHON" tools/srt_refine_ja.py \
  "${RUN_DIR}/srt_ja/${SLUG}_clean.srt" \
  -o "${RUN_DIR}/srt_ja/${SLUG}_refined.srt" \
  --no-merge

# 4) 最終の体裁
"$PYTHON" tools/srt_lint_polish.py \
  "${RUN_DIR}/srt_ja/${SLUG}_refined.srt" \
  -o "${RUN_DIR}/final/${SLUG}_ja.final.srt" \
  --lead-in 0.15 --lead-out 0.22 --hysteresis 0.06 \
  --min-dur 1.0 --max-cps 17 --max-chars 42

# 5) 品質チェック（下記tools/srt_qc.py）
"$PYTHON" tools/srt_qc.py "${RUN_DIR}/final/${SLUG}_ja.final.srt"
