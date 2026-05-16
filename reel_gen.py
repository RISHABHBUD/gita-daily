"""
Gita Daily Bot — Reel Generator (calm light theme)

1080×1920 vertical reel: soft gradients, slow motion, gentle typography.
Same sections and copy as before: intro → Sanskrit → Hindi → English → outro.
"""

import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageFilter
from moviepy import VideoClip, AudioFileClip

import devanagari_shaper as dvs

from config import (
    PAGE_NAME,
    PAGE_HANDLE,
    MUSIC_DIR,
    R_GRAD_TOP,
    R_GRAD_MID,
    R_GRAD_BOT,
    R_INK,
    R_INK_MUTED,
    R_SAGE,
    R_SAGE_LIGHT,
    R_ROSE,
    R_ROSE_LIGHT,
    R_GOLD,
    R_GOLD_LIGHT,
    R_CARD,
    R_CARD_RIM,
    R_BOKEH,
    R_VIGNETTE,
)

from font_helper import raqm_text_kwargs

_PROD_W, _PROD_H, _PROD_FPS = 1080, 1920, 30
W, H, FPS = _PROD_W, _PROD_H, _PROD_FPS


def font(size, bold=False, devanagari=False, hindi_prose=False):
    """Prefer calm Latin UI fonts; Devanagari uses Raqm shaping when available."""
    scaled = max(6, int(round(float(size) * W / float(_PROD_W))))
    from font_helper import devanagari_search_paths, truetype_compat

    if devanagari:
        for p in devanagari_search_paths(bold=bold, prefer_serif_for_hindi=hindi_prose):
            if not os.path.isfile(p):
                continue
            try:
                return truetype_compat(p, scaled)
            except OSError:
                continue
        return ImageFont.load_default()
    else:
        if bold:
            candidates = [
                "C:/Windows/Fonts/seguisb.ttf",
                "C:/Windows/Fonts/segoeuib.ttf",
                "C:/Windows/Fonts/calibrib.ttf",
                "C:/Windows/Fonts/Georgia.ttf",
                "arialbd.ttf",
                "Arial_Bold.ttf",
                "DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            ]
        else:
            candidates = [
                "C:/Windows/Fonts/segoeui.ttf",
                "C:/Windows/Fonts/segoeuil.ttf",
                "C:/Windows/Fonts/calibri.ttf",
                "C:/Windows/Fonts/constan.ttf",
                "C:/Windows/Fonts/Georgia.ttf",
                "arial.ttf",
                "Arial.ttf",
                "DejaVuSans.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, scaled)
        except Exception:
            pass
    return ImageFont.load_default()


def tw(d, t, f, language=None):
    kw = raqm_text_kwargs(language=language)
    b = d.textbbox((0, 0), t, font=f, **kw)
    return b[2] - b[0]


def cx(d, t, f, w=W, language=None):
    return (w - tw(d, t, f, language=language)) // 2


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def prog(t, s, e):
    return clamp((t - s) / (e - s)) if e > s else float(t >= s)


def smoothstep(t):
    t = clamp(t)
    return t * t * (3.0 - 2.0 * t)


def ease_io(t):
    """Ease in-out sine — very gentle."""
    t = clamp(t)
    return 0.5 - 0.5 * math.cos(math.pi * t)


def lerp(a, b, t):
    return a + (b - a) * clamp(t)


def lerp_col(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


def lerp_col3(c1, c2, c3, t):
    """t in [0,1]: top→mid→bot."""
    if t < 0.5:
        return lerp_col(c1, c2, t * 2.0)
    return lerp_col(c2, c3, (t - 0.5) * 2.0)


def breathe(t, phase=0.0, amp=1.0, period=4.2):
    return math.sin((t + phase) * (2 * math.pi / period)) * amp


def base_canvas(t=0.0):
    """Soft vertical gradient, drifting light orbs, barely-there grain."""
    arr = np.zeros((H, W, 3), dtype=np.uint8)
    drift = 0.04 * math.sin(t * 0.35)
    for y in range(H):
        u = y / H + drift * (1.0 - abs(y / H - 0.5))
        arr[y] = lerp_col3(R_GRAD_TOP, R_GRAD_MID, R_GRAD_BOT, clamp(u))
    img = Image.fromarray(arr)
    img = img.convert("RGBA")

    # Soft bokeh orbs (slow drift)
    bokeh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bokeh)
    seeds = [(0.22, 0.18, 140), (0.78, 0.25, 180), (0.55, 0.72, 220), (0.15, 0.62, 160), (0.88, 0.58, 130)]
    for i, (fx, fy, r0) in enumerate(seeds):
        ox = breathe(t, phase=i * 0.7, amp=28, period=5.5 + i * 0.4)
        oy = breathe(t, phase=i * 0.5 + 1.1, amp=22, period=6.2 + i * 0.3)
        cx_ = int(fx * W + ox)
        cy_ = int(fy * H + oy)
        rr = int(r0 + 12 * math.sin(t * 0.9 + i))
        for layer, alpha in [(1.0, 18), (0.65, 28), (0.35, 38)]:
            rr2 = int(rr * layer)
            bd.ellipse(
                [cx_ - rr2, cy_ - rr2, cx_ + rr2, cy_ + rr2],
                fill=(*R_BOKEH, alpha),
            )
    bokeh = bokeh.filter(ImageFilter.GaussianBlur(radius=max(5, int(round(18 * W / float(_PROD_W))))))
    img = Image.alpha_composite(img, bokeh)

    # Gentle radial vignette (soft edges, no harsh lines)
    base_rgb = img.convert("RGB")
    arr = np.asarray(base_rgb, dtype=np.float32)
    yy, xx = np.ogrid[:H, :W]
    cx_, cy_ = (W - 1) / 2.0, (H - 1) / 2.0
    dist = np.sqrt((xx - cx_) ** 2 + (yy - cy_) ** 2)
    norm = float(np.sqrt(cx_**2 + cy_**2))
    vig = (dist / max(norm, 1.0)) ** 1.35 * 0.22
    vig = vig[..., np.newaxis]
    vc = np.array(R_VIGNETTE, dtype=np.float32)
    arr = arr * (1.0 - vig) + vc * vig
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")

    # Whisper grain
    rng = np.random.default_rng(int(t * 120) + 7)
    noise = rng.integers(0, 5, size=(H, W), dtype=np.uint8)
    layer = Image.fromarray(noise, "L").convert("RGB")
    base_rgb = img.convert("RGB")
    layer = ImageChops.multiply(layer, Image.new("RGB", (W, H), (255, 255, 255)))
    base_rgb = ImageChops.soft_light(base_rgb, layer)
    return base_rgb


def draw_text_soft(img, xy, text, fnt, fill, shadow=(220, 225, 222), opacity=1.0, language=None):
    """Subtle lifted shadow for readability on light backgrounds."""
    x, y = xy
    tkw = raqm_text_kwargs(language=language)
    if isinstance(fill, tuple) and len(fill) == 4:
        rgba_fill = fill
    else:
        o = int(255 * opacity)
        rgba_fill = (*fill[:3], o) if len(fill) == 3 else fill
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for dx, dy, a in [(3, 3, 22), (2, 2, 14), (1, 1, 10)]:
        od.text((x + dx, y + dy), text, font=fnt, fill=(*shadow, a), **tkw)
    od.text((x, y), text, font=fnt, fill=rgba_fill, **tkw)
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def draw_text_alpha(img, xy, text, fnt, rgb, alpha, language=None):
    """Text with explicit alpha 0–255."""
    x, y = xy
    a = int(clamp(float(alpha), 0.0, 255.0))
    if a < 1:
        return img
    tkw = raqm_text_kwargs(language=language)
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).text((x, y), text, font=fnt, fill=(*rgb, a), **tkw)
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def frosted_card(img, box, radius=28, rim=R_CARD_RIM, fill_alpha=235):
    """Light frosted panel. Lower fill_alpha lets peaceful background motion show through."""
    x0, y0, x1, y1 = box
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=(*R_CARD, int(fill_alpha)))
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, outline=(*rim, 200), width=1)
    out = Image.alpha_composite(img.convert("RGBA"), layer)
    return out.convert("RGB")


