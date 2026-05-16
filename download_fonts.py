"""
Download Noto Sans Devanagari font for Hindi/Sanskrit rendering.
Run once: python download_fonts.py
"""
import urllib.request, os, zipfile

FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
os.makedirs(FONTS_DIR, exist_ok=True)

FONT_URL = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf"
FONT_BOLD_URL = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Bold.ttf"
SERIF_URL = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSerifDevanagari/NotoSerifDevanagari-Regular.ttf"
SERIF_BOLD_URL = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSerifDevanagari/NotoSerifDevanagari-Bold.ttf"

headers = {"User-Agent": "Mozilla/5.0"}

for url, name in [
    (FONT_URL, "NotoSansDevanagari-Regular.ttf"),
    (FONT_BOLD_URL, "NotoSansDevanagari-Bold.ttf"),
    (SERIF_URL, "NotoSerifDevanagari-Regular.ttf"),
    (SERIF_BOLD_URL, "NotoSerifDevanagari-Bold.ttf"),
]:
    path = os.path.join(FONTS_DIR, name)
    if os.path.exists(path):
        print(f"  Already exists: {name}")
        continue
    print(f"  Downloading {name}...")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r, open(path, "wb") as f:
            f.write(r.read())
        print(f"  [✓] Saved: {name} ({os.path.getsize(path)//1024}KB)")
    except Exception as e:
        print(f"  [!] Failed: {e}")

print("\nDone. Fonts saved in gita-daily-bot/fonts/")
