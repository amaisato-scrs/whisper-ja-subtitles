# /Users/sato/Scripts/Whisper/bin/ja_polish.sh
#!/usr/bin/env bash
set -euo pipefail
in="${1:-}"; out="${2:-}"
if [[ -z "${in}" || -z "${out}" ]]; then
  echo "Usage: bin/ja_polish.sh <in.srt> <out.srt>" >&2
  exit 2
fi
python tools/srt_lint_polish.py \
  "${in}" -o "${out}" \
  --lead-in 0.2 --lead-out 0.2 \
  --hysteresis 0.02 \
  --min-dur 1.0 \
  --max-cps 19.5 \
  --max-chars 40
echo "[ja_polish] wrote: ${out}"
