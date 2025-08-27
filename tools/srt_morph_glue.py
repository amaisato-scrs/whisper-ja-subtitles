# /Users/sato/Scripts/Whisper/tools/srt_morph_glue.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
付属語ヘッド（ます/です/なります…）や「です｜ね」等の境界を自動で縫合して
読みやすさを改善する後処理ツール。時間は左のstart〜右のendで結合。
- 右ブロックが「ます/です/なります…」などで始まる場合に前ブロックと結合
- 左が「です/ます/でした/ません」で終わり右が「ね/よ/が/けど」開始も結合
- 行頭の付属語ヘッドを作らないため、結合時は改行ではなく “直結” します
"""

import sys
import srt

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


def _right_startswith_suffix_head(s: str) -> bool:
    s = s.lstrip()
    return any(s.startswith(h) for h in SUFFIX_HEADS)


def _is_desu_masu_plus_particle(left: str, right: str) -> bool:
    lt = left.rstrip()
    rt = right.lstrip()
    return lt.endswith(TAILS) and any(rt.startswith(p) for p in PARTICLE_HEADS)


def should_glue(left_text: str, right_text: str) -> bool:
    # 1) 右が付属語ヘッドで始まる（ただし左が句読点終端なら文替わりとみなし許容）
    if _right_startswith_suffix_head(right_text):
        if left_text and left_text[-1] in "。！？…」』）】":
            return False
        return True
    # 2) 「…です/ます」+ 「ね/よ/が/けど」の分断も結合
    if _is_desu_masu_plus_particle(left_text, right_text):
        return True
    return False


def _compose_join(a: str, b: str) -> str:
    """
    改行を入れずに直結して、付属語ヘッドが行頭に来るのを防止。
    """
    left = a.rstrip()
    right = b.lstrip()
    return left + right


def glue_once(items):
    out = []
    i = 0
    changed = False
    n = len(items)
    while i < n:
        cur = items[i]
        if i < n - 1:
            nxt = items[i + 1]
            if should_glue(cur.content, nxt.content):
                merged = srt.Subtitle(
                    index=cur.index,
                    start=cur.start,
                    end=nxt.end,
                    content=_compose_join(cur.content, nxt.content),
                    proprietary=cur.proprietary,
                )
                # 次項にマージして、その位置で評価を続ける
                items[i + 1] = merged
                changed = True
                i += 1
                continue
        out.append(cur)
        i += 1
    return out, changed


def glue(items):
    # 収束するまで繰り返し
    work = list(items)
    while True:
        work, changed = glue_once(work)
        if not changed:
            break
    # 連番ふり直し
    for idx, sub in enumerate(work, start=1):
        sub.index = idx
    return work


def main():
    if len(sys.argv) < 3:
        print("Usage: python tools/srt_morph_glue.py <in.srt> <out.srt>")
        sys.exit(2)
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, "r", encoding="utf-8") as f:
        txt = f.read()
    items = list(srt.parse(txt))
    glued = glue(items)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(srt.compose(glued))
    print(f"[glue] {len(items)} -> {len(glued)} blocks (wrote {dst})")


if __name__ == "__main__":
    main()
