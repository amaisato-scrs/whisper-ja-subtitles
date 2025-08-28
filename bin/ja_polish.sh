# /Users/sato/Scripts/Whisper/bin/ja_polish.sh
#!/usr/bin/env bash
set -euo pipefail
in="${1:-}"; out="${2:-}"
if [[ -z "${in}" || -z "${out}" ]]; then
  echo "Usage: bin/ja_polish.sh <in.srt> <out.srt>" >&2
  exit 2
fi
"$PYTHON" tools/srt_lint_polish.py \
  "${in}" -o "${out}" \
  --lead-in 0.15 --lead-out 0.22 \
  --hysteresis 0.06 \
  --min-dur 1.0 \
  --max-cps 17 \
  --max-chars 42
echo "[ja_polish] wrote: ${out}"
