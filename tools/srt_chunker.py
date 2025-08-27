# /Users/sato/Scripts/Whisper/tools/srt_chunker.py
#!/usr/bin/env python3
import os, shutil, argparse, math, srt
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--chunk-size", type=int, default=int(os.environ.get("CFG_CHUNK_SIZE", "200")))
    args = ap.parse_args()

    Path(args.dir).mkdir(parents=True, exist_ok=True)
    with open(args.inp, "r", encoding="utf-8") as f:
        subs = list(srt.parse(f.read()))

    n = len(subs)
    size = max(1, int(args.chunk_size))
    chunks = [subs[i:i+size] for i in range(0, n, size)]

    for ci, chunk in enumerate(chunks, 1):
        out = Path(args.dir) / f"JA_{ci:03d}.srt"
        with open(out, "w", encoding="utf-8") as f:
            f.write(srt.compose(chunk))
    # 翻訳プロンプトもコピー
    root = Path(__file__).resolve().parents[1]
    tpl = root / "templates" / "chatgpt_prompt_translation_ja_to_en.txt"
    if tpl.exists():
        shutil.copy2(tpl, Path(args.dir) / tpl.name)

    print(f"[chunker] wrote {len(chunks)} chunks to {args.dir}")

if __name__ == "__main__":
    main()
