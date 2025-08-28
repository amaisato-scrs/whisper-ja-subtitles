#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== Path check =="
pwd; git rev-parse --show-toplevel

echo "== Recreate skeleton =="
mkdir -p Workspace/{Inbox,Runs,Done,Fail} config bin tools templates shortcuts Apps
touch Workspace/.gitkeep Workspace/Inbox/.gitkeep Workspace/Runs/.gitkeep Workspace/Done/.gitkeep Workspace/Fail/.gitkeep

echo "== Sudachi check =="
if [ -f config/sudachi.json ]; then
  echo "  config/sudachi.json exists"
else
  "$PWD/.venv/bin/python" - <<'PY'
import json, os, importlib
base = os.path.dirname(importlib.import_module("sudachidict_full").__file__)
cfg={"systemDict": os.path.join(base,"resources","system.dic")}
os.makedirs("config", exist_ok=True)
open("config/sudachi.json","w").write(json.dumps(cfg, ensure_ascii=False, indent=2))
print("wrote config/sudachi.json")
PY
fi

SUDACHI_CONFIG_PATH="$PWD/config/sudachi.json" "$PWD/.venv/bin/python" - <<'PY'
from sudachipy import dictionary, tokenizer as t
tok = dictionary.Dictionary(config_path="${SUDACHI_CONFIG_PATH}").create()
m = tok.tokenize("こんにちは、ね です よね。", t.Tokenizer.SplitMode.C)
print("Sudachi OK:", [(w.surface(), w.part_of_speech()) for w in m])
PY

echo "== Done =="
