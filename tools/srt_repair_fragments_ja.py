# /Users/sato/Scripts/Whisper/tools/srt_repair_fragments_ja.py
# v2.1: 断片（≤6〜8文字）と語尾（す・ね・よ・が・と・で・も・に 等）を右優先で結合。
#       マージ後に最小尺やCPSも軽くケア。
import re, sys, argparse
from dataclasses import dataclass

TIMECODE = re.compile(r"(\d\d):(\d\d):(\d\d),(\d\d\d)\s*-->\s*(\d\d):(\d\d):(\d\d),(\d\d\d)")
TAILERS = tuple("すねよがとでもにはをがの".split())
SENT_PUNCTS = "。！？…"

def t2s(h, m, s, ms): return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000.0
def s2t(x):
    x = max(0.0, x)
    h = int(x//3600); x -= h*3600
    m = int(x//60);   x -= m*60
    s = int(x);       ms = int(round((x-s)*1000))
    if ms == 1000: s += 1; ms = 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

@dataclass
class Block:
    idx: int
    st: float
    en: float
    text: str
    @property
    def dur(self): return self.en - self.st
    @property
    def chars(self): return len(self.text.replace("\n",""))
    @property
    def cps(self): return self.chars / max(1e-6, self.dur)

def read_srt(path):
    out=[]
    with open(path, "r", encoding="utf-8") as f:
        buf=[]
        for line in f:
            if line.strip()=="":
                if buf: out.append(parse_block(buf)); buf=[]
            else:
                buf.append(line.rstrip("\n"))
    if buf: out.append(parse_block(buf))
    for i,b in enumerate(out,1): b.idx=i
    return out

def parse_block(lines):
    idx = int(lines[0].strip()) if lines and lines[0].strip().isdigit() else 0
    m = TIMECODE.match(lines[1])
    st = t2s(*m.groups()[:4]); en = t2s(*m.groups()[4:])
    text = "\n".join(lines[2:]).strip()
    return Block(idx, st, en, text)

def write_srt(path, blocks):
    with open(path, "w", encoding="utf-8") as f:
        for i,b in enumerate(blocks,1):
            f.write(f"{i}\n{s2t(b.st)} --> {s2t(b.en)}\n{b.text}\n\n")

def looks_fragment(b: Block, low_chars:int):
    if b.chars <= low_chars: return True
    # 行末が機能語/語尾のみで終わる場合も断片扱い
    t = b.text.replace("\n","")
    if len(t)<=8 and (len(t)==1 or t[-1] in TAILERS): return True
    return False

def repair(blocks, min_dur, max_dur, low_chars=6, max_cps=19.0):
    i=0
    while i < len(blocks):
        b = blocks[i]
        if not looks_fragment(b, low_chars):
            i += 1; continue

        # 右優先でマージ（文末句読点の尊重）
        if i+1 < len(blocks):
            nxt = blocks[i+1]
            merged = Block(b.idx, b.st, nxt.en, (b.text+"\n"+nxt.text).strip())
            # 最大尺やCPSが過大なら、左借用だけに留める
            if merged.dur <= max_dur and merged.cps <= max_cps:
                blocks[i] = merged
                del blocks[i+1]
                continue
        # 右が無理なら左と
        if i-1 >= 0:
            prv = blocks[i-1]
            merged = Block(prv.idx, prv.st, b.en, (prv.text+"\n"+b.text).strip())
            if merged.dur <= max_dur and merged.cps <= max_cps:
                blocks[i-1] = merged
                del blocks[i]
                i -= 1
                continue

        # どちらも無理 → 可能なら僅かに拡張
        if i+1 < len(blocks):
            gap = max(0.0, blocks[i+1].st - b.en)
            take = min(gap*0.5, max(0.0, min_dur - b.dur))
            if take>0: b.en += take
        if i-1 >= 0:
            gap = max(0.0, b.st - blocks[i-1].en)
            take = min(gap*0.5, max(0.0, min_dur - b.dur))
            if take>0: b.st -= take

        i += 1

    for i,b in enumerate(blocks,1): b.idx=i
    return blocks

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("-o","--output", required=True)
    ap.add_argument("--min-dur", type=float, default=1.0)
    ap.add_argument("--max-dur", type=float, default=6.0)
    ap.add_argument("--low-chars", type=int, default=6)
    ap.add_argument("--max-cps", type=float, default=19.0)
    args = ap.parse_args()

    blocks = read_srt(args.input)
    blocks = repair(blocks, args.min_dur, args.max_dur, args.low_chars, args.max_cps)
    write_srt(args.output, blocks)

if __name__ == "__main__":
    main()
