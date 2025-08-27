# /Users/sato/Scripts/Whisper/bin/setup.sh
#!/usr/bin/env bash
set -euo pipefail
# 互換: 仕様に bin/setup.sh 記述があるため、ルートの setup.sh を呼ぶ
SCRIPT_DIR="$(cd "$(dirname "$0")"/.. && pwd)"
exec "${SCRIPT_DIR}/setup.sh"
