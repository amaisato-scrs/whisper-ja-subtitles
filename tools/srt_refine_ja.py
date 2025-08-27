#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JA字幕の後段整形：
1) フィラー間引き（「ね」「ですね」等。文末「です」は保持）
2) 文境界の是正（非終端で切れていれば後続と結合）
3) Sudachi があれば POS で高精度、無ければ安全なルールで近似

使い方:
  python tools/srt_refine_ja.py IN.srt -o OUT.srt [--no-merge] [--dry]
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
HEAD_CONNECTIVES = ("ね","よ","が","けど","そして","また","まず","その","この","で")
# --------------------------------------

# Sudachiの有無を自動検出（あれば高精度で）: 環境変数 SUDACHI_CONFIG_PATH を尊重
HAVE_SUDACHI = False
try:
    from sudachipy import dictionary, tokenizer as sudachi_tokenizer
    cfg = os.environ.get("SUDACHI_CONFIG_PATH")  # env で明示
    _sudachi = dictionary.Dictionary(config_path=cfg).create()
    _SMODE = sudachi_tokenizer.Tokenizer.SplitMode.C
    HAVE_SUDACHI = True
except Exception:
    HAVE_SUDACHI = False

def _strip_fillers_rule(text: str) -> str:
    """正規表現ベースの安全なフィラー除去（Sudachiなし）"""
    t = text

    # 1) 「です(よ)?ね」→「です」 （句読点・改行直前のみ）
    t = re.sub(r'(です)[ 　]*(?:よ)?[ 　]*(?:ね|ねー|ねぇ|ねえ)(?=(?:$|\n|[、,。！？!?]))',
               r'\1', t, flags=re.MULTILINE)

    # 1b) 文中の「です(よ)?ね」は丸ごと削除（「9月のです 税務…」を防ぐ）
    t = re.sub(r'です[ 　]*(?:よ)?[ 　]*ね(?![、,。！？!?]|\s*$)', '', t)

    # 2) 文頭の「ね」系を除去
    t = re.sub(r'(^|\n)[ 　]*(?:ね|ねー|ねぇ|ねえ)[ 　]*(?=[^\n])', r'\1', t)

    # 3) 「(ます/でした/…)+ (よ)? +ね」→ tail を保持して「ね」を削除（句読点・改行直前のみ）
    tails_cap = r'(' + '|'.join(map(re.escape, KEEP_TAILS)) + r')'
    t = re.sub(tails_cap + r'[ 　]*(?:よ)?[ 　]*(?:ね|ねー|ねぇ|ねえ)(?=(?:$|\n|[、,。！？!?]))',
               r'\1', t, flags=re.MULTILINE)

    # 4) 「、ね、」「、ね。」 の「ね」だけ除去（句読点は維持）
    t = re.sub(r'([、,])[ 　]*(?:ね|ねー|ねぇ|ねえ)(?=[、,。！？!?])', r'\1', t)

    # 5) 行中の独立「ね」を基本削除（空白で独立している場合）
    t = re.sub(r'(?<!\S)(?:ね|ねー|ねぇ|ねえ)(?!\S)', '', t)

    # 後始末：二重スペース等の縮約
    t = re.sub(r'[ 　]{2,}', ' ', t)
    return t

