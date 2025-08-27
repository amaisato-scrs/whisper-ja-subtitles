# /Users/sato/Scripts/Whisper/bin/view_last_run.sh
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "${ROOT_DIR}/env.sh"

LINES="${1:-100}"
FOLLOW="${2:-}"

LAST_RUN="$(ls -td "${WORKSPACE_ROOT}/Runs"/* 2>/dev/null | head -n1 || true)"
[[ -n "$LAST_RUN" ]] || { echo "Runs が空です"; exit 1; }

LOG="${LAST_RUN}/logs/pipeline.log"
[[ -f "$LOG" ]] || { echo "ログがありません: $LOG"; exit 1; }

if [[ "$FOLLOW" == "-f" ]]; then
  tail -n "$LINES" -f "$LOG"
else
  tail -n "$LINES" "$LOG"
fi
