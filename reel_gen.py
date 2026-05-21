"""
Gita Daily Bot — Reel Generator (calm light theme)

1080×1920 vertical reel: soft gradients, slow motion, gentle typography.
Flow: intro → hindi_explanation → english_explanation → life_lesson → outro
Data source: gita_data.json
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

# ── Krishna background cache ──────────────────────────────────────────────────
_krishna_cache: dict = {}

def _load_krishna(w, h):
    """
    Load krishna.jpg, resize to cover w×h (center-crop), desaturate 80%,
    apply strong vignette so edges fade to black, cache the result.
    Returns an RGBA PIL image ready to composite at low alpha.
    """
    key = (w, h)
    if key in _krishna_cache:
        return _krishna_cache[key]

    bot_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(bot_dir, "krishna.jpg")
    if not os.path.isfile(path):
        _krishna_cache[key] = None
        return None

    src = Image.open(path).convert("RGB")
    sw, sh = src.size

    # Cover-fit: scale so image fills w×h, then center-crop
    scale = max(w / sw, h / sh)
    nw, nh = int(sw * scale), int(sh * scale)
    src = src.resize((nw, nh), Image.LANCZOS)
    left = (nw - w) // 2
    top  = (nh - h) // 2
    src = src.crop((left, top, left + w, top + h))

    # Desaturate 80% — keeps a hint of color, mostly grayscale
    gray = src.convert("L").convert("RGB")
    src = Image.blend(src, gray, alpha=0.80)

    # Heavy vignette — fade to black at edges so gradient/text stays readable
    arr = np.asarray(src, dtype=np.float32)
    yy, xx = np.ogrid[:h, :w]
    cx_, cy_ = (w - 1) / 2.0, (h - 1) / 2.0
    dist = np.sqrt(((xx - cx_) / cx_) ** 2 + ((yy - cy_) / cy_) ** 2)
    # Vignette: center=1.0, edges=0.0, power 1.8
    vig = np.clip(1.0 - dist ** 1.8, 0.0, 1.0)[..., np.newaxis]
    arr = arr * vig
    src = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")

    _krishna_cache[key] = src
    return src


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
                "arialbd.ttf", "Arial_Bold.ttf", "DejaVuSans-Bold.ttf",
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
                "arial.ttf", "Arial.ttf", "DejaVuSans.ttf",
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
    t = clamp(t)
    return 0.5 - 0.5 * math.cos(math.pi * t)


def lerp(a, b, t):
    return a + (b - a) * clamp(t)


def lerp_col(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


def lerp_col3(c1, c2, c3, t):
    if t < 0.5:
        return lerp_col(c1, c2, t * 2.0)
    return lerp_col(c2, c3, (t - 0.5) * 2.0)


def breathe(t, phase=0.0, amp=1.0, period=4.2):
    return math.sin((t + phase) * (2 * math.pi / period)) * amp


def base_canvas(t=0.0):
    """Soft vertical gradient, Krishna bg watermark, drifting light orbs, barely-there grain."""
    arr = np.zeros((H, W, 3), dtype=np.uint8)
    drift = 0.04 * math.sin(t * 0.35)
    for y in range(H):
        u = y / H + drift * (1.0 - abs(y / H - 0.5))
        arr[y] = lerp_col3(R_GRAD_TOP, R_GRAD_MID, R_GRAD_BOT, clamp(u))
    img = Image.fromarray(arr).convert("RGBA")

    # ── Krishna watermark — very subtle, breathing alpha ─────────────────────
    krishna = _load_krishna(W, H)
    if krishna is not None:
        # Gentle breathing: alpha oscillates between 28 and 38 (~11-15% opacity)
        k_alpha = int(33 + 5 * math.sin(t * 0.4))
        k_layer = krishna.copy()
        # Apply alpha by modifying the A channel
        r, g, b, a = k_layer.split()
        # Scale existing vignette-alpha by our desired opacity
        a = a.point(lambda x: int(x * k_alpha / 255))
        k_layer = Image.merge("RGBA", (r, g, b, a))
        img = Image.alpha_composite(img, k_layer)

    bokeh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bokeh)
    seeds = [(0.22, 0.18, 140), (0.78, 0.25, 180), (0.55, 0.72, 220), (0.15, 0.62, 160), (0.88, 0.58, 130)]
    for i, (fx, fy, r0) in enumerate(seeds):
        ox = breathe(t, phase=i * 0.7, amp=28, period=5.5 + i * 0.4)
        oy = breathe(t, phase=i * 0.5 + 1.1, amp=22, period=6.2 + i * 0.3)
        cx_ = int(fx * W + ox)
        cy_ = int(fy * H + oy)
        rr = int(r0 + 12 * math.sin(t * 0.9 + i))
        for layer_f, alpha in [(1.0, 18), (0.65, 28), (0.35, 38)]:
            rr2 = int(rr * layer_f)
            bd.ellipse([cx_ - rr2, cy_ - rr2, cx_ + rr2, cy_ + rr2], fill=(*R_BOKEH, alpha))
    bokeh = bokeh.filter(ImageFilter.GaussianBlur(radius=max(5, int(round(18 * W / float(_PROD_W))))))
    img = Image.alpha_composite(img, bokeh)

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

    rng = np.random.default_rng(int(t * 120) + 7)
    noise = rng.integers(0, 5, size=(H, W), dtype=np.uint8)
    layer = Image.fromarray(noise, "L").convert("RGB")
    base_rgb = img.convert("RGB")
    layer = ImageChops.multiply(layer, Image.new("RGB", (W, H), (255, 255, 255)))
    return ImageChops.soft_light(base_rgb, layer)


def draw_text_soft(img, xy, text, fnt, fill, shadow=(220, 225, 222), opacity=1.0, language=None):
    x, y = xy
    tkw = raqm_text_kwargs(language=language)
    o = int(255 * opacity)
    rgba_fill = (*fill[:3], o) if len(fill) == 3 else fill
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for dx, dy, a in [(3, 3, 22), (2, 2, 14), (1, 1, 10)]:
        od.text((x + dx, y + dy), text, font=fnt, fill=(*shadow, a), **tkw)
    od.text((x, y), text, font=fnt, fill=rgba_fill, **tkw)
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def draw_text_alpha(img, xy, text, fnt, rgb, alpha, language=None):
    x, y = xy
    a = int(clamp(float(alpha), 0.0, 255.0))
    if a < 1:
        return img
    tkw = raqm_text_kwargs(language=language)
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).text((x, y), text, font=fnt, fill=(*rgb, a), **tkw)
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def frosted_card(img, box, radius=28, rim=R_CARD_RIM, fill_alpha=235):
    x0, y0, x1, y1 = box
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=(*R_CARD, int(fill_alpha)))
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, outline=(*rim, 200), width=1)
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def rgba_overlay(img, draw_fn):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_fn(layer, ImageDraw.Draw(layer))
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def draw_om_bg(img, t, alpha_max=28):
    """Faint pulsing ॐ symbol — drawn behind card for background layer."""
    hb_path = dvs.first_font_path(True) if dvs.is_available() else None
    pulse = alpha_max + int(8 * math.sin(t * 0.7))
    om_text = "ॐ"
    om_size = 420
    if hb_path:
        try:
            from font_helper import truetype_compat
            om_font = truetype_compat(hb_path, om_size)
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(ov)
            tkw = raqm_text_kwargs(language="hi")
            bb = od.textbbox((0, 0), om_text, font=om_font, **tkw)
            ox = (W - (bb[2] - bb[0])) // 2 - bb[0]
            oy = (H - (bb[3] - bb[1])) // 2 - bb[1] - 60
            od.text((ox, oy), om_text, font=om_font, fill=(*R_GOLD, pulse), **tkw)
            blurred = ov.filter(ImageFilter.GaussianBlur(radius=6))
            return Image.alpha_composite(img.convert("RGBA"), blurred).convert("RGB")
        except Exception:
            pass
    return img


def draw_om_on_card(img, t, alpha_max=32):
    """
    Animated ॐ drawn ON the card — slow rotation via crop+paste trick,
    pulsing alpha, and a soft gold glow ring underneath.
    Placed at card center so it sits behind text but above the card surface.
    """
    hb_path = dvs.first_font_path(True) if dvs.is_available() else None
    om_text = "ॐ"
    om_size = 380

    # Pulse: breathe between alpha_max-10 and alpha_max+10
    pulse_a = int(alpha_max + 10 * math.sin(t * 0.65))

    # Glow ring — slow breathe radius
    glow_r = int(160 + 18 * math.sin(t * 0.5))
    glow_a = int(18 + 8 * math.sin(t * 0.5))
    cx_ = W // 2
    cy_ = H // 2 - 40
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([cx_ - glow_r, cy_ - glow_r, cx_ + glow_r, cy_ + glow_r],
               fill=(*R_GOLD, glow_a))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=40))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")

    if not hb_path:
        return img
    try:
        from font_helper import truetype_compat
        om_font = truetype_compat(hb_path, om_size)
        # Render Om onto a square canvas
        pad = 60
        tmp = Image.new("RGBA", (om_size + pad * 2, om_size + pad * 2), (0, 0, 0, 0))
        td = ImageDraw.Draw(tmp)
        tkw = raqm_text_kwargs(language="hi")
        bb = td.textbbox((0, 0), om_text, font=om_font, **tkw)
        tx = pad + (om_size - (bb[2] - bb[0])) // 2 - bb[0]
        ty = pad + (om_size - (bb[3] - bb[1])) // 2 - bb[1]
        td.text((tx, ty), om_text, font=om_font, fill=(*R_GOLD, pulse_a), **tkw)
        tmp = tmp.filter(ImageFilter.GaussianBlur(radius=3))

        # Slow rotation — one full turn every 30s
        angle = (t * 360 / 30) % 360
        rotated = tmp.rotate(angle, resample=Image.BICUBIC, expand=False)

        # Paste centered on card
        rw, rh = rotated.size
        px = cx_ - rw // 2
        py = cy_ - rh // 2
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        canvas.paste(rotated, (px, py), rotated)
        return Image.alpha_composite(img.convert("RGBA"), canvas).convert("RGB")
    except Exception:
        return img


def draw_glowing_header_bar(img, accent_rgb, t):
    """Animated accent bar that expands from center with a gold pulse glow."""
    p = ease_io(prog(t, 0.0, 0.5))
    bar_w = int((W - 96) * p)
    if bar_w < 2:
        return img
    cx_ = W // 2
    x0, x1 = cx_ - bar_w // 2, cx_ + bar_w // 2
    y0, y1 = 128, 134
    # Glow layer — wider, blurred
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    glow_a = int(60 * p)
    gd.rectangle([x0 - 20, y0 - 4, x1 + 20, y1 + 4], fill=(*R_GOLD, glow_a))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=8))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    # Sharp bar on top
    bar_a = int(200 * p)
    img = rgba_overlay(img, lambda layer, draw: draw.rectangle(
        [x0, y0, x1, y1], fill=(*accent_rgb, bar_a)))
    # Bright center spark
    spark_w = max(4, bar_w // 6)
    spark_a = int(255 * smoothstep(prog(t, 0.0, 0.25)))
    if spark_a > 8:
        img = rgba_overlay(img, lambda layer, draw: draw.rectangle(
            [cx_ - spark_w // 2, y0 - 1, cx_ + spark_w // 2, y1 + 1],
            fill=(*R_GOLD_LIGHT, spark_a)))
    return img


def peaceful_motion_layer(t, style):
    """style: 'hindi' | 'english' | 'lesson'"""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)

    if style == "hindi":
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
    elif style == "english":
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
                fill=(*R_GOLD, 12), width=18,
            )
    else:  # lesson — soft sage drifting dots
        for k in range(9):
            ph = k * 0.8
            x = int(W * (0.12 + 0.09 * k) + 55 * math.sin(t * 0.45 + ph))
            y = int(H * (0.35 + 0.05 * (k % 3)) + 40 * math.cos(t * 0.38 + ph * 0.7))
            r = 22 + (k % 4) * 10
            dr.ellipse([x - r, y - r, x + r, y + r], fill=(*R_SAGE_LIGHT, 14))
            dr.ellipse([x - r // 2, y - r // 2, x + r // 2, y + r // 2], fill=(*R_SAGE, 10))

    blur = max(4, int(round(12 * W / float(_PROD_W))))
    return layer.filter(ImageFilter.GaussianBlur(radius=blur))


def composite_peaceful_bg(img, t, style):
    motion = peaceful_motion_layer(t, style)
    return Image.alpha_composite(img.convert("RGBA"), motion).convert("RGB")


def hud_footer(img, t):
    """Minimal glass strip at bottom."""
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
    if dvs.is_available():
        return dvs.wrap_lines(text, font_path, font_px, max_w)
    f = font(font_px, False, devanagari=True)
    d_tmp = ImageDraw.Draw(Image.new("RGB", (max_w + 100, 100)))
    return wrap_text(d_tmp, text, f, max_w)


def line_reveal_alpha(t, total, n_lines, start=0.12, end=0.92):
    """Per-line fade-in that stays fully visible once revealed (no fade-out)."""
    if n_lines <= 0:
        return []
    # Each line gets a staggered start within [start*total .. end*total]
    out = []
    for i in range(n_lines):
        # line i starts revealing at start + i*(end-start)/(n_lines)
        line_start = start + i * (end - start) / max(n_lines, 1)
        line_end   = line_start + (end - start) / max(n_lines, 1) * 0.8
        out.append(smoothstep(prog(t, total * line_start, total * line_end)))
    return out


def draw_section_header(img, title, accent_rgb, t):
    """Accent rule (animated glow from center) + section title."""
    img = draw_glowing_header_bar(img, accent_rgb, t)
    fade = int(255 * smoothstep(prog(t, 0.05, 0.52)))
    if fade < 1:
        return img
    d = ImageDraw.Draw(img)
    # Pure Devanagari title
    if any('\u0900' <= c <= '\u097F' for c in title):
        hb_path = dvs.first_font_path(False) if dvs.is_available() else None
        if hb_path and fade > 8:
            return dvs.composite_line_centered(img, 148, title, hb_path, 32, R_INK, fade, canvas_w=W)
        tf = font(32, False, devanagari=True)
        return draw_text_alpha(img, (cx(d, title, tf, language="hi"), 148), title, tf, R_INK, fade)
    # Pure Latin title
    tf = font(32, True)
    return draw_text_alpha(img, (cx(d, title, tf), 148), title, tf, R_INK, fade)


# ── Section 1: Intro ──────────────────────────────────────────────────────────

def frame_intro(t, shloka, day_number, total=3.0):
    """Chapter/verse reveal with breathing rings, warm saffron grade, Om bg."""
    img = base_canvas(t).convert("RGBA")

    # Enhancement 8: warm saffron/amber color grade over the intro
    warm = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    wd = ImageDraw.Draw(warm)
    warm_a = int(38 * ease_io(prog(t, 0.0, 0.6)))
    wd.rectangle([0, 0, W, H], fill=(200, 90, 10, warm_a))
    img = Image.alpha_composite(img, warm).convert("RGB")

    # Enhancement 7: faint Om symbol behind content on intro
    img = draw_om_on_card(img, t, alpha_max=20)

    img = img.convert("RGBA")
    arc_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ad = ImageDraw.Draw(arc_layer)
    cx_, cy_ = W // 2, H // 2 - 40
    breath = 1.0 + 0.04 * breathe(t, amp=1.0, period=5.0)
    for i in range(5):
        base_r = 120 + i * 72
        r = int(base_r * breath)
        a = max(10, 55 - i * 9)
        rot = t * 14 + i * 14
        bbox = [cx_ - r, cy_ - r, cx_ + r, cy_ + r]
        ad.arc(bbox, start=int(rot) % 360, end=int(rot) % 360 + 100,
               fill=(*R_SAGE_LIGHT, min(a, 85)), width=2)
        ad.arc(bbox, start=int(rot + 130) % 360, end=int(rot + 240) % 360,
               fill=(*R_ROSE_LIGHT, min(a // 2 + 8, 45)), width=1)
    arc_layer = arc_layer.filter(ImageFilter.GaussianBlur(radius=max(1, int(round(1.2 * W / float(_PROD_W))))))
    img = Image.alpha_composite(img, arc_layer).convert("RGB")
    d = ImageDraw.Draw(img)

    p = ease_io(prog(t, 0.05, total * 0.95))

    # "Bhagavad Gita" subtitle
    subtitle = "Bhagavad Gita"
    sf = font(36, False)
    img = draw_text_alpha(img, (cx(d, subtitle, sf), int(H // 2 - 400 + 24 * (1 - p))),
                          subtitle, sf, R_SAGE, int(220 * p))
    d = ImageDraw.Draw(img)

    # Chapter title
    ch_name = shloka.get("chapter_title", "")
    if ch_name:
        cf = font(30, False)
        img = draw_text_alpha(img, (cx(d, ch_name, cf), int(H // 2 - 348 + 20 * (1 - p))),
                              ch_name, cf, R_INK_MUTED,
                              int(230 * smoothstep(prog(t, 0.15, total * 0.9))))
        d = ImageDraw.Draw(img)

    # Chapter · Verse (large)
    cv_txt = f"Chapter {shloka['chapter']}  ·  Verse {shloka['verse']}"
    for fsize in [76, 64, 54]:
        cvf = font(fsize, True)
        if tw(d, cv_txt, cvf) <= W - 100:
            break
    img = draw_text_alpha(img, (cx(d, cv_txt, cvf), int(H // 2 - 240 + 36 * (1 - p))),
                          cv_txt, cvf, R_INK,
                          int(255 * smoothstep(prog(t, 0.2, total * 0.85))))
    d = ImageDraw.Draw(img)

    # अध्याय X, श्लोक Y in Devanagari
    hb_path = dvs.first_font_path(False) if dvs.is_available() else None
    deva_txt = f"अध्याय {shloka['chapter']}, श्लोक {shloka['verse']}"
    deva_a = int(230 * smoothstep(prog(t, 0.25, total * 0.9)))
    if hb_path and deva_a > 8:
        img = dvs.composite_line_centered(img, int(H // 2 - 168 + 14 * (1 - p)),
                                          deva_txt, hb_path, 36, R_GOLD, deva_a, canvas_w=W)
    d = ImageDraw.Draw(img)

    # Day counter
    day_txt = f"Day {day_number} of 700"
    df = font(32, False)
    img = draw_text_alpha(img, (cx(d, day_txt, df), int(H // 2 - 100 + 16 * (1 - p))),
                          day_txt, df, R_GOLD,
                          int(240 * smoothstep(prog(t, 0.35, total))))
    d = ImageDraw.Draw(img)

    # Thin gold divider
    dw = int((W - 200) * smoothstep(prog(t, 0.25, total * 0.75)))
    yl = H // 2 - 36
    if dw > 6:
        img = rgba_overlay(img, lambda layer, draw: draw.rectangle(
            [W // 2 - dw // 2, yl, W // 2 + dw // 2, yl + 2], fill=(*R_GOLD_LIGHT, int(200 * p))))
        d = ImageDraw.Draw(img)

    return hud_footer(img, t)


# ── Section 2: Sanskrit Shloka ───────────────────────────────────────────────

def frame_sanskrit(t, shloka, total=5.0):
    """Sanskrit shloka with line-by-line reveal."""
    img = composite_peaceful_bg(base_canvas(t), t, "lesson")
    img = frosted_card(img, [36, 120, W - 36, H - 200], radius=32, fill_alpha=218)
    img = draw_om_on_card(img, t, alpha_max=30)
    d = ImageDraw.Draw(img)
    img = draw_section_header(img, "Shloka", R_SAGE, t)
    d = ImageDraw.Draw(img)

    sanskrit = shloka.get("sanskrit", "")
    hb_path = dvs.first_font_path(False) if dvs.is_available() else None
    for fsize in [54, 48, 42, 36, 32]:
        sf = font(fsize, False, devanagari=True)
        lines = wrap_devanagari(sanskrit, hb_path or "", fsize, W - 120) if hb_path else \
                wrap_text(d, sanskrit, sf, W - 120, language="sa")
        if len(lines) * (fsize + 22) <= 580:
            break

    n = len(lines)
    alphas = line_reveal_alpha(t, total, n, start=0.08, end=0.88)
    lh = fsize + 22
    block_h = n * lh
    sy = int(H // 2 - block_h // 2 - 20 + 8 * breathe(t, 0.2, 0.5, 6.0))

    for i, line in enumerate(lines):
        a = int(255 * alphas[i]) if i < len(alphas) else 0
        if a < 8:
            sy += lh
            continue
        rgb = tuple(int(lerp(R_INK[j], R_SAGE[j], 0.22)) for j in range(3))
        if hb_path:
            img = dvs.composite_line_centered(img, sy, line, hb_path, fsize, rgb, a, canvas_w=W)
        else:
            x = cx(d, line, sf, language="sa")
            img = draw_text_alpha(img, (x, sy), line, sf, rgb, a, language="sa")
        d = ImageDraw.Draw(img)
        sy += lh

    return hud_footer(img, t)


# ── Section 3: Hindi Explanation ─────────────────────────────────────────────

def draw_particles(img, t, trigger_t, cx_=None, cy_=None, n=28, color=None):
    """Burst of gold particles from center, triggered at trigger_t, fade over 1.2s."""
    elapsed = t - trigger_t
    if elapsed < 0 or elapsed > 1.4:
        return img
    color = color or R_GOLD
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)
    cx_ = cx_ or W // 2
    cy_ = cy_ or H // 2
    rng = np.random.default_rng(42)
    angles = rng.uniform(0, 2 * math.pi, n)
    speeds = rng.uniform(120, 380, n)
    sizes  = rng.uniform(4, 11, n)
    fade = max(0.0, 1.0 - elapsed / 1.2)
    for i in range(n):
        dist = speeds[i] * elapsed
        px = int(cx_ + math.cos(angles[i]) * dist)
        py = int(cy_ + math.sin(angles[i]) * dist)
        r = int(sizes[i] * fade)
        if r < 1:
            continue
        a = int(220 * fade * fade)
        dr.ellipse([px - r, py - r, px + r, py + r], fill=(*color, a))
    blurred = layer.filter(ImageFilter.GaussianBlur(radius=2))
    return Image.alpha_composite(img.convert("RGBA"), blurred).convert("RGB")


def frame_hindi(t, shloka, total=7.0, bridge_sec=0.0):
    """Hindi explanation — all text fades in together after bridge, particle burst on entry."""
    img = composite_peaceful_bg(base_canvas(t), t, "hindi")
    img = frosted_card(img, [36, 120, W - 36, H - 200], radius=32, fill_alpha=222)
    img = draw_om_on_card(img, t, alpha_max=28)
    d = ImageDraw.Draw(img)
    img = draw_section_header(img, "हिंदी व्याख्या", R_ROSE, t)
    d = ImageDraw.Draw(img)

    # Enhancement 2: particle burst when text starts appearing
    img = draw_particles(img, t, trigger_t=bridge_sec, cx_=W // 2, cy_=H // 2, color=R_ROSE)

    hindi = shloka.get("hindi_explanation", "")
    hb_path = dvs.first_font_path(False) if dvs.is_available() else None

    MAX_TEXT_H = H - 530
    fsize = 40
    for fsize in [40, 36, 32, 28, 24, 20]:
        lines = wrap_devanagari(hindi, hb_path or "", fsize, W - 140) if hb_path else \
                wrap_text(d, hindi, font(fsize, False, devanagari=True), W - 140, language="hi")
        lh = fsize + 18
        if len(lines) * lh <= MAX_TEXT_H:
            break

    n = len(lines)
    text_start_frac = min(0.95, bridge_sec / max(total, 1.0))
    reveal_end_frac = min(0.99, text_start_frac + 0.15)
    lh = fsize + 18
    block_h = n * lh
    card_text_top = 310
    card_text_bot = H - 220
    center_y = H // 2 - block_h // 2 + int(6 * breathe(t, 0.4, 0.45, 5.5))
    vy = max(card_text_top, min(center_y, card_text_bot - block_h))

    rgb = tuple(int(lerp(R_INK[j], R_ROSE[j], 0.15)) for j in range(3))
    for line in lines:
        a = int(255 * smoothstep(prog(t, total * text_start_frac, total * reveal_end_frac)))
        if a < 8:
            vy += lh
            continue
        if hb_path:
            img = dvs.composite_line_centered(img, vy, line, hb_path, fsize, rgb, a, canvas_w=W)
        else:
            hf = font(fsize, False, devanagari=True)
            img = draw_text_alpha(img, (cx(d, line, hf, language="hi"), vy),
                                  line, hf, rgb, a, language="hi")
        d = ImageDraw.Draw(img)
        vy += lh

    return hud_footer(img, t)


# ── Section 3: English Explanation ───────────────────────────────────────────

def frame_english(t, shloka, total=6.0, bridge_sec=0.0):
    """English explanation from english_explanation field."""
    img = composite_peaceful_bg(base_canvas(t), t, "english")
    img = frosted_card(img, [36, 120, W - 36, H - 200], radius=32, fill_alpha=218)
    d = ImageDraw.Draw(img)
    img = draw_section_header(img, "English Explanation", R_GOLD, t)
    d = ImageDraw.Draw(img)

    english = shloka.get("english_explanation", "")
    for fsize in [42, 38, 34, 30]:
        lf = font(fsize, False)
        lines = wrap_text(d, english, lf, W - 120)
        if len(lines) * (fsize + 20) <= 720:
            break

    n = len(lines)
    # All lines appear together the moment bridge voice ends, then stay visible
    text_start_sec = bridge_sec          # absolute seconds when bridge finishes
    text_start_frac = min(0.95, text_start_sec / max(total, 1.0))
    reveal_end_frac = min(0.99, text_start_frac + 0.15)  # fast 0.15-fraction fade-in
    lh = lf.size + 20
    block_h = n * lh
    ly = int(H // 2 - block_h // 2 + 6 * breathe(t, 0.6, 0.5, 6.2))

    for line in lines:
        # Single shared alpha — all lines fade in together
        a = int(255 * smoothstep(prog(t, total * text_start_frac, total * reveal_end_frac)))
        if a < 8:
            ly += lh
            continue
        img = draw_text_alpha(img, (cx(d, line, lf), ly), line, lf, R_INK, a)
        d = ImageDraw.Draw(img)
        ly += lh

    return hud_footer(img, t)


# ── Section 4: Life Lesson (Hindi + English in one frame) ────────────────────

def frame_lesson(t, shloka, total=6.0, bridge_sec=0.0, lesson_hi_dur=0.0):
    """
    Single frame showing both life_lesson_hindi and life_lesson_english.
    Text reveal is synced to audio: Hindi appears after bridge ends,
    English appears after Hindi lesson voice ends.
    """
    img = composite_peaceful_bg(base_canvas(t), t, "lesson")
    img = frosted_card(img, [36, 120, W - 36, H - 200], radius=32, fill_alpha=225)
    img = draw_om_on_card(img, t, alpha_max=28)
    d = ImageDraw.Draw(img)
    img = draw_section_header(img, "Life Lesson", R_SAGE, t)
    d = ImageDraw.Draw(img)

    # Enhancement 2: particle burst when lesson text appears
    img = draw_particles(img, t, trigger_t=bridge_sec, cx_=W // 2, cy_=H // 2, color=R_SAGE)

    hindi_lesson   = shloka.get("life_lesson_hindi", "")
    english_lesson = shloka.get("life_lesson_english", "")
    hb_path = dvs.first_font_path(False) if dvs.is_available() else None

    # ── Hindi lesson ──────────────────────────────────────────
    for h_fsize in [46, 42, 38, 34]:
        h_lines = wrap_devanagari(hindi_lesson, hb_path or "", h_fsize, W - 120) if hb_path else \
                  wrap_text(d, hindi_lesson, font(h_fsize, False, devanagari=True), W - 120, language="hi")
        if len(h_lines) * (h_fsize + 18) <= 340:
            break

    # ── English lesson ────────────────────────────────────────
    for e_fsize in [38, 34, 30, 26]:
        ef = font(e_fsize, False)
        e_lines = wrap_text(d, english_lesson, ef, W - 120)
        if len(e_lines) * (e_fsize + 18) <= 280:
            break

    h_block = len(h_lines) * (h_fsize + 18)
    e_block = len(e_lines) * (e_fsize + 18)
    sep_gap = 48
    total_block = h_block + sep_gap + e_block
    start_y = int(H // 2 - total_block // 2 + 6 * breathe(t, 0.3, 0.4, 5.8))

    # Hindi text appears right after bridge ends
    h_start_sec = bridge_sec
    h_start = min(0.95, h_start_sec / max(total, 1.0))
    h_end   = min(0.99, h_start + 0.12)
    hy = start_y
    for line in h_lines:
        a = int(255 * smoothstep(prog(t, total * h_start, total * h_end)))
        if a < 8:
            hy += h_fsize + 18
            continue
        rgb = tuple(int(lerp(R_INK[j], R_ROSE[j], 0.2)) for j in range(3))
        if hb_path:
            img = dvs.composite_line_centered(img, hy, line, hb_path, h_fsize, rgb, a, canvas_w=W)
        else:
            hf = font(h_fsize, False, devanagari=True)
            img = draw_text_alpha(img, (cx(d, line, hf, language="hi"), hy),
                                  line, hf, rgb, a, language="hi")
        d = ImageDraw.Draw(img)
        hy += h_fsize + 18

    # Separator line
    sep_y = hy + 14
    sep_a = int(160 * smoothstep(prog(t, total * h_end, total * min(0.99, h_end + 0.08))))
    if sep_a > 8:
        img = rgba_overlay(img, lambda layer, draw: draw.rectangle(
            [80, sep_y, W - 80, sep_y + 2], fill=(*R_GOLD_LIGHT, sep_a)))
        d = ImageDraw.Draw(img)

    # English lines — appear after Hindi lesson voice finishes
    e_start_sec = bridge_sec + lesson_hi_dur + 0.15
    e_start = min(0.97, e_start_sec / max(total, 1.0))
    e_end   = min(0.99, e_start + 0.12)
    ey = sep_y + sep_gap - 14
    for line in e_lines:
        a = int(255 * smoothstep(prog(t, total * e_start, total * e_end)))
        if a < 8:
            ey += e_fsize + 18
            continue
        img = draw_text_alpha(img, (cx(d, line, ef), ey), line, ef, R_INK_MUTED, a)
        d = ImageDraw.Draw(img)
        ey += e_fsize + 18

    return hud_footer(img, t)


# ── Section 5: Outro ──────────────────────────────────────────────────────────

def frame_outro(t, total=5.0):
    """
    5s outro:
      0.0–2.0s : Jai Shree Krishna (with voice) — brand name + Devanagari
      2.0–5.0s : Follow CTA fades in — handle, CTA lines, pill
    """
    img = base_canvas(t)

    # Soft bloom
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    br = int(300 + 30 * math.sin(t * 1.1))
    od.ellipse([W // 2 - br, H // 2 - 260 - br, W // 2 + br, H // 2 - 260 + br],
               fill=(*R_ROSE_LIGHT, int(55 * ease_io(prog(t, 0.0, 0.4)))))
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    d = ImageDraw.Draw(img)

    # ── Phase 1: Brand + Jai Shree Krishna (0–2s, stays visible whole outro) ──
    jai_p = smoothstep(prog(t, 0.05, 0.4))   # fast fade-in

    nf = font(82, True)
    img = draw_text_alpha(img, (cx(d, PAGE_NAME, nf), H // 2 - 260),
                          PAGE_NAME, nf, R_INK, int(255 * jai_p))
    d = ImageDraw.Draw(img)

    hb_path = dvs.first_font_path(True) if dvs.is_available() else None
    jai_deva = "जय श्री कृष्ण"
    jai_a = int(255 * jai_p)
    if hb_path and jai_a > 8:
        img = dvs.composite_line_centered(img, H // 2 - 160,
                                          jai_deva, hb_path, 56, R_GOLD, jai_a, canvas_w=W)
    else:
        jf = font(48, True)
        img = draw_text_alpha(img, (cx(d, "Jai Shree Krishna", jf), H // 2 - 160),
                              "Jai Shree Krishna", jf, R_GOLD, jai_a)
    d = ImageDraw.Draw(img)

    # ── Phase 2: CTA fades in after 2s ────────────────────────────────────────
    cta_p = smoothstep(prog(t, 2.0, 3.0))   # fades in between 2s–3s

    hf = font(32, False)
    img = draw_text_alpha(img, (cx(d, PAGE_HANDLE, hf), H // 2 - 60),
                          PAGE_HANDLE, hf, R_INK_MUTED, int(240 * cta_p))
    d = ImageDraw.Draw(img)

    for i, (line, col) in enumerate([("Follow for daily", R_INK), ("Gita wisdom & shlokas", R_SAGE)]):
        cf = font(40, i == 1)
        py = H // 2 + 20 + i * 62
        img = draw_text_alpha(img, (cx(d, line, cf), py), line, cf, col, int(235 * cta_p))
        d = ImageDraw.Draw(img)

    # Follow pill
    bw, bh = 400, 76
    bx, by = W // 2 - bw // 2, H // 2 + 180
    pill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pill)
    pd.rounded_rectangle([bx, by, bx + bw, by + bh], radius=40,
                         fill=(*R_SAGE, int(230 * cta_p)))
    img = Image.alpha_composite(img.convert("RGBA"), pill).convert("RGB")
    d = ImageDraw.Draw(img)
    if cta_p > 0.1:
        ctf = font(28, True)
        cta = "Follow now"
        img = draw_text_soft(img, (bx + (bw - tw(d, cta, ctf)) // 2, by + 22),
                             cta, ctf, (255, 255, 255), shadow=(60, 90, 75))

    return hud_footer(img, t)


# ── TTS helpers ───────────────────────────────────────────────────────────────

def generate_tts(text, lang, output_path, rate=None, pitch="-5Hz"):
    """Neural TTS via Microsoft Edge — hi-IN-MadhurNeural for all sections."""
    import re
    text = re.sub(r"^[\d\.\s।|]+", "", text).strip()
    text = text[:300]
    if not text:
        return None

    voice = "hi-IN-MadhurNeural"
    if rate is None:
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


def pick_background_track(bot_dir):
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

    hit = scan_dir(os.path.join(bot_dir, MUSIC_DIR))
    return hit or scan_dir(bot_dir)


# ── Main entry point ──────────────────────────────────────────────────────────

def create_shloka_reel(shloka, output_path, day_number=1, fast_preview=False):
    """
    Generate shloka reel from gita_data.json entry.

    Flow:
      intro  →  sanskrit  →  hindi_explanation  →  life_lesson  →  outro

    TTS voices:
      intro        : "Geeta ka gyaan..." hook + "adhyay X, shlok Y"
      bridge_hindi : "Aayiye, iss shloka ki Hindi vyakhya samajhte hain."
      hindi        : hindi_explanation
      bridge_lesson: "Aur iska jeevan sandesh hai..."
      lesson_hi    : life_lesson_hindi
      lesson_en    : life_lesson_english (English TTS)
      jai          : "Jai Shree Krishna"

    Speed: final video is played at 1.2x (video + audio both sped up).
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
        ch, v = shloka["chapter"], shloka["verse"]
        print(f"  Shloka: BG {ch}.{v}")

        DURATIONS = {
            "intro":    10.0,
            "sanskrit":  6.0,
            "hindi":     7.0,
            "lesson":    6.0,
            "outro":     3.0,
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

        # ── TTS generation ────────────────────────────────────────────────────
        print("  Generating TTS...")
        tts_dir = os.path.join(os.path.dirname(os.path.abspath(output_path)), "tts")
        os.makedirs(tts_dir, exist_ok=True)

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
                shloka.get("sanskrit", "").replace("\n", " "),
                "hi", os.path.join(tts_dir, "tts_sanskrit.mp3"), rate="-22%"
            ),
            "bridge_hindi": generate_tts(
                "Aayiye, iss shloka ki Hindi vyakhya samajhte hain.",
                "hi", os.path.join(tts_dir, "tts_bridge_hindi.mp3"), rate="-5%"
            ),
            "hindi": generate_tts(
                shloka.get("hindi_explanation", ""),
                "hi", os.path.join(tts_dir, "tts_hindi.mp3"), rate="-16%"
            ),
            "bridge_lesson": generate_tts(
                "Is shloka se hame ye sikhna chahiye ki",
                "hi", os.path.join(tts_dir, "tts_bridge_lesson.mp3"), rate="-5%"
            ),
            "lesson_hi": generate_tts(
                shloka.get("life_lesson_hindi", ""),
                "hi", os.path.join(tts_dir, "tts_lesson_hi.mp3"), rate="-18%"
            ),
            "lesson_en": generate_tts(
                shloka.get("life_lesson_english", ""),
                "en", os.path.join(tts_dir, "tts_lesson_en.mp3"), rate="+5%"
            ),
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

        # Intro: hook + 0.4s + chapter/verse + 2s breathing room
        intro_tts = _dur("intro") + 0.4 + _dur("chapter_verse")
        actual["intro"] = max(8.5, intro_tts + 2.0)
        print(f"  TTS intro: {intro_tts:.1f}s → {actual['intro']:.1f}s")

        # Sanskrit: shloka reading + 0.3s tail (bridge_hindi starts right after)
        san = _dur("sanskrit")
        actual["sanskrit"] = max(DURATIONS["sanskrit"], san + 0.3)
        print(f"  TTS sanskrit: {san:.1f}s → {actual['sanskrit']:.1f}s")

        # Hindi: bridge + 0.15s + explanation + 0.5s tail
        bh = _dur("bridge_hindi")
        hi = _dur("hindi")
        actual["hindi"] = max(bh + 0.15 + hi + 0.5, 4.0)
        print(f"  TTS hindi: bridge({bh:.1f}s) + explanation({hi:.1f}s) → {actual['hindi']:.1f}s")

        # Lesson: bridge + 0.15s + hindi lesson + 0.15s + english lesson + 4.0s tail
        bl = _dur("bridge_lesson")
        lh_dur = _dur("lesson_hi")
        le_dur = _dur("lesson_en")
        actual["lesson"] = max(bl + 0.15 + lh_dur + 0.15 + le_dur + 4.0, 4.0)
        print(f"  TTS lesson: bridge({bl:.1f}s) + hi({lh_dur:.1f}s) + en({le_dur:.1f}s) → {actual['lesson']:.1f}s")

        # Outro: fixed 5s, jai fires at start
        jai = _dur("jai")
        actual["outro"] = 5.0
        print(f"  TTS jai: {jai:.1f}s → outro {actual['outro']:.1f}s")

        # ── Video clips ───────────────────────────────────────────────────────
        print("  Rendering video sections...")
        clips = [
            make_clip(frame_intro,    actual["intro"],    shloka=shloka, day_number=day_number, total=actual["intro"]),
            make_clip(frame_sanskrit, actual["sanskrit"], shloka=shloka, total=actual["sanskrit"]),
            make_clip(frame_hindi,    actual["hindi"],    shloka=shloka, total=actual["hindi"],   bridge_sec=bh + 0.15),
            make_clip(frame_lesson,   actual["lesson"],   shloka=shloka, total=actual["lesson"], bridge_sec=bl + 0.15 + 1.05 + 1.0, lesson_hi_dur=lh_dur),
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
            # Hindi: bridge → 0.15s → explanation → pad
            build_section([("bridge_hindi", 0.15), ("hindi", 0.0)], actual["hindi"]),
            # Lesson: bridge → 0.15s → hindi lesson → 0.15s → english lesson → pad
            build_section([("bridge_lesson", 0.15), ("lesson_hi", 0.15), ("lesson_en", 0.0)], actual["lesson"]),
            # Outro: Jai Shree Krishna fires immediately, CTA is visual only
            build_section([("jai", 0.0)], actual["outro"]),
        ]

        tts_audio = concatenate_audioclips(audio_parts)

        # ── Background music ──────────────────────────────────────────────────
        bot_dir = os.path.dirname(os.path.abspath(__file__))
        bg_path = pick_background_track(bot_dir)

        SPEED = 1.2
        sped_dur = total_dur / SPEED

        # ── Speed up TTS audio via rubberband (tempo up, pitch preserved) ────
        # Write raw TTS to a temp file, then use ffmpeg rubberband filter to
        # stretch tempo without pitch shift, producing natural-sounding fast voice.
        print("  Applying rubberband tempo stretch to TTS audio...")
        from moviepy.config import FFMPEG_BINARY
        import subprocess, tempfile

        raw_tts_path = os.path.join(tts_dir, "_tts_raw.wav")
        stretched_tts_path = os.path.join(tts_dir, "_tts_stretched.wav")
        tts_audio.write_audiofile(raw_tts_path, fps=44100, logger=None)

        rb_cmd = [
            FFMPEG_BINARY, "-y", "-i", raw_tts_path,
            "-af", f"rubberband=tempo={SPEED}:pitch=1.0",
            stretched_tts_path
        ]
        try:
            subprocess.run(rb_cmd, check=True, capture_output=True)
            tts_final = AudioFileClip(stretched_tts_path)
            print(f"  [✓] Rubberband stretch: {total_dur:.1f}s → {tts_final.duration:.1f}s (pitch preserved)")
        except Exception as e:
            print(f"  [!] Rubberband failed ({e}), falling back to atempo")
            # atempo fallback — max factor per filter is 2.0, chain if needed
            atempo = SPEED if SPEED <= 2.0 else 2.0
            atempo_filter = f"atempo={atempo}"
            fb_cmd = [
                FFMPEG_BINARY, "-y", "-i", raw_tts_path,
                "-af", atempo_filter,
                stretched_tts_path
            ]
            subprocess.run(fb_cmd, check=True, capture_output=True)
            tts_final = AudioFileClip(stretched_tts_path)

        # ── Background music (trimmed to sped duration) ───────────────────────
        if bg_path and os.path.isfile(bg_path):
            try:
                from moviepy import CompositeAudioClip
                probe = AudioFileClip(bg_path)
                clip_len = float(probe.duration)
                probe.close()
                if clip_len + 0.01 < sped_dur:
                    loops, rem = [], sped_dur
                    while rem > 1e-3:
                        seg = min(rem, clip_len)
                        loops.append(AudioFileClip(bg_path).subclipped(0, seg))
                        rem -= seg
                    bg = concatenate_audioclips(loops)
                else:
                    bg = AudioFileClip(bg_path).subclipped(0, min(sped_dur, clip_len))
                bg = bg.with_volume_scaled(0.25)
                final_audio = CompositeAudioClip([tts_final, bg])
                print(f"  [✓] TTS + music ({os.path.basename(bg_path)}) @ 25%")
            except Exception as e:
                print(f"  [!] Music skipped: {e}")
                final_audio = tts_final
        else:
            final_audio = tts_final
            print("  [✓] TTS only (no music file found)")

        # ── Speed up video frames only (no audio), attach stretched audio ─────
        video_fast = video.with_speed_scaled(SPEED)
        video_fast = video_fast.with_audio(final_audio)

        print(f"  Writing video ({total_dur:.1f}s → {sped_dur:.1f}s at {SPEED}x)...")
        video_fast.write_videofile(
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
