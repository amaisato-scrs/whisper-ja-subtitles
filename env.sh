# /Users/sato/Scripts/Whisper/env.sh
#!/usr/bin/env bash
# このファイルは bash / zsh いずれから source されても動作するように実装

# --- strict（zsh対応） ---
set -e
set -u
{ set -o pipefail; } 2>/dev/null || true  # 未対応シェルでも落とさない

# --- このファイルの絶対パス（bash / zsh 兼用） ---
__env_file=""
if [ -n "${BASH_SOURCE:-}" ]; then
  # bash: BASH_SOURCE[0] が使える
  __env_file="${BASH_SOURCE[0]}"
elif [ -n "${ZSH_VERSION:-}" ]; then
  # zsh: %N 拡張を eval で評価（bash に読ませても解釈されないように）
  eval '__env_file="${(%):-%N}"'
fi
# 最終フォールバック
if [ -z "${__env_file}" ]; then
  __env_file="$0"
fi

# --- ルート決定 ---
WHISPER_HOME="$(cd "$(dirname "$__env_file")" && pwd)"
export WHISPER_HOME
export WORKSPACE_ROOT="${WHISPER_HOME}/Workspace"
export WHISPER_CONFIG="${WHISPER_HOME}/config/defaults.sh"

# venv を PATH 先頭に
export PYTHON="${WHISPER_HOME}/.venv/bin/python"
export PATH="${WHISPER_HOME}/bin:${WHISPER_HOME}/.venv/bin:$PATH"

# 必要フォルダ
mkdir -p "${WORKSPACE_ROOT}/Inbox" "${WORKSPACE_ROOT}/Runs" "${WORKSPACE_ROOT}/Done" "${WORKSPACE_ROOT}/Fail" \
         "${WHISPER_HOME}/Apps" "${WHISPER_HOME}/shortcuts" "${WHISPER_HOME}/tools" \
         "${WHISPER_HOME}/templates" "${WHISPER_HOME}/config" "${WHISPER_HOME}/bin"

# 既定値をロード
if [ -f "${WHISPER_CONFIG}" ]; then
  if [ -n "${BASH_VERSION:-}" ]; then
    source "${WHISPER_CONFIG}"
  else
    . "${WHISPER_CONFIG}"
  fi
fi

umask 022
unset __env_file

# Sudachi の辞書設定
export SUDACHI_CONFIG_PATH="$WHISPER_HOME/config/sudachi.json"
