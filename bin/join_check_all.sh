# /Users/sato/Scripts/Whisper/bin/join_check_all.sh
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "${ROOT_DIR}/env.sh"

for RUN_DIR in "${WORKSPACE_ROOT}/Runs"/*; do
  [[ -d "$RUN_DIR" ]] || continue
  SLUG="$(basename "$RUN_DIR")"
  JA="${RUN_DIR}/final/${SLUG}_ja.srt"
  [[ -f "$JA" ]] || continue
  bash "${ROOT_DIR}/bin/join_check_en.sh" -r "$RUN_DIR" -s "$SLUG" || true
done
