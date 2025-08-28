#!/usr/bin/env bash
set -euo pipefail

# リポジトリのルート
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"

# オプション
OUT=""
STDOUT=0
INCLUDE_WORKSPACE=0
INCLUDE_APPS=0
INCLUDE_VENV=0

usage() {
  cat <<USAGE
Usage: $(basename "$0") [options]

Options:
  -o, --out FILE          出力ファイル（未指定なら bundle/bundle_<UTC>.txt）
      --stdout            標準出力へ書き出し（ファイルは作らない）
      --include-workspace Workspace/ を含める（既定は除外）
      --include-apps      Apps/ を含める（既定は除外）
      --include-venv      .venv/ を含める（既定は除外）
      --all               上3つをすべて含める
  -h, --help              このヘルプ
USAGE
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--out) OUT="${2:-}"; shift 2;;
    --stdout) STDOUT=1; shift;;
    --include-workspace) INCLUDE_WORKSPACE=1; shift;;
    --include-apps) INCLUDE_APPS=1; shift;;
    --include-venv) INCLUDE_VENV=1; shift;;
    --all) INCLUDE_WORKSPACE=1; INCLUDE_APPS=1; INCLUDE_VENV=1; shift;;
    -h|--help) usage;;
    *) echo "unknown option: $1" >&2; usage;;
  esac
done

# 出力先決定
ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
if [[ $STDOUT -eq 0 ]]; then
  mkdir -p "$ROOT/bundle"
  OUT="${OUT:-$ROOT/bundle/bundle_${ts}.txt}"
  exec >"$OUT"
fi

# ヘッダ
echo "# bundle generated: ${ts}"
echo "# root: ${ROOT}"
echo

# ファイル一覧を取得（Git管理下 + 未追跡だが無視されていないもの）
declare -a files
if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  mapfile -t files < <(git -C "$ROOT" ls-files -co --exclude-standard | LC_ALL=C sort)
else
  mapfile -t files < <(cd "$ROOT" && find . -type f -not -path '*/.git/*' | sed 's|^\./||' | LC_ALL=C sort)
fi

should_skip() {
  local p="$1"
  [[ "$p" == .git/* ]] && return 0
  [[ "$p" == *.pyc ]] && return 0
  [[ "$p" == */__pycache__/* ]] && return 0
  [[ "$p" == *.DS_Store || "$p" == .DS_Store ]] && return 0
  [[ "$p" == bundle/* ]] && return 0
  [[ $INCLUDE_VENV -eq 0 && "$p" == .venv/* ]] && return 0
  [[ $INCLUDE_WORKSPACE -eq 0 && "$p" == Workspace/* ]] && return 0
  [[ $INCLUDE_APPS -eq 0 && "$p" == Apps/* ]] && return 0
  return 1
}

sha256sum_() {
  local f="$1"
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$f" | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$f" | awk '{print $1}'
  else
    openssl dgst -sha256 -r "$f" | awk '{print $1}'
  fi
}

filesize_() {
  local f="$1"
  if stat -f%z "$f" >/dev/null 2>&1; then
    stat -f%z "$f"
  else
    stat -c%s "$f"
  fi
}

is_text() {
  # NULバイトが無ければテキストとみなす（高速でそこそこ安全）
  LC_ALL=C grep -Iq . "$1"
}

# 収集
for rel in "${files[@]}"; do
  if should_skip "$rel"; then continue; fi
  abs="$ROOT/$rel"
  [[ -f "$abs" ]] || continue
  size="$(filesize_ "$abs" 2>/dev/null || echo 0)"
  hash="$(sha256sum_ "$abs" 2>/dev/null || echo NA)"

  echo "===== BEGIN ./$rel ====="
  echo "[sha256] $hash"
  echo "[size] ${size}B"

  if is_text "$abs"; then
    # CRLF→LF 正規化だけ軽く
    sed -e $'s/\r$//' "$abs"
  else
    echo "[binary omitted]"  # バイナリは本文を省略（見出しとメタのみ）
  fi

  echo "===== END ./$rel ====="
  echo
done

if [[ $STDOUT -eq 0 ]]; then
  echo "Wrote: $OUT" >&2
fi
