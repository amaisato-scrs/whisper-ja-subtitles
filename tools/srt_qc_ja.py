#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, sys, srt, math, argparse
from pathlib import Path

EOS = "。！？!?"
TAILS = ("です","ます","でした","ません","なります","になります")

def ends_ok(t: str) -> bool:
    t = t.rstrip()
    if not t: return True
    if t[-1] in EOS: return True
    return any(t.endswith(x) for x in TAILS)

def cps(chars: int, dur_s: float) -> float:
    return chars / max(dur_s, 1e-6)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("srt")
    ap.add_argument("--max-cps", type=float, default=17.0)
    args = ap.parse_args()

    p = Path(args.srt)
    subs = list(srt.parse(p.read_text(encoding='utf-8')))

    bad_eos, midword, over_cps = [], [], []
    for s in subs:
        t = s.content.strip()
        if not ends_ok(t):
            bad_eos.append((s.index, t))
        if re.search(r'[一-龥ぁ-んァ-ン][\n][一-龥ぁ-んァ-ン]', t):
            midword.append((s.index, t))
        dur = (s.end - s.start).total_seconds()
        c = len(t.replace("\n",""))
        if cps(c, dur) > args.max_cps:
            over_cps.append((s.index, c, dur))

    print(f"[QC] 未終端: {len(bad_eos)} / 語中改行疑い: {len(midword)} / CPS超過: {len(over_cps)} (> {args.max_cps})")
    if bad_eos:
        print("\n== 未終端例 ==")
        for i, t in bad_eos[:15]:
            print(f"#{i}: {t.replace('\\n',' / ')}")
    if midword:
        print("\n== 語中改行例 ==")
        for i, t in midword[:15]:
            print(f"#{i}: {t.replace('\\n',' / ')}")
    if over_cps:
        print("\n== CPS超過例 ==")
        for i, c, d in over_cps[:15]:
            print(f"#{i}: chars={c} dur={d:.2f}s -> cps={c/d:.2f}")

if __name__ == "__main__":
    main()