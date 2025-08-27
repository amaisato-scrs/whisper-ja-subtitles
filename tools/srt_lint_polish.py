# /Users/sato/Scripts/Whisper/tools/srt_lint_polish.py
# v2.2: v2.1の最小尺再保証に加え、2行折返しの安全整形（禁則に配慮）を実装。
import re, sys, argparse
from dataclasses import dataclass

TIMECODE = re.compile(r"(\d\d):(\d\d):(\d\d),(\d\d\d)\s*-->\s*(\d\d):(\d\d):(\d\d),(\d\d\d)")
SENT_PUNCTS = "。！？"
WEAK_PUNCTS = "、，・…"
FORBIDDEN_SPLIT_2 = set(["ます","です","でした","なります","ください","いただき"])
NUM_UNITS_HEAD = "年月日区期"

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
    def cps(self):
        n = len(self.text.replace("\n",""))
        return n / max(1e-6, self.dur)

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

def wrap_ja(text: str, max_chars:int=40) -> str:
    """
    2行までの安全折返し。句読点優先・禁則回避。
    既存改行は無視して一旦結合→安全な位置で再分割。
    """
    raw = text.replace("\n","").strip()
    if len(raw) <= max_chars: return raw  # 1行でOK

    # 候補点を列挙（句読点を強く優先）
    candidates = []
    for i,ch in enumerate(raw):
        if ch in SENT_PUNCTS: candidates.append((i, 0))   # 強
        elif ch in WEAK_PUNCTS: candidates.append((i, 1)) # 弱
    # バックアップ候補：空白や中立文字
    for i in range(1, len(raw)-1):
        candidates.append((i, 2))

    # 禁則：直前直後の2-gramをチェック
    def bad_break(pos:int) -> bool:
        a = raw[pos-1]; b = raw[pos]  # break は pos の前で改行
        if (a+b) in FORBIDDEN_SPLIT_2: return True
        if a.isdigit() and b in NUM_UNITS_HEAD: return True
        if a == "第" and b.isdigit(): return True
        if a == "翌" and b == "日":   return True
        return False

    # 目標は中央付近
    target = len(raw)//2
    # 距離優先で最良の候補を探す（句読点に重み）
    best = None
    best_score = 1e18
    for i, kind in candidates:
        if i<=0 or i>=len(raw): continue
        if bad_break(i): continue
        # 行長の偏差 + 種別の重み
        left_len = i
        right_len = len(raw) - i
        # 片側が極端に短いのは避ける
        if min(left_len, right_len) < max(6, max_chars//5):
            continue
        base = abs(i - target)
        kind_w = {0:0.0, 1:0.5, 2:1.0}[kind]
        score = base + kind_w * (max_chars//2)
        if score < best_score:
            best_score = score; best = i

    if best is None:
        # 苦し紛れの中央割り（禁則衝突時は少しずらす）
        best = target
        shift = 0
        while (best+shift)<len(raw) and bad_break(best+shift): shift += 1
        best += shift

    return raw[:best] + "\n" + raw[best:]

def polish(blocks, lead_in, lead_out, hysteresis, min_dur, max_cps, max_chars):
    # 1) リードイン/アウト
    N=len(blocks)
    for i,b in enumerate(blocks):
        if i==0: b.st = max(0.0, b.st - lead_in)
        else:    b.st = max(blocks[i-1].en + hysteresis, b.st - lead_in)
        if i==N-1: b.en = b.en + lead_out
        else:      b.en = min(blocks[i+1].st - hysteresis, b.en + lead_out)
        if b.en < b.st:
            mid = (b.st + b.en)/2
            b.st = mid - 0.1; b.en = mid + 0.1

    # 2) オーバーラップ解消
    for i in range(1,N):
        prev, cur = blocks[i-1], blocks[i]
        if cur.st < prev.en + hysteresis:
            cur.st = prev.en + hysteresis
            if cur.en < cur.st + 0.1:
                cur.en = cur.st + 0.1

    # 3) 最小尺の再保証（借用→必要なら右マージ）
    i=0
    while i < len(blocks):
        b = blocks[i]
        if b.dur + 1e-6 >= min_dur:
            i += 1; continue
        need = min_dur - b.dur
        # 右から借用
        if i+1 < len(blocks):
            nxt = blocks[i+1]
            avail_right = max(0.0, (nxt.st - b.en) - hysteresis)
            take = min(avail_right, need)
            if take > 0: b.en += take; need -= take
        # 左から借用
        if need > 1e-9 and i-1 >= 0:
            prev = blocks[i-1]
            avail_left = max(0.0, (b.st - prev.en) - hysteresis)
            take = min(avail_left, need)
            if take > 0: b.st -= take; need -= take
        # 右とマージ
        if need > 1e-9 and i+1 < len(blocks):
            nxt = blocks[i+1]
            merged = Block(b.idx, b.st, nxt.en, (b.text+"\n"+nxt.text).strip())
            blocks[i] = merged
            del blocks[i+1]
            continue
        i += 1

    # 4) 軽いCPS調整（必要最低限）
    for i,b in enumerate(blocks):
        if b.cps > max_cps and i+1 < len(blocks):
            shift = min(0.2, (blocks[i+1].st - b.en) - hysteresis)
            if shift > 0: b.en += shift

    # 5) 行折返し（2行、禁則配慮）
    for b in blocks:
        b.text = wrap_ja(b.text, max_chars=max_chars)

    for i,b in enumerate(blocks,1): b.idx=i
    return blocks

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("-o","--output", required=True)
    ap.add_argument("--lead-in",  type=float, default=0.20)
    ap.add_argument("--lead-out", type=float, default=0.20)
    ap.add_argument("--hysteresis", type=float, default=0.02)
    ap.add_argument("--min-dur", type=float, default=1.00)
    ap.add_argument("--max-cps", type=float, default=19.0)
    ap.add_argument("--max-chars", type=int, default=40)
    args = ap.parse_args()

    blocks = read_srt(args.input)
    blocks = polish(blocks, args.lead_in, args.lead_out, args.hysteresis, args.min_dur, args.max_cps, args.max_chars)
    write_srt(args.output, blocks)

if __name__ == "__main__":
    main()
