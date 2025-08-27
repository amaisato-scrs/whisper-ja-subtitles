# /Users/sato/Scripts/Whisper/tools/srt_qc_ja.py
# 禁則境界（ございま|す, 9|月, 10|日 等）がブロック間に残っていないかをレポート。
import re, sys

def parse(path):
    with open(path, "r", encoding="utf-8") as f:
        blocks=[]
        idx=None; span=None; txt=[]
        for line in f:
            line=line.rstrip("\n")
            if line.isdigit():
                idx=int(line); span=None; txt=[]
            elif " --> " in line:
                span=line
            elif line=="":
                if idx is not None:
                    blocks.append(("".join(txt), span))
                idx=None; span=None; txt=[]
            else:
                txt.append(line)
        if idx is not None:
            blocks.append(("".join(txt), span))
    return blocks

pairs = set(["ます","です","でした","なります","ください","いただき","翌日","第2","2期","9月","10日","23区","納付","納期"])
units = "年月日区期"

def bad_pair(a,b):
    if a+b in pairs: return True
    if a.isdigit() and b in units: return True
    if a=="第" and b.isdigit(): return True
    if a=="翌" and b=="日": return True
    return False

def main(p):
    blocks = parse(p)
    bad=0
    for i in range(len(blocks)-1):
        ta,_ = blocks[i]
        tb,_ = blocks[i+1]
        if not ta or not tb: continue
        a = ta[-1]; b = tb[0]
        if bad_pair(a,b):
            bad+=1
            print(f"[BAD] …{a} | {b}…  at boundary #{i+1}/#{i+2}")
    print(f"Checked {len(blocks)} blocks. Forbidden boundary count = {bad}")

if __name__ == "__main__":
    main(sys.argv[1])
