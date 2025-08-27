# /Users/sato/Scripts/Whisper/tools/transcribe_from_wav.py
#!/usr/bin/env python3
import os, sys, json, argparse, math
import numpy as np
import soundfile as sf
import torch
import torchaudio
from faster_whisper import WhisperModel
import whisperx
import srt
from datetime import timedelta
from pathlib import Path

def read_and_normalize(wav_path: str) -> np.ndarray:
    data, sr = sf.read(wav_path, dtype="float32", always_2d=False)
    if data.ndim == 2:
        data = data.mean(axis=1)
    if sr != 16000:
        # resample to 16k (cpu)
        x = torch.from_numpy(data).unsqueeze(0)
        y = torchaudio.functional.resample(x, orig_freq=sr, new_freq=16000)
        data = y.squeeze(0).numpy()
    # Clamp to [-1,1]
    data = np.clip(data, -1.0, 1.0).astype("float32")
    return data

def save_srt(segments, out_path: str):
    items = []
    idx = 1
    for seg in segments:
        st = max(0.0, float(seg["start"]))
        en = max(st, float(seg["end"]))
        text = seg["text"].strip()
        items.append(srt.Subtitle(index=idx,
                                  start=timedelta(seconds=st),
                                  end=timedelta(seconds=en),
                                  content=text))
        idx += 1
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(srt.compose(items))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--slug", required=True)
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    asr_dir = run_dir / "asr"
    asr_dir.mkdir(parents=True, exist_ok=True)

    model_name = os.environ.get("CFG_MODEL", "large-v2")
    compute_type = os.environ.get("CFG_CT2_COMPUTE", "int8")
    device_asr = os.environ.get("CFG_DEVICE_ASR", "cpu")
    device_align = os.environ.get("CFG_DEVICE_ALIGN", "cpu")

    print(f"[transcribe] model={model_name} compute={compute_type} asr_device={device_asr} align_device={device_align}")
    audio = read_and_normalize(args.input)

    # --- ASR (faster-whisper) ---
    model = WhisperModel(model_name, device=device_asr, compute_type=compute_type)
    segments_iter, info = model.transcribe(audio, language="ja", task="transcribe", beam_size=5)
    segments = []
    for seg in segments_iter:
        segments.append({"start": float(seg.start), "end": float(seg.end), "text": seg.text.strip()})

    raw_srt = asr_dir / f"{args.slug}_ja-JP_raw.srt"
    save_srt(segments, str(raw_srt))
    # 固定名リンク
    try:
        p = asr_dir / "ja-JP_raw.srt"
        if p.exists() or p.is_symlink():
            p.unlink()
        p.symlink_to(raw_srt.name)
    except Exception as e:
        print(f"[warn] symlink ja-JP_raw.srt: {e}")

    # --- Alignment (WhisperX, CPU 固定) ---
    print("[transcribe] load align model (ja, cpu)")
    align_model, metadata = whisperx.load_align_model(language_code="ja", device=device_align)
    aligned_result = whisperx.align(segments, align_model, metadata, audio, device=device_align, return_char_alignments=False)

    aligned_json = {
        "language": "ja",
        "segments": aligned_result.get("segments", [])
    }

    out_json = asr_dir / f"{args.slug}_aligned.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(aligned_json, f, ensure_ascii=False, indent=2)
    try:
        p = asr_dir / "aligned.json"
        if p.exists() or p.is_symlink():
            p.unlink()
        p.symlink_to(out_json.name)
    except Exception as e:
        print(f"[warn] symlink aligned.json: {e}")

    print(f"[transcribe] wrote: {out_json}")
    print("[transcribe] done")

if __name__ == "__main__":
    main()