def peaceful_motion_layer(t, style):
    """
    Full-frame soft motion behind the card (different per section, not the intro rings).
    style: 'sanskrit' | 'hindi' | 'english'
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)

    if style == "sanskrit":
        # Drifting soft petals / dots — sage mist
        for k in range(9):
            ph = k * 0.8
            x = int(W * (0.12 + 0.09 * k) + 55 * math.sin(t * 0.45 + ph))
            y = int(H * (0.35 + 0.05 * (k % 3)) + 40 * math.cos(t * 0.38 + ph * 0.7))
            r = 22 + (k % 4) * 10
            dr.ellipse([x - r, y - r, x + r, y + r], fill=(*R_SAGE_LIGHT, 14))
            dr.ellipse([x - r // 2, y - r // 2, x + r // 2, y + r // 2], fill=(*R_SAGE, 10))
    elif style == "hindi":
        # Slow wide ribbons — rose wash
        for k in range(5):
            yb = int(H * (0.22 + k * 0.14) + 30 * math.sin(t * 0.25 + k))
            pts = []
            for sx in range(0, W + 80, 40):
                yy = yb + int(18 * math.sin(sx * 0.008 + t * 0.6 + k))
                pts.append((sx, yy))
            if len(pts) > 2:
                flat = [c for p in pts for c in p]
                dr.line(flat, fill=(*R_ROSE_LIGHT, 18), width=26)
        for k in range(6):
            cx_ = int(W * (0.15 + 0.14 * k) + 25 * math.sin(t * 0.5 + k))
            cy_ = int(H * (0.55 + 0.06 * (k % 2)) + 20 * math.cos(t * 0.42 + k))
            dr.ellipse([cx_ - 80, cy_ - 28, cx_ + 80, cy_ + 28], fill=(*R_ROSE, 8))
    else:
        # English: gentle rising motes — pale gold
        for k in range(14):
            ph = k * 1.1
            x = int(W * (0.08 + (k * 0.067) % 0.86) + 20 * math.sin(t * 0.35 + ph))
            y = int(H * 0.92 - (t * 22 + k * 47) % (H * 0.75))
            s = 4 + (k % 3)
            dr.ellipse([x - s, y - s, x + s, y + s], fill=(*R_GOLD_LIGHT, 26))
        for k in range(3):
            ox = int(40 * math.sin(t * 0.2 + k * 2))
            dr.arc(
                [ox + k * 280 - 60, 200 + k * 220, ox + k * 280 + 220, 520 + k * 180],
                start=int(t * 25 + k * 40) % 360,
                end=int(t * 25 + k * 40) % 360 + 70,
                fill=(*R_GOLD, 12),
                width=18,
            )

    blur = 11 if style == "hindi" else 13
    blur = max(4, int(round(blur * W / float(_PROD_W))))
    return layer.filter(ImageFilter.GaussianBlur(radius=blur))


def composite_peaceful_bg(img, t, style):
    """Stack base image + soft motion (for shloka / arth / English sections)."""
    motion = peaceful_motion_layer(t, style)
    return Image.alpha_composite(img.convert("RGBA"), motion).convert("RGB")


def rgba_overlay(img, draw_fn):
    """Composite a small RGBA layer produced by draw_fn(layer, draw)."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_fn(layer, ImageDraw.Draw(layer))
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def hud_footer(img, t):
    """Minimal glass strip."""
    img = img.convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    y0, y1 = H - 132, H - 48
    float_y = int(3 * breathe(t, phase=0.3, amp=1.0, period=7.0))
    d.rounded_rectangle([40, y0 + float_y, W - 40, y1 + float_y], radius=22, fill=(*R_CARD, 210))
    d.rounded_rectangle([40, y0 + float_y, W - 40, y1 + float_y], radius=22, outline=(*R_CARD_RIM, 160), width=1)
    img = Image.alpha_composite(img, layer).convert("RGB")
    d = ImageDraw.Draw(img)
    name_f = font(34, True)
    handle_f = font(24)
    img = draw_text_soft(img, (58, H - 112 + float_y), PAGE_NAME, name_f, R_INK)
    hx = W - 58 - tw(ImageDraw.Draw(img), PAGE_HANDLE, handle_f)
    img = draw_text_soft(img, (hx, H - 104 + float_y), PAGE_HANDLE, handle_f, R_INK_MUTED)
    return np.array(img)


