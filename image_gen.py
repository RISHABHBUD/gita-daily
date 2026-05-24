"""
Gita Daily Bot — Image Post Generator
1080x1080 spiritual aesthetic with saffron/gold theme.
"""

import re, math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops
from datetime import datetime
from config import (PAGE_NAME, PAGE_HANDLE,
                    C_BG_TOP, C_BG_BOT, C_SAFFRON, C_GOLD,
                    C_LOTUS, C_WHITE, C_MUTED, C_PANEL, C_ACCENT)
from font_helper import raqm_text_kwargs
import devanagari_shaper as dvs

W, H = 1080, 1080


def font(size, bold=False, devanagari=False, hindi_prose=False):
    from font_helper import devanagari_search_paths, truetype_compat, raqm_text_kwargs

    if devanagari:
        for p in devanagari_search_paths(bold=bold, prefer_serif_for_hindi=hindi_prose):
            if not os.path.isfile(p):
                continue
            try:
                return truetype_compat(p, size)
            except OSError:
                continue
        return ImageFont.load_default()
    candidates = (
        ["arialbd.ttf", "Arial_Bold.ttf", "DejaVuSans-Bold.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
        if bold else
        ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    )
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    return ImageFont.load_default()


def tw(d, txt, f, language=None):
    kw = raqm_text_kwargs(language=language)
    b = d.textbbox((0, 0), txt, font=f, **kw)
    return b[2] - b[0]


def cx(d, txt, f, w=W, language=None):
    return (w - tw(d, txt, f, language=language)) // 2


def lerp_col(c1, c2, t):
    return tuple(int(c1[i]+(c2[i]-c1[i])*t) for i in range(3))


def make_canvas():
    """Spiritual gradient background with subtle texture."""
    arr = np.zeros((H, W, 3), dtype=np.uint8)
    for y in range(H):
        arr[y] = lerp_col(C_BG_TOP, C_BG_BOT, y/H)
    img = Image.fromarray(arr)
    d   = ImageDraw.Draw(img)
    # Subtle diagonal lines for texture
    for i in range(0, W+H, 80):
        d.line([(i,0),(0,i)], fill=(255,140,0,8), width=1)
    # Film grain
    rng   = np.random.default_rng(42)
    noise = rng.integers(0,12,size=(H,W),dtype=np.uint8)
    layer = Image.fromarray(noise,"L").convert("RGB")
    img   = ImageChops.screen(img, layer)
    return img


def soft_glow(img, x, y, radius, color):
    ov = Image.new("RGBA", img.size, (0,0,0,0))
    od = ImageDraw.Draw(ov)
    for r in range(6,0,-1):
        rr=radius+(6-r)*20; a=int(55*r/6)
        od.ellipse([x-rr,y-rr,x+rr,y+rr], fill=(*color,a))
    return Image.alpha_composite(img.convert("RGBA"),ov).convert("RGB")


def glow_text(img, txt, f, x, y, color, glow, language=None):
    tkw = raqm_text_kwargs(language=language)
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for r in [6, 4, 2]:
        od.text((x, y), txt, font=f, fill=(*glow, 70 // max(1, r // 2)), **tkw)
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    ImageDraw.Draw(img).text((x, y), txt, font=f, fill=color, **tkw)
    return img


def wrap_text(d, text, f, max_w, language=None):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if tw(d, test, f, language=language) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def wrap_devanagari(text, font_path, font_px, max_w):
    """
    Wrap Devanagari text using HarfBuzz when available.
    PIL without Raqm over-measures Devanagari words by 15-35%, causing
    wrong line breaks. Always use this for Sanskrit and Hindi.
    """
    if dvs.is_available():
        return dvs.wrap_lines(text, font_path, font_px, max_w)
    f = font(font_px, False, devanagari=True)
    d_tmp = ImageDraw.Draw(Image.new("RGB", (max_w + 100, 100)))
    return wrap_text(d_tmp, text, f, max_w)


def cx_devanagari(text, font_path, font_px, w=W):
    """
    Compute centered x for Devanagari text using HarfBuzz shaped width.
    PIL textbbox without Raqm gives ~15-35% too-large widths for Devanagari.
    """
    if dvs.is_available():
        return (w - dvs.line_width_px(font_path, font_px, text)) // 2
    f = font(font_px, False, devanagari=True)
    d_tmp = ImageDraw.Draw(Image.new("RGB", (w + 100, 100)))
    return cx(d_tmp, text, f)


def draw_om_symbol(d, x, y, size, color, alpha=60):
    """Draw a simple Om-like decorative circle."""
    ov = Image.new("RGBA", (W,H), (0,0,0,0))
    od = ImageDraw.Draw(ov)
    od.ellipse([x-size, y-size, x+size, y+size],
               outline=(*color, alpha), width=3)
    od.ellipse([x-size//2, y-size//2, x+size//2, y+size//2],
               outline=(*color, alpha//2), width=2)
    return ov


def create_post_image(shloka, output_path, day_number=1):
    """
    Generate a 1080x1080 shloka image post.
    Layout:
      - Top: chapter/verse badge + day counter
      - Center: Sanskrit shloka (large, glowing)
      - Below: Hindi meaning
      - Bottom: English lesson + brand footer
    """
    img = make_canvas()
    img = soft_glow(img, W//2, H//2, 320, C_SAFFRON)
    d   = ImageDraw.Draw(img)

    # Decorative Om circles in corners
    for ov in [draw_om_symbol(d, 80, 80, 60, C_GOLD),
               draw_om_symbol(d, W-80, 80, 60, C_GOLD),
               draw_om_symbol(d, 80, H-80, 60, C_GOLD),
               draw_om_symbol(d, W-80, H-80, 60, C_GOLD)]:
        img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
        d   = ImageDraw.Draw(img)

    # ── Top section ────────────────────────────────────────────
    # Chapter + verse badge
    ch_txt = f"Chapter {shloka['chapter']}  •  Verse {shloka['verse']}"
    cf     = font(26, True)
    cw_    = tw(d,ch_txt,cf)+48
    bx     = (W-cw_)//2
    d.rounded_rectangle([bx,38,bx+cw_,88], radius=25, fill=C_PANEL)
    d.rectangle([bx,38,bx+cw_,44], fill=C_SAFFRON)
    d.text((bx+24,50), ch_txt, font=cf, fill=C_SAFFRON)

    # Day counter top-right
    day_txt = f"Day {day_number}"
    df      = font(24)
    d.text((W-tw(d,day_txt,df)-40, 48), day_txt, font=df, fill=C_MUTED)

    # Gold divider
    d.rectangle([60, 100, W-60, 103], fill=(*C_GOLD, 100))

    # ── Sanskrit shloka — centered, glowing ───────────────────
    sanskrit = shloka["sanskrit"]
    import re as _re
    def _clean(t):
        t = _re.sub(r'[।|]{2}\s*\d+\.\d+\s*[।|]{2}','',t)
        t = _re.sub(r'\|\|\s*\d+[-\.]\d+\s*\|\|','',t)
        t = _re.sub(r'^\s*\d+\.\s*\d*\.?\s*','',t)
        return t.strip()
    sanskrit = _clean(sanskrit)
    hb_path = dvs.first_font_path(True) if dvs.is_available() else None
    for fsize in [52, 44, 38, 34, 30]:
        sf = font(fsize, True, devanagari=True, hindi_prose=False)
        lines = wrap_devanagari(sanskrit, hb_path or "", fsize, W - 80) if hb_path else wrap_text(d, sanskrit, sf, W - 80, language="sa")
        if len(lines) * (fsize + 16) <= 280:
            break

    lh = sf.size + 16
    sy = 130
    for line in lines:
        if hb_path:
            # Glow layer: saffron at low alpha
            img = dvs.composite_line_centered(img, sy, line, hb_path, fsize, C_SAFFRON, 60, canvas_w=W)
            # Main text: gold at full alpha
            img = dvs.composite_line_centered(img, sy, line, hb_path, fsize, C_GOLD, 255, canvas_w=W)
        else:
            x = cx(d, line, sf, language="sa")
            img = glow_text(img, line, sf, x, sy, C_GOLD, C_SAFFRON, language="sa")
        d = ImageDraw.Draw(img)
        sy += lh

    # Transliteration — Latin font (no devanagari)
    trans = shloka.get("transliteration","")
    if trans:
        tf  = font(24)  # Latin font
        for line in wrap_text(d, trans, tf, W-100)[:2]:
            d.text((cx(d,line,tf), sy), line, font=tf, fill=C_MUTED)
            sy += 34

    # Thin divider
    d.rectangle([80, sy+12, W-80, sy+15], fill=(*C_SAFFRON, 80))
    sy += 28

    # ── Hindi meaning — HarfBuzz path when uharfbuzz is installed ──
    hindi = shloka.get("hindi_explanation") or shloka.get("hindi", "")
    hb_path_hindi = dvs.first_font_path(False) if dvs.is_available() else None
    for fsize in [34, 30, 26, 24]:
        hf = font(fsize, False, devanagari=True, hindi_prose=False)
        if hb_path_hindi:
            lines = dvs.wrap_lines(hindi, hb_path_hindi, fsize, W - 80)
        else:
            lines = wrap_text(d, hindi, hf, W - 80, language="hi")
        if len(lines) * (fsize + 14) <= 260:
            break

    lh = hf.size + 14
    for line in lines[:5]:
        if hb_path_hindi:
            img = dvs.composite_line_centered(img, sy, line, hb_path_hindi, fsize, C_WHITE, 255, canvas_w=W)
            d = ImageDraw.Draw(img)
        else:
            d.text(
                (cx(d, line, hf, language="hi"), sy),
                line,
                font=hf,
                fill=C_WHITE,
                **raqm_text_kwargs(language="hi"),
            )
        sy += lh

    # ── Lesson — Latin font ────────────────────────────────────
    lesson = shloka.get("life_lesson_english") or shloka.get("lesson", "")
    d.rectangle([80, sy+10, W-80, sy+13], fill=(*C_GOLD, 60))
    sy += 24

    for fsize in [28, 24, 22]:
        lf_   = font(fsize)  # Latin font
        lines = wrap_text(d, lesson, lf_, W-100)
        if len(lines)*(fsize+12) <= 160: break

    for line in lines[:4]:
        d.text((cx(d,line,lf_), sy), line, font=lf_, fill=C_LOTUS)
        sy += lf_.size+12

    # ── Footer ─────────────────────────────────────────────────
    foot_y = H - 120
    d.rounded_rectangle([40, foot_y, W-40, H-40], radius=22, fill=C_PANEL)
    d.rectangle([40, foot_y, W-40, foot_y+5], fill=C_SAFFRON)

    bf = font(38, True)
    hf2 = font(24)
    d.text((cx(d,PAGE_NAME,bf), foot_y+14), PAGE_NAME, font=bf, fill=C_GOLD)
    handle = PAGE_HANDLE + "   |   Daily Gita Wisdom"
    while tw(d,handle,hf2) > W-120: handle = handle[:-4]+"..."
    d.text((cx(d,handle,hf2), foot_y+64), handle, font=hf2, fill=C_MUTED)

    img.save(output_path, quality=95)
    print(f"  [✓] Image saved -> {output_path}")
