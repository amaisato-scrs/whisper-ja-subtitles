# /Users/sato/Scripts/Whisper/config/defaults.sh
#!/usr/bin/env bash
# export 前提（Python からも参照できるように）
# --- モデル / 実行 ---
export CFG_MODEL="large-v2"          # 最高狙いは large-v3 可
export CFG_DEVICE_ASR="cpu"          # ASR デバイス
export CFG_CT2_COMPUTE="int8"        # faster-whisper compute type
export CFG_DEVICE_ALIGN="cpu"        # **必ず CPU (重要)**

# --- 分割/可読性 ---
export JA_MAX_CHARS=40               # 1行あたり最大文字数の目安
export JA_TARGET_CPS=15.0            # 目標 CPS
export JA_MIN_DUR=1.0                # 最小尺
export JA_MAX_DUR=6.0                # 最大尺
export JA_PAUSE_STRONG=0.35          # 強ポーズ閾値 (sec)
export JA_PAUSE_WEAK=0.25            # 弱ポーズ閾値 (sec)
export JA_HYSTERESIS=0.02            # オーバーラップ解消のヒステリシス (sec)
export JA_LEAD_MIN=0.20              # リードイン/アウト最小 (sec 推奨)

# --- チャンク ---
export CFG_CHUNK_SIZE=200            # 行/チャンク

# --- バッチ ---
export CFG_KEEP_ON_FAIL=1            # 失敗時に Inbox に残す (1)
export CFG_BATCH_SLEEP=0             # 多数投入時のスリープ (秒)