def wrap_text(d, text, f, max_w, language=None):
    words = text.replace("\n", " \n ").split()
    lines, cur = [], ""
    for w in words:
        if w == "\n":
            if cur:
                lines.append(cur)
            cur = ""
            continue
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


def cx_devanagari(text, font_path, font_px, w=None):
    """
    Compute centered x for Devanagari text using HarfBuzz shaped width.
    PIL textbbox without Raqm gives ~15-35% too-large widths for Devanagari.
    """
    if w is None:
        w = W
    if dvs.is_available():
        return (w - dvs.line_width_px(font_path, font_px, text)) // 2
    f = font(font_px, False, devanagari=True)
    d_tmp = ImageDraw.Draw(Image.new("RGB", (w + 100, 100)))
    return cx(d_tmp, text, f)


def line_reveal_alpha(t, total, n_lines, start=0.12, end=0.92):
    """Per-line fade-in progress 0..1 for line index."""
    if n_lines <= 0:
        return []
    p = smoothstep(prog(t, total * start, total * end))
    out = []
    for i in range(n_lines):
        gate = i / max(1, n_lines + 1)
        li = clamp((p - gate) * (n_lines + 2))
        out.append(smoothstep(li))
    return out


def frame_intro(t, shloka, day_number, total=3.0):
    img = base_canvas(t).convert("RGBA")
    arc_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ad = ImageDraw.Draw(arc_layer)
    # Breathing concentric rings (soft watercolor-like)
    cx_, cy_ = W // 2, H // 2 - 40
    breath = 1.0 + 0.04 * breathe(t, amp=1.0, period=5.0)
    for i in range(5):
        base_r = 120 + i * 72
        r = int(base_r * breath)
        a = max(10, 55 - i * 9)
        rot = t * 14 + i * 14
        bbox = [cx_ - r, cy_ - r, cx_ + r, cy_ + r]
        ad.arc(
            bbox,
            start=int(rot) % 360,
            end=int(rot) % 360 + 100,
            fill=(*R_SAGE_LIGHT, min(a, 85)),
            width=2,
        )
        ad.arc(
            bbox,
            start=int(rot + 130) % 360,
            end=int(rot + 240) % 360,
            fill=(*R_ROSE_LIGHT, min(a // 2 + 8, 45)),
            width=1,
        )
    arc_layer = arc_layer.filter(
        ImageFilter.GaussianBlur(radius=max(0.35, 1.2 * W / float(_PROD_W)))
    )
    img = Image.alpha_composite(img, arc_layer).convert("RGB")
    d = ImageDraw.Draw(img)

    p = ease_io(prog(t, 0.05, total * 0.95))

    subtitle = "Bhagavad Gita"
    sf = font(36, False)
    img = draw_text_alpha(
        img,
        (cx(d, subtitle, sf), int(H // 2 - 400 + 24 * (1 - p))),
        subtitle,
        sf,
        R_SAGE,
        int(220 * p),
    )
    d = ImageDraw.Draw(img)

    ch_name = shloka.get("chapter_title", shloka.get("chapter_name", ""))
    if ch_name:
        cf = font(30, False)
        img = draw_text_alpha(
            img,
            (cx(d, ch_name, cf), int(H // 2 - 348 + 20 * (1 - p))),
            ch_name,
            cf,
            R_INK_MUTED,
            int(230 * smoothstep(prog(t, 0.15, total * 0.9))),
        )
        d = ImageDraw.Draw(img)

    cv_txt = f"Chapter {shloka['chapter']}  ·  Verse {shloka['verse']}"
    for fsize in [76, 64, 54]:
        cvf = font(fsize, True)
        if tw(d, cv_txt, cvf) <= W - 100:
            break
    ty = int(H // 2 - 240 + 36 * (1 - p))
    img = draw_text_alpha(img, (cx(d, cv_txt, cvf), ty), cv_txt, cvf, R_INK, int(255 * smoothstep(prog(t, 0.2, total * 0.85))))
    d = ImageDraw.Draw(img)

    # अध्याय X, श्लोक Y — Devanagari via HarfBuzz
    hb_path = dvs.first_font_path(False) if dvs.is_available() else None
    deva_txt = f"अध्याय {shloka['chapter']}, श्लोक {shloka['verse']}"
    deva_fsize = 36
    deva_a = int(230 * smoothstep(prog(t, 0.25, total * 0.9)))
    if hb_path and deva_a > 8:
        img = dvs.composite_line_centered(img, int(H // 2 - 168 + 14 * (1 - p)), deva_txt, hb_path, deva_fsize, R_GOLD, deva_a, canvas_w=W)
    d = ImageDraw.Draw(img)

    day_txt = f"Day {day_number} of 700"
    df = font(32, False)
    img = draw_text_alpha(
        img,
        (cx(d, day_txt, df), int(H // 2 - 120 + 16 * (1 - p))),
        day_txt,
        df,
        R_GOLD,
        int(240 * smoothstep(prog(t, 0.35, total))),
    )
    d = ImageDraw.Draw(img)

    dw = int((W - 200) * smoothstep(prog(t, 0.25, total * 0.75)))
    yl = H // 2 - 36
    if dw > 6:
        la = int(200 * p)
        img = rgba_overlay(
            img,
            lambda layer, draw: draw.rectangle(
                [W // 2 - dw // 2, yl, W // 2 + dw // 2, yl + 2],
                fill=(*R_GOLD_LIGHT, la),
            ),
        )
        d = ImageDraw.Draw(img)

    return hud_footer(img, t)


def draw_section_header(img, title, accent_rgb, t):
    """Accent rule + title inside existing content card."""
    bar_a = int(115 + 85 * ease_io(prog(t, 0, 0.55)))
    img = rgba_overlay(
        img,
        lambda layer, draw: draw.rectangle(
            [48, 128, W - 48, 134], fill=(*accent_rgb, bar_a)
        ),
    )
    d = ImageDraw.Draw(img)
    tf = font(32, True)
    fade = int(255 * smoothstep(prog(t, 0.05, 0.52)))
    return draw_text_alpha(img, (cx(d, title, tf), 148), title, tf, R_INK, fade)


def frame_sanskrit(t, shloka, total=5.0):
    img = composite_peaceful_bg(base_canvas(t), t, "sanskrit")
    img = frosted_card(img, [36, 120, W - 36, H - 200], radius=32, fill_alpha=218)
    d = ImageDraw.Draw(img)
    img = draw_section_header(img, "Shloka", R_SAGE, t)
    d = ImageDraw.Draw(img)

    sanskrit = shloka["sanskrit"]
    hb_path = dvs.first_font_path(False) if dvs.is_available() else None
    for fsize in [54, 48, 42, 36]:
        sf = font(fsize, False, devanagari=True, hindi_prose=False)
        lines = wrap_devanagari(sanskrit, hb_path or "", fsize, W - 120) if hb_path else wrap_text(d, sanskrit, sf, W - 120, language="sa")
        if len(lines) * (fsize + 22) <= 560:
            break

    n = len(lines)
    alphas = line_reveal_alpha(t, total, n, start=0.08, end=0.88)
    lh = sf.size + 22
    block_h = n * lh
    sy = int(H // 2 - block_h // 2 - 20 + 8 * breathe(t, 0.2, 0.5, 6.0))

    for i, line in enumerate(lines):
        a = int(255 * alphas[i]) if i < len(alphas) else 0
        if a < 8:
            continue
        rgb = tuple(int(lerp(R_INK[j], R_SAGE[j], 0.22)) for j in range(3))
        if hb_path:
            img = dvs.composite_line_centered(img, sy, line, hb_path, fsize, rgb, a, canvas_w=W)
        else:
            x = cx(d, line, sf, language="sa")
            img = draw_text_alpha(img, (x, sy), line, sf, rgb, a, language="sa")
        d = ImageDraw.Draw(img)
        sy += lh

    # Transliteration: gentle fade after main lines visible
    if n > 0 and all(a > 0.92 for a in alphas):
        p_trans = ease_io(prog(t, total * 0.58, total))
        trans = shloka.get("transliteration", "")
        tf = font(24, False)
        ty = sy + 12
        for line in wrap_text(d, trans, tf, W - 120)[:3]:
            img = draw_text_alpha(img, (cx(d, line, tf), ty), line, tf, R_INK_MUTED, int(210 * p_trans))
            d = ImageDraw.Draw(img)
            ty += 34

    return hud_footer(img, t)


def frame_vyakhya(t, shloka, total=6.0, bridge_sec=0.0):
    """Hindi meaning frame — shows shloka['hindi'] key.
    bridge_sec: duration of bridge voice that plays before text should appear.
    """
    img = composite_peaceful_bg(base_canvas(t), t, "hindi")
    img = frosted_card(img, [36, 120, W - 36, H - 200], radius=32, fill_alpha=222)
    d = ImageDraw.Draw(img)
    img = draw_section_header(img, "Arth  ·  Hindi Meaning", R_ROSE, t)
    d = ImageDraw.Draw(img)

    hindi = shloka.get("hindi", "")

    hb_path = dvs.first_font_path(False) if dvs.is_available() else None
    for fsize in [44, 40, 36, 32]:
        lines = wrap_devanagari(hindi, hb_path or "", fsize, W - 120) if hb_path else wrap_text(
            d, hindi, font(fsize, False, devanagari=True), W - 120, language="hi"
        )
        if len(lines) * (fsize + 20) <= 680:
            break

    n = len(lines)
    # Text starts only after bridge voice finishes + small buffer
    text_start = min(0.85, (bridge_sec + 0.3) / max(total, 1.0))
    alphas = line_reveal_alpha(t, total, n, start=text_start, end=0.95)
    lh = fsize + 20
    block_h = n * lh
    vy = int(H // 2 - block_h // 2 + 6 * breathe(t, 0.4, 0.45, 5.5))

    for i, line in enumerate(lines):
        a = int(255 * alphas[i]) if i < len(alphas) else 0
        if a < 8:
            continue
        rgb = tuple(int(lerp(R_INK[j], R_ROSE[j], 0.15)) for j in range(3))
        if hb_path:
            img = dvs.composite_line_centered(img, vy, line, hb_path, fsize, rgb, a, canvas_w=W)
        else:
            hf = font(fsize, False, devanagari=True)
            img = draw_text_alpha(img, (cx(d, line, hf, language="hi"), vy), line, hf, rgb, a, language="hi")
        d = ImageDraw.Draw(img)
        vy += lh

    return hud_footer(img, t)




def frame_english(t, shloka, total=5.0):
    img = composite_peaceful_bg(base_canvas(t), t, "english")
    img = frosted_card(img, [36, 120, W - 36, H - 200], radius=32, fill_alpha=218)
    d = ImageDraw.Draw(img)
    img = draw_section_header(img, "Meaning (English)", R_GOLD, t)
    d = ImageDraw.Draw(img)

    english = shloka.get("english", "")
    for fsize in [44, 38, 34, 30]:
        lf = font(fsize, False)
        lines = wrap_text(d, english, lf, W - 120)
        if len(lines) * (fsize + 20) <= 720:
            break

    n = len(lines)
    # start=0.35 — text waits for bridge voice to finish before appearing
    alphas = line_reveal_alpha(t, total, n, start=0.35, end=0.95)
    lh = lf.size + 20
    block_h = n * lh
    ly = int(H // 2 - block_h // 2 + 6 * breathe(t, 0.6, 0.5, 6.2))

    for i, line in enumerate(lines):
        a = int(255 * alphas[i]) if i < len(alphas) else 0
        if a < 8:
            continue
        img = draw_text_alpha(img, (cx(d, line, lf), ly), line, lf, R_INK, a)
        d = ImageDraw.Draw(img)
        ly += lh

    return hud_footer(img, t)


def frame_outro(t, total=2.0):
    img = base_canvas(t)
    p = ease_io(prog(t, 0.05, total * 0.92))

    # Soft center bloom
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    br = int(320 + 40 * math.sin(t * 1.1))
    od.ellipse([W // 2 - br, H // 2 - 260 - br, W // 2 + br, H // 2 - 260 + br], fill=(*R_ROSE_LIGHT, int(50 * p)))
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    d = ImageDraw.Draw(img)

    nf = font(82, True)
    name_y = int(H // 2 - 240 + 20 * (1 - p))
    img = draw_text_alpha(img, (cx(d, PAGE_NAME, nf), name_y), PAGE_NAME, nf, R_INK, int(255 * p))
    d = ImageDraw.Draw(img)

    # Jai Shree Krishna in Devanagari via HarfBuzz
    hb_path = dvs.first_font_path(True) if dvs.is_available() else None
    jai_deva = "जय श्री कृष्ण"
    jai_fsize = 52
    jai_a = int(255 * smoothstep(prog(t, 0.15, total * 0.85)))
    if hb_path and jai_a > 8:
        img = dvs.composite_line_centered(img, int(H // 2 - 148 + 12 * (1 - p)), jai_deva, hb_path, jai_fsize, R_GOLD, jai_a, canvas_w=W)
    else:
        jf = font(44, True)
        img = draw_text_alpha(img, (cx(d, "Jai Shree Krishna", jf), int(H // 2 - 148 + 12 * (1 - p))), "Jai Shree Krishna", jf, R_GOLD, jai_a)
    d = ImageDraw.Draw(img)

    hf = font(32, False)
    img = draw_text_alpha(
        img,
        (cx(d, PAGE_HANDLE, hf), int(H // 2 - 130 + 14 * (1 - p))),
        PAGE_HANDLE,
        hf,
        R_INK_MUTED,
        int(240 * smoothstep(prog(t, 0.2, total))),
    )
    d = ImageDraw.Draw(img)

    l1, l2 = "Follow for daily", "Gita wisdom & shlokas"
    for i, line in enumerate([l1, l2]):
        cf = font(40, i == 1)
        py = int(H // 2 - 20 + i * 62 + 6 * breathe(t, i * 0.3, 0.4, 5.0))
        fa = int(235 * smoothstep(prog(t, 0.25 + i * 0.08, total * 0.95)))
        img = draw_text_alpha(img, (cx(d, line, cf), py), line, cf, R_INK if i == 0 else R_SAGE, fa)
        d = ImageDraw.Draw(img)

    bw, bh = 400, 76
    bx, by = W // 2 - bw // 2, int(H // 2 + 200)
    pill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pill)
    show = smoothstep(prog(t, 0.35, total))
    pd.rounded_rectangle([bx, by, bx + bw, by + bh], radius=40, fill=(*R_SAGE, int(230 * show)))
    img = Image.alpha_composite(img.convert("RGBA"), pill).convert("RGB")
    d = ImageDraw.Draw(img)
    cta = "Follow now"
    ctf = font(28, True)
    img = draw_text_soft(
        img,
        (bx + (bw - tw(d, cta, ctf)) // 2, by + 22),
        cta,
        ctf,
        (255, 255, 255),
        shadow=(60, 90, 75),
    )

    return hud_footer(img, t)


def pick_background_track(bot_dir):
    """
    Prefer spiritual.mp3 (or any *spiritual* audio).
    Searches: gita-daily-bot/music/ first, then gita-daily-bot/ (same folder as reel_gen.py).
    """
    audio_ext = (".mp3", ".wav", ".m4a")

    def scan_dir(d):
        if not os.path.isdir(d):
            return None
        try:
            names = [f for f in os.listdir(d) if f.lower().endswith(audio_ext)]
        except OSError:
            return None
        if not names:
            return None
        lower_map = {n.lower(): n for n in names}
        if "spiritual.mp3" in lower_map:
            return os.path.join(d, lower_map["spiritual.mp3"])
        for n in names:
            if "spiritual" in n.lower():
                return os.path.join(d, n)
        return os.path.join(d, sorted(names, key=str.lower)[0])

    music_dir = os.path.join(bot_dir, MUSIC_DIR)
    hit = scan_dir(music_dir)
    if hit:
        return hit
    return scan_dir(bot_dir)


def generate_tts(text, lang, output_path, rate=None, pitch="-5Hz"):
    """Neural TTS via Microsoft Edge — hi-IN-MadhurNeural for all sections."""
    import re

    text = re.sub(r"^[\d\.\s।|]+", "", text).strip()
    text = text[:300]
    if not text:
        return None

    voice = "hi-IN-MadhurNeural"
    if rate is None:
        # English slightly faster, Hindi/Sanskrit calmer
        rate = "-10%" if lang == "en" else "-18%"

    try:
        import asyncio
        import edge_tts

        async def _save():
            com = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
            await com.save(output_path)

        asyncio.run(_save())
        return output_path
    except Exception as e_edge:
        try:
            from gtts import gTTS
            print(f"  [!] edge-tts unavailable ({e_edge}); using gTTS fallback")
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(output_path)
            return output_path
        except Exception as e_gt:
            print(f"  [!] TTS failed ({lang}): {e_gt}")
            return None


def _build_vyakhya_tts(shloka):
    """TTS text for vyakhya frame — uses hindi key."""
    return shloka.get("hindi", "")[:250]


def create_shloka_reel(shloka, output_path, day_number=1, fast_preview=False):
    """
    Generate shloka reel from gita_v8.json data.

    Flow:
      intro  →  sanskrit  →  vyakhya (hindi)  →  english  →  outro

    Bridge voices:
      after sanskrit : "Aayiye, iss shloka ko Hindi mein samajhte hain."
      after vyakhya  : "Now let's understand this shloka in English."

    fast_preview: 540x960 @ 16fps for quick local testing.
    """
    global W, H, FPS
    _saved_dims = (W, H, FPS)
    enc_preset = "medium"
    enc_crf_list = ["-crf", "28"]
    if fast_preview:
        W, H, FPS = 540, 960, 16
        enc_preset = "ultrafast"
        enc_crf_list = ["-crf", "32"]
        print("  [FAST PREVIEW] 540x960 @ 16fps, ultrafast encode")
    try:
        print(f"  Shloka: BG {shloka['chapter']}.{shloka['verse']}")

        DURATIONS = {
            "intro":   10.0,
            "sanskrit": 6.0,
            "vyakhya":  7.0,
            "english":  6.0,
            "outro":    3.0,
        }

        def make_clip(fn, dur, **kw):
            return VideoClip(lambda t: fn(t, **kw).astype(np.uint8), duration=dur).with_fps(FPS)

        FADE = 1.05

        def crossfade(a, b, fade=FADE):
            from moviepy import VideoClip as VC
            total = a.duration + b.duration - fade
            def mf(t):
                if t < a.duration - fade:
                    return a.get_frame(t)
                if t > a.duration:
                    return b.get_frame(t - a.duration + fade)
                raw = (t - (a.duration - fade)) / max(fade, 1e-6)
                alpha = smoothstep(raw)
                fa = a.get_frame(t).astype(np.float32)
                fb = b.get_frame(t - a.duration + fade).astype(np.float32)
                return (fa * (1.0 - alpha) + fb * alpha).astype(np.uint8)
            return VC(mf, duration=total).with_fps(FPS)

        print("  Generating TTS...")
        tts_dir = os.path.join(os.path.dirname(os.path.abspath(output_path)), "tts")
        os.makedirs(tts_dir, exist_ok=True)
        ch, v = shloka["chapter"], shloka["verse"]

        tts_files = {
            "intro": generate_tts(
                "Geeta sirf granth nahi… jeene ka gyaan hai. "
                "Aaiye, roz ek shlok ke saath hum issse samajhte hain.",
                "hi", os.path.join(tts_dir, "tts_intro.mp3"), rate="-8%"
            ),
            "chapter_verse": generate_tts(
                f"adhyay {ch}, shlok {v}",
                "hi", os.path.join(tts_dir, "tts_chapter_verse.mp3"), rate="-15%"
            ),
            "sanskrit": generate_tts(
                shloka["sanskrit"].replace("\n", " "),
                "hi", os.path.join(tts_dir, "tts_sanskrit.mp3"), rate="-22%"
            ),
            "bridge_hindi": generate_tts(
                "Aayiye, iss shloka ko Hindi mein samajhte hain.",
                "hi", os.path.join(tts_dir, "tts_bridge_hindi.mp3"), rate="-10%"
            ),
            "vyakhya": generate_tts(
                _build_vyakhya_tts(shloka),
                "hi", os.path.join(tts_dir, "tts_vyakhya.mp3"), rate="-16%"
            ),
            "bridge_english": generate_tts(
                "Now let's understand this shloka in English.",
                "en", os.path.join(tts_dir, "tts_bridge_english.mp3"), rate="+5%"
            ),
            "english": generate_tts(
                shloka.get("english", ""),
                "en", os.path.join(tts_dir, "tts_english.mp3"), rate="+5%"
            ),
            "bridge_lesson": None,
            "lesson": None,
            "jai": generate_tts(
                "Jai Shree Krishna",
                "hi", os.path.join(tts_dir, "tts_jai.mp3"), rate="-20%"
            ),
        }

        # ── Duration calculation ──────────────────────────────────────────────
        actual = dict(DURATIONS)

        def _dur(key):
            p = tts_files.get(key)
            if p and os.path.exists(p):
                try:
                    return AudioFileClip(p).duration
                except Exception:
                    pass
            return 0.0

        # Intro: hook + 0.4s gap + chapter/verse + 2s breathing room
        intro_tts = _dur("intro") + 0.4 + _dur("chapter_verse")
        actual["intro"] = max(8.5, intro_tts + 2.0)
        print(f"  TTS intro: {intro_tts:.1f}s → {actual['intro']:.1f}s")

        # Sanskrit: shloka reading + 1s tail
        san = _dur("sanskrit")
        actual["sanskrit"] = max(DURATIONS["sanskrit"], san + 1.0)
        print(f"  TTS sanskrit: {san:.1f}s → {actual['sanskrit']:.1f}s")

        # Vyakhya: bridge_hindi plays first, then hindi translation
        bh = _dur("bridge_hindi")
        vy = _dur("vyakhya")
        # Add 0.5s gap between bridge and content, plus 1.2s tail
        actual["vyakhya"] = max(DURATIONS["vyakhya"], bh + 0.5 + vy + 1.2)
        print(f"  TTS vyakhya: bridge({bh:.1f}s) + hindi({vy:.1f}s) → {actual['vyakhya']:.1f}s")

        # English: bridge_english plays first, then translation
        # Add enough tail so outro doesn't start before english finishes
        be = _dur("bridge_english")
        en = _dur("english")
        actual["english"] = max(DURATIONS["english"], be + 0.4 + en + 2.5)
        print(f"  TTS english: bridge({be:.1f}s) + translation({en:.1f}s) → {actual['english']:.1f}s")

        # Outro: sized to fit Jai Shree Krishna
        jai = _dur("jai")
        actual["outro"] = max(3.0, jai + 1.5)
        print(f"  TTS jai: {jai:.1f}s → outro {actual['outro']:.1f}s")

        # ── Video clips ───────────────────────────────────────────────────────
        print("  Rendering video sections...")
        clips = [
            make_clip(frame_intro,    actual["intro"],   shloka=shloka, day_number=day_number, total=actual["intro"]),
            make_clip(frame_sanskrit, actual["sanskrit"], shloka=shloka, total=actual["sanskrit"]),
            make_clip(frame_vyakhya,  actual["vyakhya"],  shloka=shloka, total=actual["vyakhya"], bridge_sec=bh + 0.5),
            make_clip(frame_english,  actual["english"],  shloka=shloka, total=actual["english"]),
            make_clip(frame_outro,    actual["outro"],    total=actual["outro"]),
        ]

        video = clips[0]
        for c in clips[1:]:
            video = crossfade(video, c)
        total_dur = sum(c.duration for c in clips) - FADE * (len(clips) - 1)
        print(f"  Total video: {total_dur:.1f}s")

        # ── Audio assembly ────────────────────────────────────────────────────
        from moviepy import concatenate_audioclips
        from moviepy.audio.AudioClip import AudioArrayClip

        def silence(dur):
            return AudioArrayClip(
                np.zeros((max(1, int(dur * 44100)), 2), dtype=np.float32), fps=44100
            ).with_duration(dur)

        def load(key):
            p = tts_files.get(key)
            if p and os.path.exists(p):
                try:
                    return AudioFileClip(p)
                except Exception:
                    pass
            return None

        def build_section(parts, total_sec):
            """parts = list of (tts_key_or_None, gap_after_secs). Pads to total_sec."""
            clips_list = []
            used = 0.0
            for key, gap in parts:
                c = load(key) if key else None
                if c:
                    clips_list.append(c)
                    used += c.duration
                if gap > 0:
                    clips_list.append(silence(gap))
                    used += gap
            tail = max(0.1, total_sec - used)
            clips_list.append(silence(tail))
            return concatenate_audioclips(clips_list)

        audio_parts = [
            # Intro: hook → 0.4s → chapter/verse → pad
            build_section([("intro", 0.4), ("chapter_verse", 0.0)], actual["intro"]),

            # Sanskrit: shloka reading → pad
            build_section([("sanskrit", 0.0)], actual["sanskrit"]),

            # Vyakhya: bridge_hindi → 0.4s → hindi → pad
            build_section([("bridge_hindi", 0.4), ("vyakhya", 0.0)], actual["vyakhya"]),

            # English: bridge_english → 0.4s → translation → pad
            build_section([("bridge_english", 0.4), ("english", 0.0)], actual["english"]),

            # Outro: 0.15s silence → Jai Shree Krishna early → pad
            build_section([(None, 0.15), ("jai", 0.0)], actual["outro"]),
        ]

        tts_audio = concatenate_audioclips(audio_parts)

        # ── Background music ──────────────────────────────────────────────────
        bot_dir = os.path.dirname(os.path.abspath(__file__))
        bg_path = pick_background_track(bot_dir)

        if bg_path and os.path.isfile(bg_path):
            try:
                from moviepy import CompositeAudioClip
                probe = AudioFileClip(bg_path)
                clip_len = float(probe.duration)
                probe.close()
                if clip_len + 0.01 < total_dur:
                    loops, rem = [], total_dur
                    while rem > 1e-3:
                        seg = min(rem, clip_len)
                        loops.append(AudioFileClip(bg_path).subclipped(0, seg))
                        rem -= seg
                    bg = concatenate_audioclips(loops)
                else:
                    bg = AudioFileClip(bg_path).subclipped(0, min(total_dur, clip_len))
                bg = bg.with_volume_scaled(0.25)
                video = video.with_audio(CompositeAudioClip([tts_audio, bg]))
                print(f"  [✓] TTS + music ({os.path.basename(bg_path)}) @ 25%")
            except Exception as e:
                print(f"  [!] Music skipped: {e}")
                video = video.with_audio(tts_audio)
        else:
            video = video.with_audio(tts_audio)
            print("  [✓] TTS only (no music file found)")

        print(f"  Writing video ({total_dur:.1f}s)...")
        video.write_videofile(
            output_path,
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="temp_gita.m4a",
            remove_temp=True,
            logger="bar",
            preset=enc_preset,
            ffmpeg_params=enc_crf_list,
        )
        print(f"  [✓] Reel saved -> {output_path}")
    finally:
        W, H, FPS = _saved_dims
