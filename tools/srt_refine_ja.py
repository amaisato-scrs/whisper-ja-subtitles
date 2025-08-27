#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JA字幕の後段整形：
1) フィラー間引き（「ね」「ですね」「よね」等。文末「です」は保持）
2) 文境界の是正（非終端で切れていれば“近接・短距離のみ”結合）
3) Sudachi があれば POS で高精度、無ければ安全なルールで近似

使い方:
  python tools/srt_refine_ja.py IN.srt -o OUT.srt [--no-merge] [--dry]
  追加オプション:
    --merge-pause 0.35   # 連結を許す最大ポーズ秒
    --merge-max 2        # 何ブロック先まで連結を許すか（上限）
"""

import re
import sys
import os
import srt
import argparse
from datetime import timedelta

# --------- 設定（安全サイド） ---------
EOS_PUNCT = "。！？!?"
KEEP_TAILS = ("です","ます","でした","ません","なります","になります")
HEAD_CONNECTIVES = ("が","けど","そして","また","まず","その","この","で")
# --------------------------------------

# Sudachi（あるなら使う）
HAVE_SUDACHI = False
try:
    from sudachipy import dictionary, tokenizer as sudachi_tokenizer
    cfg = os.environ.get("SUDACHI_CONFIG_PATH")  # 明示設定（必須ではないが推奨）
    _sudachi = dictionary.Dictionary(config_path=cfg).create()
    _SMODE = sudachi_tokenizer.Tokenizer.SplitMode.C
    HAVE_SUDACHI = True
except Exception:
    HAVE_SUDACHI = False

def _is_punct_or_eol(surf: str) -> bool:
    return surf in ("、", ",", "。", "！", "？", "!", "?")

def _strip_fillers_rule(text: str) -> str:
    """正規表現ベースの安全な近似版（Sudachiなし）"""
    t = text

    # 文中の「です(よ)?ね」→ 前後が続くなら 丸ごと削除
    # ただし直後が句読点/行末なら「です」を残し「ね」だけ落とす
    def repl_desune(m):
        before = m.group(1)
        after  = m.group(2) or ""
        if after == "" or re.match(r'^[、,。！？!?]', after):
            return "です"  # 文末様 → 「です」を保持
        return ""          # 文中様 → まるごと削除

    t = re.sub(r'です[ 　]*(?:よ)?[ 　]*(?:ね|ねー|ねぇ|ねえ)(?=([、,。！？!?]|\n|$)|(.))',
               lambda m: repl_desune(m), t)

    # 文中・独立の終助詞「ね」「よね」を削除（句読点直前の「ね」も落とす）
    t = re.sub(r'(?<!\S)(?:よね|ね|ねー|ねぇ|ねえ)(?!\S)', '', t)
    t = re.sub(r'[、,][ 　]*(?:よね|ね|ねー|ねぇ|ねえ)(?=[、,。！？!?])', lambda m: m.group(0)[0], t)

    # 連続スペース整理
    t = re.sub(r'[ 　]{2,}', ' ', t)
    return t

def _strip_fillers_sudachi(text: str) -> str:
    """Sudachi: 品詞で終助詞/フィラーを削除。『です＋ね』は look-ahead で扱う"""
    out_lines = []
    if not HAVE_SUDACHI:
        return _strip_fillers_rule(text)

    for line in text.splitlines(True):  # keepends
        if line.strip() == '':
            out_lines.append(line); continue

        toks = list(_sudachi.tokenize(line, _SMODE))
        buf = []
        i = 0
        while i < len(toks):
            surf = toks[i].surface()
            pos  = toks[i].part_of_speech()
            nxt  = toks[i+1] if i+1 < len(toks) else None
            nxt_surf = nxt.surface() if nxt else ""
            nxt_pos  = nxt.part_of_speech() if nxt else None

            # 空白はそのまま
            if pos[0] == "空白":
                buf.append(surf); i += 1; continue

            # 感動詞フィラー（えーと、あのー等）は削除
            if pos[0] == "感動詞" and pos[1] in ("フィラー","一般"):
                i += 1; continue

            # ケース: 「です + (よ)? + ね」
            if surf == "です" and nxt and nxt_pos[0] == "助詞":
                # 次が「よ」→ さらに「ね」が続くか？
                if nxt_surf == "よ" and i+2 < len(toks) and toks[i+2].surface() in ("ね","ねー","ねぇ","ねえ"):
                    # 直後が句読点/改行/行末なら「です」だけ残す。続くなら丸ごと捨てる
                    nn = toks[i+3] if i+3 < len(toks) else None
                    if nn is None or _is_punct_or_eol(nn.surface()):
                        buf.append("です")
                    # else: 丸ごと削除
                    i += 3; continue
                # 次が「ね」系
                if nxt_surf in ("ね","ねー","ねぇ","ねえ"):
                    nn = toks[i+2] if i+2 < len(toks) else None
                    if nn is None or _is_punct_or_eol(nn.surface()):
                        buf.append("です")
                    i += 2; continue

            # 単独の終助詞「ね／よね」は削除（句読点直前のものも）
            if pos[0] == "助詞" and pos[1] == "終助詞" and surf in ("ね","ねー","ねぇ","ねえ"):
                i += 1; continue
            if surf == "よ" and nxt and nxt.surface() in ("ね","ねー","ねぇ","ねえ"):
                # 「よね」セットもフィラー扱い（上のロジックで文末なら「です」保持済）
                i += 2; continue

            buf.append(surf); i += 1

        out_lines.append(''.join(buf))
    return ''.join(out_lines)

def strip_fillers(text: str) -> str:
    return _strip_fillers_sudachi(text) if HAVE_SUDACHI else _strip_fillers_rule(text)

def is_eos(text: str) -> bool:
    """文末とみなせるか：終止記号 or 終止形（です等）で終わる"""
    tt = text.rstrip()
    if not tt:
        return True
    if tt[-1] in EOS_PUNCT:
        return True
    for tail in KEEP_TAILS:
        if tt.endswith(tail):
            return True
    return False

def begins_with_connective(text: str) -> bool:
    t = text.lstrip()
    return any(t.startswith(h) for h in HEAD_CONNECTIVES)

def merge_nonfinal_blocks(subs, merge_pause=0.35, merge_max=2):
    """
    非終端で切れているブロックを“近接かつ短距離”に限定して結合。
      - 次ブロック開始が現ブロック終了＋merge_pause 以内
      - 最大 merge_max ブロックまで
      - 次が接続詞始まり or 現・次どちらかが非終端なら結合
    """
    out = []
    i = 0
    while i < len(subs):
        cur = subs[i]
        cur_text = cur.content.strip()
        merged = 0
        while (merged < merge_max) and (i + 1 < len(subs)) and not is_eos(cur_text):
            nxt = subs[i+1]
            gap = (nxt.start - cur.end).total_seconds()
            if gap > merge_pause:
                break
            if begins_with_connective(nxt.content) or not is_eos(nxt.content):
                # 結合
                cur_text = (cur_text + "\n" + nxt.content.strip()).strip()
                cur = srt.Subtitle(index=cur.index, start=cur.start, end=nxt.end, content=cur_text)
                i += 1
                merged += 1
            else:
                break
        out.append(srt.Subtitle(index=len(out)+1, start=cur.start, end=cur.end, content=cur_text))
        i += 1
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="入力SRT")
    ap.add_argument("-o", "--output", required=True, help="出力SRT")
    ap.add_argument("--no-merge", action="store_true", help="文境界の結合を行わない")
    ap.add_argument("--merge-pause", type=float, default=0.35, help="連結を許す最大ポーズ秒")
    ap.add_argument("--merge-max", type=int, default=2, help="連結上限ブロック数")
    ap.add_argument("--dry", action="store_true", help="変更件数のみ表示して書き出さない")
    args = ap.parse_args()

    raw = open(args.input, encoding="utf-8").read()
    subs = list(srt.parse(raw))

    # 1) フィラー除去（安全）
    fixed = []
    n_drop = 0
    for s in subs:
        before = s.content
        after = strip_fillers(before)
        if after != before:
            n_drop += 1
        fixed.append(srt.Subtitle(index=s.index, start=s.start, end=s.end, content=after))

    # 2) 非終端の結合（保守的条件）
    if not args.no_merge:
        fixed2 = merge_nonfinal_blocks(fixed, merge_pause=args.merge_pause, merge_max=args.merge_max)
    else:
        fixed2 = [srt.Subtitle(index=i+1, start=x.start, end=x.end, content=x.content.strip()) for i, x in enumerate(fixed)]

    if args.dry:
        print(f"[refine_ja] sudachi={'on' if HAVE_SUDACHI else 'off'} drop_or_edit_blocks={n_drop} merged={len(subs)-len(fixed2)}")
        return

    out_txt = srt.compose(fixed2)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(out_txt)
    print(f"[refine_ja] sudachi={'on' if HAVE_SUDACHI else 'off'} wrote: {args.output}  (edited={n_drop}, merged={len(subs)-len(fixed2)})")

if __name__ == "__main__":
    main()