"""
Devanagari font loading with OpenType shaping (libraqm) when Pillow supports it.
Without Raqm, matras/conjuncts often render incorrectly for Hindi and Sanskrit.

Compatible across Pillow versions: LAYOUT_* constants were added in Pillow 8;
some builds expose Raqm without exporting LAYOUT_BASIC on ImageFont.
"""

import os
import warnings
from typing import Any, Optional

from PIL import ImageFont, features

_BOT_DIR = os.path.dirname(os.path.abspath(__file__))
_FONTS_DIR = os.path.join(_BOT_DIR, "fonts")
_RAQM_WARNED = False


def _layout_engine_kw() -> Optional[Any]:
    """
    Return the value to pass as layout_engine=... to ImageFont.truetype,
    or None to omit the argument (Pillow's default / basic layout).
    """
    global _RAQM_WARNED
    if not features.check("raqm"):
        if not _RAQM_WARNED:
            warnings.warn(
                "Pillow was built without libraqm: Hindi/Sanskrit shaping may be wrong "
                "(broken matras, reph, conjuncts). Install a Pillow build with Raqm, "
                "or install libraqm and rebuild Pillow. See Pillow installation docs.",
                UserWarning,
                stacklevel=3,
            )
            _RAQM_WARNED = True
        return None

    # Pillow 8+: ImageFont.LAYOUT_RAQM; avoid LAYOUT_BASIC (missing on some builds).
    raqm = getattr(ImageFont, "LAYOUT_RAQM", None)
    if raqm is not None:
        return raqm
    return 1


def truetype_compat(path: str, size_px: int) -> ImageFont.ImageFont:
    """Load TTF with complex-script shaping when Raqm is available."""
    le = _layout_engine_kw()
    try:
        if le is not None:
            return ImageFont.truetype(path, size_px, layout_engine=le)
        return ImageFont.truetype(path, size_px)
    except TypeError:
        return ImageFont.truetype(path, size_px)


def raqm_text_kwargs(
    language: Optional[str] = None,
    direction: Optional[str] = None,
    ot_features: Optional[str] = None,
) -> dict[str, Any]:
    """
    Kwargs for ImageDraw.text / textbbox / ImageFont.getbbox.
    Pillow raises if language/direction/features are set without libraqm — omit them.
    """
    if not features.check("raqm"):
        return {}
    out: dict[str, Any] = {}
    if language is not None:
        out["language"] = language
    if direction is not None:
        out["direction"] = direction
    if ot_features is not None:
        out["features"] = ot_features
    return out


def devanagari_search_paths(bold: bool = False, prefer_serif_for_hindi: bool = False) -> list[str]:
    """
    prefer_serif_for_hindi: try Noto Serif Devanagari first (Hindi prose), then Sans.
    """
    sans_r = os.path.join(_FONTS_DIR, "NotoSansDevanagari-Regular.ttf")
    sans_b = os.path.join(_FONTS_DIR, "NotoSansDevanagari-Bold.ttf")
    serif_r = os.path.join(_FONTS_DIR, "NotoSerifDevanagari-Regular.ttf")
    serif_b = os.path.join(_FONTS_DIR, "NotoSerifDevanagari-Bold.ttf")
    sans_sys = (
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"
    )
    paths: list[str] = []
    if prefer_serif_for_hindi:
        paths.append(serif_b if bold else serif_r)
    paths.extend(
        [
            sans_b if bold else sans_r,
            sans_sys,
            "C:/Windows/Fonts/Nirmala.ttf",
            "C:/Windows/Fonts/mangal.ttf",
        ]
    )
    return paths