def _strip_fillers_sudachi(text: str) -> str:
    """Sudachiで品詞を見て「終助詞/フィラー」だけを落とす。「です」は保持。
       ただし「です(よ)?ね」は位置に応じて扱いを変える：
         - 句読点/行末直前なら「です」に縮約
         - 文中なら「です(よ)?ね」を丸ごと削除
    """
    if not HAVE_SUDACHI:
        return _strip_fillers_rule(text)

    def is_space(tok):
        try:
            return tok.part_of_speech()[0] == "空白" or tok.surface().isspace()
        except Exception:
            return tok.surface().isspace()

    def is_punct(tok):
        pos = tok.part_of_speech()
        return pos[0] == "補助記号"

    def is_end_particle(tok, allow=("ね","ねー","ねぇ","ねえ","よ")):
        pos = tok.part_of_speech()
        return pos[0] == "助詞" and pos[1] == "終助詞" and tok.surface() in allow

    out_lines = []
    for line in text.splitlines(True):  # keepends
        if line.strip() == '':
            out_lines.append(line)
            continue
        toks = list(_sudachi.tokenize(line, _SMODE))
        N = len(toks)
        i = 0
        buf = []

        def next_nonspace(j):
            while j < N and is_space(toks[j]):
                j += 1
            return j

        while i < N:
            tok = toks[i]
            surf = tok.surface()
            pos = tok.part_of_speech()

            # 「です(よ)?ね」処理
            if surf == "です":
                j = next_nonspace(i + 1)
                # optional 「よ」
                if j < N and is_end_particle(toks[j], allow=("よ",)):
                    j = next_nonspace(j + 1)
                # 「ね」
                if j < N and is_end_particle(toks[j], allow=("ね","ねー","ねぇ","ねえ")):
                    k = next_nonspace(j + 1)
                    # 句読点 or 行末 なら「です」に縮約
                    if k >= N or (k < N and is_punct(toks[k])):
                        buf.append("です")
                        i = j + 1
                        continue
                    # 文中なら「です(よ)?ね」を丸ごと削除
                    else:
                        i = j + 1
                        continue
                # ふつうの「です」は保持
                buf.append("です")
                i += 1
                continue

            # 単体の終助詞「ね」は落とす（文中フィラー）
            if pos[0] == "助詞" and pos[1] == "終助詞" and surf in ("ね","ねー","ねぇ","ねえ"):
                i += 1
                continue

            # 感動詞フィラーは落とす（えー、えっと、あの 等）
            if pos[0] == "感動詞" and (pos[1] == "フィラー"):
                i += 1
                continue

            # それ以外は保持（「よ」は triad 以外は保持）
            buf.append(surf)
            i += 1

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

def merge_nonfinal_blocks(subs):
    """非終端で切れているブロックを後続と結合。時間は連結、連番は後で振り直し。"""
    out = []
    i = 0
    while i < len(subs):
        cur = subs[i]
        cur_text = cur.content
        while i + 1 < len(subs) and not is_eos(cur_text):
            nxt = subs[i+1]
            if begins_with_connective(nxt.content) or not is_eos(nxt.content):
                cur_text = (cur_text + "\n" + nxt.content).strip()
                cur = srt.Subtitle(index=cur.index, start=cur.start, end=nxt.end, content=cur_text)
                i += 1
            else:
                break
        out.append(cur)
        i += 1
    for k, s in enumerate(out, 1):
        s.index = k
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="入力SRT")
    ap.add_argument("-o", "--output", required=True, help="出力SRT")
    ap.add_argument("--no-merge", action="store_true", help="文境界の結合を行わない")
    ap.add_argument("--dry", action="store_true", help="変更件数のみ表示して書き出さない")
    args = ap.parse_args()

    raw = open(args.input, encoding="utf-8").read()
    subs = list(srt.parse(raw))

    # 1) フィラー除去
    fixed = []
    n_drop = 0
    for s in subs:
        before = s.content
        after = strip_fillers(before)
        if after != before:
            n_drop += 1
        fixed.append(srt.Subtitle(index=s.index, start=s.start, end=s.end, content=after))

    # 2) 非終端の結合（必要に応じて無効化可）
    if not args.no_merge:
        fixed2 = merge_nonfinal_blocks(fixed)
    else:
        fixed2 = fixed

    if args.dry:
        print(f"[refine_ja] sudachi={'on' if HAVE_SUDACHI else 'off'} drop_or_edit_blocks={n_drop} merged={len(subs)-len(fixed2)}")
        return

    out_txt = srt.compose(fixed2)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(out_txt)
    print(f"[refine_ja] sudachi={'on' if HAVE_SUDACHI else 'off'} wrote: {args.output}  (edited={n_drop}, merged={len(subs)-len(fixed2)})")

if __name__ == "__main__":
    main()