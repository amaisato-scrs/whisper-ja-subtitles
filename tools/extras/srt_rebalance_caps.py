# /Users/sato/Scripts/Whisper/tools/srt_rebalance_caps.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
長すぎるSRTブロックを、読みやすい境界で再分割し、
- JA_MAX_DUR（デフォ 6.0s）上限
- TARGET_CPS（デフォ 15.0 cps）の1.3倍上限
を満たすようにリバランスする後処理。

設計方針
- 付属語ヘッド（ます/です/なります…）が新ブロック頭に来ないように禁止。
- 句読点（。！？…、）や談話標識（まず/そして/それでは/今回は/こちらは/なお/次に/また）を優先分割点に。
- どうしても候補がない場合のみ、文字比率に応じた時間按分で分割（安全fallback）。
- 2行化などの体裁は後段の srt_lint_polish.py に委譲。
"""

import sys, math, re
import srt
from datetime import timedelta

# 既定パラメータ（configと揃える）
JA_MAX_DUR = 6.0
JA_MIN_DUR = 1.0
TARGET_CPS = 15.0
CPS_SLACK = 1.3  # TARGET_CPS * 1.3 まで許容

SUFFIX_HEADS = (
    "ます","です","でした","ません",
    "なります","になります",
    "ください",
    "いたします","いたしました",
    "いただき","いただけ","いただけます",
    "できます","ましょう",
)
TAILS = ("です","ます","でした","ません")
PARTICLE_HEADS = ("ね","よ","が","けど")

# 談話標識：分割「前」に置く（= 右ブロックを談話標識で開始してOK）
DISCOURSE_TOKENS = (
    "そして","まず","それでは","はいそれでは",
    "今回は","こちらは","なお","次に","また",
)

RE_PUNCT_STRONG = re.compile(r"[。！？…]+")
RE_PUNCT_WEAK   = re.compile(r"[、，]")
RE_TOKEN        = re.compile("|".join(map(re.escape, DISCOURSE_TOKENS)))
# 「…ます/です/なります」などの直後で切りたいケースも拾う
RE_AFTER_TAIL   = re.compile(
    r"(ます|です|でした|ません|なります|になります|できます|ください|いたします|いたしました)"
    r"(?=(?:[、，。！？…]|そして|が|けど|けれども|ね|よ))"
)

def _right_startswith_suffix_head(s: str) -> bool:
    s = s.lstrip()
    return any(s.startswith(h) for h in SUFFIX_HEADS)

def _is_desu_masu_plus_particle(left: str, right: str) -> bool:
    lt = left.rstrip()
    rt = right.lstrip()
    return lt.endswith(TAILS) and any(rt.startswith(p) for p in PARTICLE_HEADS)

def forbidden_boundary(left_text: str, right_text: str) -> bool:
    # 新しい境界としてNG
    if _right_startswith_suffix_head(right_text):
        # 左が句点終端なら文替わりとして許容
        if left_text and left_text[-1] in "。！？…」』）】":
            pass
        else:
            return True
    if _is_desu_masu_plus_particle(left_text, right_text):
        return True
    return False

def duration_s(sub):
    return (sub.end - sub.start).total_seconds()

def cps(sub):
    dur = max(duration_s(sub), 1e-6)
    # 改行や空白は一旦含める（後段polishで整える前提）
    n = len(sub.content.replace("\n",""))
    return n / dur

def candidate_indices(text: str):
    """
    分割候補の文字オフセット（0<idx<len）を返す。
    優先：強い句読点 > 弱い句読点 > 談話標識頭 > 付属語末尾直後
    """
    cands = []

    # 強い句読点の直後
    for m in RE_PUNCT_STRONG.finditer(text):
        cands.append(m.end())

    # 弱い句読点の直後
    for m in RE_PUNCT_WEAK.finditer(text):
        cands.append(m.end())

    # 談話標識の直前（= 右ブロックが談話標識で始まる）
    for m in RE_TOKEN.finditer(text):
        if m.start() > 0:
            cands.append(m.start())

    # 付属語末尾の直後（ます/です 等の直後）
    for m in RE_AFTER_TAIL.finditer(text):
        cands.append(m.end())

    # 範囲内 & 重複除去 & 昇順
    cands = sorted({idx for idx in cands if 0 < idx < len(text)})
    return cands

def choose_boundaries(text: str, parts: int):
    """
    文字長に基づく目標位置に最も近い候補を順に選ぶ。
    禁止境界は避け、どうしても無ければ最も近い候補を許容。
    """
    if parts <= 1:
        return []
    cands = candidate_indices(text)
    bounds = []
    last = 0
    for i in range(1, parts):
        target = round(len(text) * i / parts)
        # 候補から未使用で target に近いものを探索
        best = None
        best_cost = 10**9
        for idx in cands:
            if idx <= last or idx in bounds:
                continue
            left = text[:idx]
            right = text[idx:]
            bad = forbidden_boundary(left, right)
            # コスト：距離 + 禁止ペナルティ
            cost = abs(idx - target) + (10000 if bad else 0)
            if cost < best_cost:
                best = idx
                best_cost = cost
        if best is None:
            break
        bounds.append(best)
        last = best
    return bounds

def split_by_bounds(sub, bounds):
    """
    文字境界に沿ってブロックを分割。時間は文字比率で按分。
    """
    if not bounds:
        return [sub]

    text = sub.content
    pieces = []
    start = sub.start
    total = len(text)
    last = 0

    for idx in bounds + [len(text)]:
        seg_text = text[last:idx]
        pieces.append(seg_text)
        last = idx

    # 時間按分
    dur = (sub.end - sub.start).total_seconds()
    lens = [len(p) for p in pieces]
    s = max(sum(lens), 1)
    secs = [dur * (l / s) for l in lens]

    # 最小1.0s未満が出たら隣へ寄せる（単純補正）
    for k in range(len(secs)):
        if secs[k] < JA_MIN_DUR and len(secs) > 1:
            if k < len(secs) - 1:
                secs[k+1] += secs[k]; secs[k] = 0.0
            else:
                secs[k-1] += secs[k]; secs[k] = 0.0
    secs = [x for x in secs if x > 0.0]
    pieces = [p for p,l in zip(pieces, lens) if l>0]

    # SRT組み立て
    out = []
    cur = start
    for p,sec in zip(pieces, secs):
        end = cur + timedelta(seconds=sec)
        out.append(srt.Subtitle(index=0, start=cur, end=end, content=p))
        cur = end
    # 端数調整：最後のendを元のendに合わせる
    if out:
        out[-1].end = sub.end
    return out

def need_split(sub):
    return (duration_s(sub) > JA_MAX_DUR) or (cps(sub) > TARGET_CPS * CPS_SLACK)

def rebalance(sub):
    """
    上限制御を満たすまで分割を繰り返す。
    """
    work = [sub]
    changed = False
    i = 0
    while i < len(work):
        s0 = work[i]
        if need_split(s0):
            # 何分割にするか：時間に基づく
            parts = max(2, math.ceil(duration_s(s0) / JA_MAX_DUR))
            bounds = choose_boundaries(s0.content, parts)
            parts_list = split_by_bounds(s0, bounds)
            if len(parts_list) > 1:
                work = work[:i] + parts_list + work[i+1:]
                changed = True
                # i据え置き（新しい先頭から再評価）
                continue
        i += 1
    return work, changed

def process(subs):
    out = []
    for s in subs:
        pieces, _ = rebalance(s)
        out.extend(pieces)
    # 連番ふり直し
    for i, it in enumerate(out, 1):
        it.index = i
    return out

def main():
    if len(sys.argv) < 3:
        print("Usage: python tools/srt_rebalance_caps.py <in.srt> <out.srt> [max_dur_sec]")
        sys.exit(2)
    src, dst = sys.argv[1], sys.argv[2]
    if len(sys.argv) >= 4:
        global JA_MAX_DUR
        JA_MAX_DUR = float(sys.argv[3])

    with open(src, "r", encoding="utf-8") as f:
        txt = f.read()
    subs = list(srt.parse(txt))
    before = len(subs)
    out = process(subs)
    after = len(out)

    with open(dst, "w", encoding="utf-8") as f:
        f.write(srt.compose(out))
    print(f"[rebalance] blocks: {before} -> {after}, max_dur={JA_MAX_DUR}s, TARGET_CPS={TARGET_CPS} (x{CPS_SLACK})")
    # ざっくり統計
    overs = [s for s in out if duration_s(s) > JA_MAX_DUR + 1e-6]
    if overs:
        print(f"[warn] {len(overs)} blocks still exceed max_dur (kept to preserve linguistic safety).")

if __name__ == "__main__":
    main()
