# /Users/sato/Scripts/Whisper/tools/srt_join_and_check.py
#!/usr/bin/env python3
import os, argparse, glob, srt
from pathlib import Path
from datetime import timedelta

def read_srt(path):
    with open(path, "r", encoding="utf-8") as f:
        return list(srt.parse(f.read()))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ja", required=True, help="final/<slug>_ja.srt")
    ap.add_argument("--en-dir", required=True, help="chunks_ja dir (expects EN_*.srt)")
    ap.add_argument("--report", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    ja = read_srt(args.ja)
    # EN_* を番号順で連結
    en_paths = sorted(glob.glob(os.path.join(args.en_dir, "EN_*.srt")))
    en = []
    for p in en_paths:
        en.extend(read_srt(p))

    report_lines = []
    if not en_paths:
        report_lines.append("[info] EN_*.srt が見つかりません。全行 JA を転記します。")

    out_subs = []
    m = min(len(ja), len(en))
    if len(en) < len(ja):
        report_lines.append(f"[warn] EN({len(en)}) < JA({len(ja)}) : 欠けた行は JA を転記")
    if len(en) > len(ja):
        report_lines.append(f"[warn] EN({len(en)}) > JA({len(ja)}) : 余剰 EN は切り捨て")

    for i, ja_sub in enumerate(ja, 1):
        text_en = ""
        if i <= len(en):
            text_en = en[i-1].content.strip()
        else:
            text_en = ja_sub.content.strip()  # 欠け → JA で埋め
        out_subs.append(srt.Subtitle(
            index=i,
            start=ja_sub.start, end=ja_sub.end,
            content=text_en
        ))

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(srt.compose(out_subs))

    Path(os.path.dirname(args.report)).mkdir(parents=True, exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")
        f.write(f"JA lines={len(ja)} EN lines={len(en)}\n")
        f.write("EN sources:\n")
        for p in en_paths:
            f.write(f" - {os.path.basename(p)}\n")

    print(f"[join_and_check] wrote: {args.out}")

if __name__ == "__main__":
    main()
