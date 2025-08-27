#!/usr/bin/env bash
set -euo pipefail

AUDIO="${1:?usage: ja_from_audio.sh INPUT_AUDIO}"
SLUG="${2:-test_$(date +%Y%m%d-%H%M%S)}"

: "${WHISPER_HOME:="$(cd "$(dirname "$0")/.." && pwd)"}"
: "${WORKSPACE_ROOT:="${WHISPER_HOME}/Workspace"}"
RUN_DIR="${WORKSPACE_ROOT}/Runs/${SLUG}"
mkdir -p "${RUN_DIR}"/{asr,srt_ja,final}

echo "[1/4] Transcribe with WhisperX..."
"$WHISPER_HOME/.venv/bin/python" -m whisperx "$AUDIO" \
  --model large-v2 --language ja --device cpu \
  --compute_type int8 --output_dir "${RUN_DIR}/asr" --output_format srt

echo "[2/4] Lint & polish..."
"$WHISPER_HOME/.venv/bin/python" "$WHISPER_HOME/tools/srt_lint_polish.py" \
  "${RUN_DIR}/asr/"*.srt \
  -o "${RUN_DIR}/srt_ja/${SLUG}_clean.srt" \
  --lead-in 0.15 --lead-out 0.22 --hysteresis 0.06 \
  --min-dur 1.0 --max-cps 17 --max-chars 42

echo "[3/4] Refine (fillers & safe merges)..."
"$WHISPER_HOME/.venv/bin/python" "$WHISPER_HOME/tools/srt_refine_ja.py" \
  "${RUN_DIR}/srt_ja/${SLUG}_clean.srt" \
  -o "${RUN_DIR}/srt_ja/${SLUG}_refined.srt" \
  --merge-pause 0.35 --merge-max 2

echo "[4/4] Final polish (timing/2-lines)..."
"$WHISPER_HOME/.venv/bin/python" "$WHISPER_HOME/tools/srt_lint_polish.py" \
  "${RUN_DIR}/srt_ja/${SLUG}_refined.srt" \
  -o "${RUN_DIR}/final/${SLUG}_ja.final.srt" \
  --lead-in 0.15 --lead-out 0.22 --hysteresis 0.06 \
  --min-dur 1.0 --max-cps 17 --max-chars 42

echo "[QC] Quick check..."
"$WHISPER_HOME/.venv/bin/python" "$WHISPER_HOME/tools/srt_qc_ja.py" \
  "${RUN_DIR}/final/${SLUG}_ja.final.srt" || true

echo "DONE:"
echo "  - ASR:     ${RUN_DIR}/asr/"
echo "  - CLEAN:   ${RUN_DIR}/srt_ja/${SLUG}_clean.srt"
echo "  - REFINED: ${RUN_DIR}/srt_ja/${SLUG}_refined.srt"
echo "  - FINAL:   ${RUN_DIR}/final/${SLUG}_ja.final.srt"