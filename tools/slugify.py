# /Users/sato/Scripts/Whisper/tools/slugify.py
#!/usr/bin/env python3
import sys, re, unicodedata, datetime

def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).lower()
    s = re.sub(r"[^A-Za-z0-9_.-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        s = "file_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return s

if __name__ == "__main__":
    raw = sys.argv[1] if len(sys.argv) > 1 else ""
    print(slugify(raw))
