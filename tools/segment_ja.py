# /Users/sato/Scripts/Whisper/tools/segment_ja.py
# v2.2: 禁則カット（ます/です/でした/になります等、数詞+単位）を導入。
#       min_dur未満しか作れないときは切らずに窓を伸ばす（フェイルセーフ）。
import json, re, sys, argparse
from dataclasses import dataclass

SENT_PUNCTS = "。！？"
WEAK_PUNCTS = "、，・…"
ALL_PUNCTS  = SENT_PUNCTS + WEAK_PUNCTS + "（）「」『』［］【】"

# 末尾と先頭の「ここで切るな」禁則（2-gram / 3-gram）
NO_SPLIT_2GRAM = set([
    "ます","です","たい","だい","ない","では","には","には","とは","とは","まで","より",
    "翌日","翌々","第2","2期","9月","10日","23区","納付","納期","中間","予定"
])
# 3-gramは主要だけ
NO_SPLIT_3GRAM = set([
    "でした","なります","いただき","してい","されま","ましょ","ください"
])

NUM_UNITS_HEAD = "年月日区期"  # 数字 + 単位の分割抑止（例: 10日, 9月, 23区, 第2期）

@dataclass
class Tok:
    t: str
    st: float
    en: float

def load_aligned(path):
    with open(path, "r", encoding="utf-8") as f:
        js = json.load(f)
    toks=[]
    for seg in js.get("segments", []):
        for w in seg.get("words", []):
            if not isinstance(w.get("start"), (int,float)) or not isinstance(w.get("end"), (int,float)):
                continue
            # WhisperXのtokenは1文字相当の場合が多い
            toks.append(Tok(str(w["word"]), float(w["start"]), float(w["end"])))
    toks.sort(key=lambda x: x.st)
    return toks

def gap_after(toks, k):
    if k+1 >= len(toks): return 1e9
    return max(0.0, toks[k+1].st - toks[k].en)

def join_txt(toks, i, j):
    return "".join(t.t for t in toks[i:j])

def cps_len(txt): return len(txt.replace("\n",""))

def forbidden_boundary(left_txt: str, right_txt: str) -> bool:
    """
    左の末尾と右の先頭で、禁則（語尾/数詞+単位 等）に該当するかを判定
    """
    if not left_txt or not right_txt: return False
    a = left_txt[-1]
    b = right_txt[:1]
    ab = a + b
    # 2-gram禁則
    if ab in NO_SPLIT_2GRAM: return True

    # 3-gram禁則（左末尾2 + 右先頭1）
    if len(left_txt) >= 2:
        ab3 = left_txt[-2:] + b
        if ab3 in NO_SPLIT_3GRAM: return True

    # 数字 + 単位（例: 10|日, 9|月, 23|区）
    if a.isdigit() and b in NUM_UNITS_HEAD:
        return True
    # 「第」+ 数字、「翌」+「日」
    if a == "第" and b.isdigit(): return True
    if a == "翌" and b == "日":   return True

    return False

def segment(toks, min_dur, max_dur, pause_strong, pause_weak, target_cps, max_chars):
    N=len(toks); out=[]
    i=0
    while i < N:
        j=i+1
        while j <= N:
            txt = join_txt(toks, i, j)
            dur = toks[j-1].en - toks[i].st
            need_cut = False
            if dur >= max_dur: need_cut = True
            if cps_len(txt) > max_chars: need_cut = True
            # 強ポーズ（ある程度の長さがあるときのみ）
            if dur >= min_dur and gap_after(toks, j-1) >= pause_strong and cps_len(txt) >= max(10, max_chars//3):
                need_cut = True

            if not need_cut and j < N:
                j += 1; continue

            # 候補選定：句読点/強弱ポーズを優先。ただし禁則境界は候補から除外。
            best_pos, best_score = -1, 1e18
            k0, k1 = i+1, j  # 先頭直後の極端な早切りは抑制（i+1から）
            for k in range(k0, k1):
                prev = toks[k-1]; cur = toks[k]
                left_txt  = join_txt(toks, i, k)
                right_txt = join_txt(toks, k, j)

                # 禁則：ここでは絶対に切らない
                if forbidden_boundary(left_txt, right_txt):
                    continue

                g = max(0.0, cur.st - prev.en)
                d = prev.en - toks[i].st
                if d < min_dur - 1e-6:
                    continue  # min_dur未満は候補外

                bonus = 0.0
                if len(left_txt)>0 and (left_txt[-1] in SENT_PUNCTS): bonus -= 0.6
                elif len(left_txt)>0 and (left_txt[-1] in WEAK_PUNCTS): bonus -= 0.3
                if g >= pause_strong: bonus -= 0.5
                elif g >= pause_weak: bonus -= 0.2

                cps = cps_len(left_txt) / max(1e-6, d)
                cps_cost = abs(cps - target_cps)*0.02
                len_cost = abs(cps_len(left_txt) - max_chars*0.6)*0.005
                score = cps_cost + len_cost + bonus
                if score < best_score:
                    best_score = score; best_pos = k

            if best_pos < 0:
                # 合理的候補が無い → 窓を伸ばす（フェイルセーフ）
                if j < N:
                    j += 1; continue
                else:
                    best_pos = j  # 末端

            out.append((toks[i].st, toks[best_pos-1].en, join_txt(toks, i, best_pos)))
            i = best_pos
            break
    return out

def s2t(x):
    x = max(0.0, x)
    h=int(x//3600); x-=h*3600
    m=int(x//60);   x-=m*60
    s=int(x);       ms=int(round((x-s)*1000))
    if ms==1000: s+=1; ms=0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def write_srt(path, blocks):
    with open(path, "w", encoding="utf-8") as f:
        for n,(st,en,txt) in enumerate(blocks,1):
            f.write(f"{n}\n{s2t(st)} --> {s2t(en)}\n{txt}\n\n")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("aligned_json")
    ap.add_argument("-o","--output", required=True)
    ap.add_argument("--min-dur", type=float, default=1.0)
    ap.add_argument("--max-dur", type=float, default=6.0)
    ap.add_argument("--pause-strong", type=float, default=0.35)
    ap.add_argument("--pause-weak",   type=float, default=0.25)
    ap.add_argument("--target-cps",   type=float, default=15.0)
    ap.add_argument("--max-chars",    type=int,   default=40)
    args=ap.parse_args()

    toks = load_aligned(args.aligned_json)
    blocks = segment(toks, args.min_dur, args.max_dur,
                     args.pause_strong, args.pause_weak,
                     args.target_cps, args.max_chars)
    write_srt(args.output, blocks)

if __name__ == "__main__":
    main()
