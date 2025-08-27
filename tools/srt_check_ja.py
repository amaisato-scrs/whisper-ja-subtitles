#!/usr/bin/env python3
import re, sys, srt, pathlib
EOS = "。！？!?"
TAILS = ("です","ます","でした","ません","なります","になります")

def end_ok(t):
    t=t.rstrip()
    return bool(t) and (t[-1] in EOS or any(t.endswith(x) for x in TAILS))

p = pathlib.Path(sys.argv[1])
subs = list(srt.parse(p.read_text(encoding="utf-8")))

bad_eos, midword, desu_touch = [], [], []
for s in subs:
    t = s.content.strip()
    if not end_ok(t):
        bad_eos.append((s.index, t))
    if re.search(r'[一-龥ぁ-んァ-ンー][\n][一-龥ぁ-んァ-ンー]', t):
        midword.append((s.index, t))
    if re.search(r'です[一-龥ぁ-んァ-ン0-9A-Za-z]', t):
        desu_touch.append((s.index, t))

print(f"[CHECK] 未終端: {len(bad_eos)} / 語中改行疑い: {len(midword)} / 'です'直後連結: {len(desu_touch)}")

def show(title, arr):
    if not arr: return
    print("\n== " + title + " ==")
    for i, txt in arr[:30]:
        print("#{}: {}".format(i, txt.replace("\n"," / ")))

show("未終端", bad_eos)
show("語中改行?", midword)
show("'です'直後連結", desu_touch)