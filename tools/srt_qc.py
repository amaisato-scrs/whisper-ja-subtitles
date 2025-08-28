#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, sys, srt, pathlib

EOS = "。！？!?"
TAILS = ("です","ます","でした","ません","なります","になります")

def is_end_ok(t: str) -> bool:
    t = t.rstrip()
    if not t: 
        return True
    if t[-1] in EOS: 
        return True
    return any(t.endswith(x) for x in TAILS)

def main():
    if len(sys.argv) < 2:
        print("usage: srt_qc.py FILE.srt"); sys.exit(1)
    p = pathlib.Path(sys.argv[1])
    subs = list(srt.parse(p.read_text(encoding="utf-8")))

    bad_eos, midword, longline = [], [], []
    for s in subs:
        t = s.content.strip()
        if not is_end_ok(t):
            bad_eos.append((s.index, t.replace("\n"," / ")))
        if re.search(r'[一-龥ぁ-んァ-ン]\n[一-龥ぁ-んァ-ン]', t):
            midword.append((s.index, t.replace("\n"," ↵ ")))
        for line in t.splitlines():
            if len(line) > 42:
                longline.append((s.index, line))

    print(f"[QC] 未終端: {len(bad_eos)} / 語中改行疑い: {len(midword)} / 1行>42字: {len(longline)}")
    def dump(title, lst):
        if not lst: return
        print(f"\n== {title} ==")
        for i, text in lst[:40]:
            print(f"#{i}: {text}")
    dump("未終端", bad_eos)
    dump("語中改行?", midword)
    dump("長行(>42)", longline)

if __name__ == "__main__":
    main()
