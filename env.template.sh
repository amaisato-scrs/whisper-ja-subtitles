#!/usr/bin/env bash
# コピーして env.sh を作る（env.sh は git-ignore 済み）
set -euo pipefail

export WHISPER_HOME="/Users/sato/Scripts/Whisper"
export WORKSPACE_ROOT="${WHISPER_HOME}/Workspace"
export PYTHON="${WHISPER_HOME}/.venv/bin/python"
export PATH="${WHISPER_HOME}/bin:${WHISPER_HOME}/.venv/bin:$PATH"
export SUDACHI_CONFIG_PATH="${WHISPER_HOME}/config/sudachi.json"

mkdir -p "${WORKSPACE_ROOT}/Inbox" "${WORKSPACE_ROOT}/Runs" "${WORKSPACE_ROOT}/Done" "${WORKSPACE_ROOT}/Fail"
