# /Users/sato/Scripts/Whisper/README.md
# Whisper SRT Pipeline – 再生成仕様 v18 実装
- 入力: Workspace/Inbox に置いた WAV (48k/16bit/mono 推奨、ステレオも可)
- 出力: Runs/<slug>/final に JA/EN SRT
- 依存: Python 3.11, pinned packages (torch/torchaudio/whisperx/faster-whisper 他)
- 通知: osascript 直通知 (バナー+Glass 音)
- HUD: AppleScriptObjC の常時表示バー (Apps/Whisper HUD.app)
- ffmpeg 不要: soundfile + torchaudio で 2ch->mono & 16k リサンプル
- アライン: WhisperX を CPU 固定で実行 (MPS/CPU 型不一致バグ回避)

主なコマンド:
- ./setup.sh                        # venv 作成 & 依存導入
- source ./env.sh                   # 環境変数読み込み
- bash bin/install_apps.sh          # HUD / Inbox アプリ生成
- bash bin/inbox_run_once.sh        # Inbox の WAV を一括処理
- bash bin/view_last_run.sh 200     # 直近ログ確認 (末尾 200 行)
