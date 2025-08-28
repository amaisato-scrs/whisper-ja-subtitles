# /Users/sato/Scripts/Whisper/setup.sh
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "[setup] Create venv (.venv) with Python 3.11"
python3 -m venv .venv

echo "[setup] Upgrade pip/setuptools/wheel"
./.venv/bin/python -m pip install --upgrade pip setuptools wheel

echo "[setup] Install pinned dependencies"
# 仕様のピン留めに準拠
./.venv/bin/pip install \
  "torch==2.8.0" "torchaudio==2.8.0" \
  "whisperx==3.4.2" \
  "faster-whisper==1.2.0" "ctranslate2==4.4.0" \
  "numpy==2.2.6" "soundfile>=0.12" "srt==3.5.3" \
  "tqdm" "pandas" "regex==2024.11.6"

echo "[setup] pip check"
./.venv/bin/pip check || true

# ワークスペース基本構造
mkdir -p Workspace/Inbox Workspace/Runs Workspace/Done Workspace/Fail Apps shortcuts

echo "done"
