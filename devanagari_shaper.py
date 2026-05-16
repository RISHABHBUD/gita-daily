"""
Devanagari via HarfBuzz + FreeType — matches JSON Unicode clusters without Pillow Raqm.

Install: pip install uharfbuzz freetype-py
"""

from __future__ import annotations

import os
import unicodedata
from functools import lru_cache
from typing import Optional, Tuple

try:
    import freetype as ft
    import uharfbuzz as hb
except ImportError:
    ft = None  # type: ignore
    hb = None  # type: ignore


def is_available() -> bool:
    return hb is not None and ft is not None


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


@lru_cache(maxsize=32)
def _hb_font(path: str, font_px: int) -> hb.Font:
    blob = hb.Blob.from_file_path(path)
    face = hb.Face(blob)
    f = hb.Font(face)
    f.scale = (font_px * 64, font_px * 64)
    return f


def _ft_face(path: str, font_px: int) -> "ft.Face":
    # Never cache — ft.Face is mutated by load_glyph() on every call.
    # Caching causes stale glyph bitmap data and wrong rendering.
    face = ft.Face(path)
    face.set_pixel_sizes(0, font_px)
    return face


def _shape(path: str, font_px: int, text: str) -> hb.Buffer:
    text = _nfc(text)
    f = _hb_font(path, font_px)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(f, buf)
    return buf


def line_width_px(font_path: str, font_px: int, text: str) -> int:
    if not is_available():
        return 0
    buf = _shape(font_path, font_px, text)
    w = 0
    for pos in buf.glyph_positions:
        w += pos.x_advance >> 6
    return max(0, w)


def wrap_lines(text: str, font_path: str, font_px: int, max_width: int) -> list[str]:
    if not is_available() or max_width <= 0:
        return [text] if text else []
    text = _nfc(text)
    words = text.replace("\n", " \n ").split()
    lines: list[str] = []
    cur = ""
    for w in words:
        if w == "\n":
            if cur:
                lines.append(cur)
            cur = ""
            continue
        test = (cur + " " + w).strip()
        if line_width_px(font_path, font_px, test) <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_line_rgba(
    font_path: str,
    font_px: int,
    text: str,
    rgb: Tuple[int, int, int],
    alpha: int = 255,
) -> Optional["Image.Image"]:
    from PIL import Image

    if not is_available():
        return None
    text = _nfc(text)
    buf = _shape(font_path, font_px, text)
    face = _ft_face(font_path, font_px)
    asc = face.size.ascender >> 6

    pen_x = 0
    min_x = 0
    max_x = 0
    min_y = 10**9
    max_y = -(10**9)
    glyphs: list[tuple] = []

    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        gid = info.codepoint
        face.load_glyph(gid, ft.FT_LOAD_RENDER)
        bm = face.glyph.bitmap
        left = face.glyph.bitmap_left
        top = face.glyph.bitmap_top
        gx = pen_x + (pos.x_offset >> 6) + left
        gy = asc - top - (pos.y_offset >> 6)
        if bm.rows and bm.width:
            # Snapshot buffer immediately — bm is a reference to the face's
            # internal glyph slot, overwritten by the next load_glyph() call.
            glyphs.append((list(bm.buffer), bm.width, bm.rows, bm.pitch, gx, gy))
            min_x = min(min_x, gx)
            max_x = max(max_x, gx + bm.width)
            min_y = min(min_y, gy)
            max_y = max(max_y, gy + bm.rows)
        pen_x += pos.x_advance >> 6

    max_x = max(max_x, pen_x)
    if not glyphs:
        wpx = max(1, pen_x) + 4
        hpx = asc + ((-face.size.descender) >> 6) + 4
        return Image.new("RGBA", (wpx, hpx), (0, 0, 0, 0))

    min_x -= 2
    min_y -= 2
    max_x += 2
    max_y += 2
    wpx = max(1, max_x - min_x)
    hpx = max(1, max_y - min_y)
    img = Image.new("RGBA", (wpx, hpx), (0, 0, 0, 0))
    px = img.load()
    r, g, b = rgb
    a = max(0, min(255, int(alpha)))

    for buf_data, bw, br, pitch, gx, gy in glyphs:
        x0 = gx - min_x
        y0 = gy - min_y
        for row in range(br):
            for col in range(bw):
                v = buf_data[row * pitch + col]
                if not v:
                    continue
                x, y = x0 + col, y0 + row
                if 0 <= x < wpx and 0 <= y < hpx:
                    ca = v * a // 255
                    if ca:
                        px[x, y] = (r, g, b, ca)
    return img


def first_font_path(bold: bool = False) -> Optional[str]:
    from font_helper import devanagari_search_paths

    for p in devanagari_search_paths(bold=bold, prefer_serif_for_hindi=False):
        if os.path.isfile(p):
            return p
    return None


def composite_line_centered(
    base: "Image.Image",
    y_pil: int,
    text: str,
    font_path: str,
    font_px: int,
    rgb: Tuple[int, int, int],
    alpha: int = 255,
    canvas_w: Optional[int] = None,
) -> "Image.Image":
    """Center shaped strip horizontally on ``canvas_w`` (default ``base.width``).

    Uses the HarfBuzz-rendered strip dimensions for centering — PIL textbbox
    without Raqm gives wrong metrics for Devanagari (over-measures by ~15-35%),
    which causes misaligned Hindi text.
    """
    from PIL import Image

    if not is_available():
        return base
    w = canvas_w if canvas_w is not None else base.width
    strip = render_line_rgba(font_path, font_px, text, rgb, alpha)
    if strip is None:
        return base
    # Use strip.width directly — it's the actual shaped pixel width from HarfBuzz.
    # Do NOT use PIL textbbox here: without Raqm it measures unshaped codepoints
    # and gives a width ~15-35% larger than the real rendered text.
    paste_x = (w - strip.width) // 2
    paste_y = y_pil

    base_rgba = base.convert("RGBA")
    layer = Image.new("RGBA", base_rgba.size, (0, 0, 0, 0))
    layer.paste(strip, (int(paste_x), int(paste_y)), strip)
    out = Image.alpha_composite(base_rgba, layer)
    return out.convert(base.mode)


def composite_on_pil_xy(
    base: "Image.Image",
    x_pil: int,
    y_pil: int,
    text: str,
    font_path: str,
    font_px: int,
    rgb: Tuple[int, int, int],
    alpha: int = 255,
) -> "Image.Image":
    """
    Paste shaped strip at (x_pil, y_pil).
    Uses strip dimensions directly — PIL textbbox without Raqm gives wrong
    metrics for Devanagari and must not be used for offset calculation.
    """
    from PIL import Image

    if not is_available():
        return base
    strip = render_line_rgba(font_path, font_px, text, rgb, alpha)
    if strip is None:
        return base
    # Use x_pil/y_pil directly as the top-left paste anchor.
    paste_x = x_pil
    paste_y = y_pil

    base_rgba = base.convert("RGBA")
    layer = Image.new("RGBA", base_rgba.size, (0, 0, 0, 0))
    layer.paste(strip, (int(paste_x), int(paste_y)), strip)
    out = Image.alpha_composite(base_rgba, layer)
    return out.convert(base.mode)
