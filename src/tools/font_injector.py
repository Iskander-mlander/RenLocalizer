# -*- coding: utf-8 -*-
"""
Font Injector Module (Google Fonts API Integration)
===================================================

Automatically downloads and injects compatible fonts for specific languages 
into Ren'Py projects. Uses Google Fonts download endpoint.
"""

import os
import requests
import logging
import zipfile
import io
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple, List, Any

logger = logging.getLogger(__name__)

# Mapping: Language Code -> ordered fallback candidates (Font Family, Is RTL?)
FONT_CANDIDATES: Dict[str, Tuple[Tuple[str, bool], ...]] = {
    "fa": (("Vazirmatn", True), ("Noto Sans Arabic", True)),
    "ar": (("Noto Sans Arabic", True), ("Cairo", True), ("Tajawal", True)),
    "he": (("Noto Sans Hebrew", True), ("Rubik", True), ("Heebo", True)),
    "ja": (("Noto Sans JP", False), ("M PLUS 1p", False), ("Kosugi Maru", False)),
    "zh": (("Noto Sans SC", False),),
    "zh_tw": (("Noto Sans TC", False),),
    "ko": (("Noto Sans KR", False), ("Nanum Gothic", False)),
    "ru": (("Noto Sans", False), ("PT Sans", False), ("Ubuntu", False)),
    "th": (("Noto Sans Thai", False), ("Sarabun", False), ("Prompt", False)),
    "tr": (("Noto Sans", False), ("Inter", False), ("Open Sans", False)),
    "uk": (("Noto Sans", False), ("PT Sans", False), ("Ubuntu", False)),
    "vi": (("Be Vietnam Pro", False), ("Noto Sans", False), ("Inter", False)),
}

LANG_NAME_TO_CODE: Dict[str, str] = {
    "turkish": "tr", "russian": "ru", "japanese": "ja", "chinese": "zh",
    "schinese": "zh", "tchinese": "zh_tw", "korean": "ko", "english": "en",
    "french": "fr", "german": "de", "spanish": "es", "italian": "it",
    "portuguese": "pt", "arabic": "ar", "persian": "fa", "hebrew": "he",
    "thai": "th", "vietnamese": "vi", "ukrainian": "uk",
}

GUI_FONT_FIELDS = (
    "text_font", "name_text_font", "interface_text_font",
    "button_text_font", "choice_button_text_font",
    "system_font", "glyph_font",
)

STYLE_FONT_NAMES = (
    "default", "say_dialogue", "say_label", "input", "button_text",
    "choice_button_text", "namebox", "notify_text", "history_text",
    "confirm_prompt_text", "navigation_button_text", "quick_button_text",
)

RTL_STYLE_NAMES = (
    "default", "say_dialogue", "say_label", "input", "button_text",
    "choice_button_text", "history_text", "namebox", "notify_text",
)


def _normalize_lang_code(lang_code: str) -> str:
    lower = lang_code.lower().strip()
    if lower in LANG_NAME_TO_CODE:
        return LANG_NAME_TO_CODE[lower]
    base = lower.split('-')[0]
    if lower in ("zh-cn", "zh_cn", "zh-hans", "schinese"):
        return "zh"
    if lower in ("zh-tw", "zh_tw", "zh-hant", "tchinese"):
        return "zh_tw"
    return base


def _download_font(font_family: str, target_dir: Path) -> Tuple[bool, str]:
    font_id = font_family.lower().strip().replace(' ', '-')
    subsets = "latin,latin-ext,cyrillic,cyrillic-ext,greek,greek-ext,vietnamese"
    urls = [
        f"https://gwfh.mranftl.com/api/fonts/{font_id}?download=zip&subsets={subsets}&variants=regular,400,500,700",
        f"https://api.fontsource.org/v1/fonts/{font_id}/download",
    ]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}

    for url in urls:
        try:
            resp = requests.get(url, headers=headers, timeout=60)
            if resp.status_code != 200:
                continue
            if len(resp.content) < 1000:
                continue
            z = zipfile.ZipFile(io.BytesIO(resp.content))
            font_files = [f for f in z.namelist() if f.lower().endswith(('.ttf', '.otf'))]
            if not font_files:
                continue
            regulars = [f for f in font_files if "regular" in f.lower() or "-400" in f.lower()]
            best = regulars[0] if regulars else font_files[0]
            target = target_dir / os.path.basename(best)
            with open(target, "wb") as dst:
                shutil.copyfileobj(z.open(best), dst)
            logger.info(f"Downloaded font: {target}")
            return True, os.path.basename(best)
        except Exception as e:
            logger.warning(f"Font download failed ({url}): {e}")
            continue
    return False, ""


def inject_font(game_dir: str, lang_code: str) -> Dict[str, Any]:
    base_lang = _normalize_lang_code(lang_code)

    if base_lang not in FONT_CANDIDATES:
        return {"success": False, "message": f"No auto font mapping for '{lang_code}'"}

    candidates = FONT_CANDIDATES[base_lang]
    game_path = Path(game_dir)
    if (game_path / "game").exists():
        game_path = game_path / "game"

    fonts_dir = game_path / "tl" / "renlocalizer_fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)

    font_family = candidates[0][0]
    is_rtl = candidates[0][1]
    font_filename = ""

    for candidate_font, candidate_rtl in candidates:
        ok, fname = _download_font(candidate_font, fonts_dir)
        if ok:
            font_family = candidate_font
            is_rtl = candidate_rtl
            font_filename = fname
            break

    if not font_filename:
        return {"success": False, "message": "Could not download any font candidate."}

    rpy_path = game_path / "zzz_renlocalizer_font.rpy"
    font_rel = f"tl/renlocalizer_fonts/{font_filename}"

    block = f'''
init -999 python:
    if not hasattr(renpy.store, "renlocalizer_fonts"):
        renpy.store.renlocalizer_fonts = {{}}
    if not hasattr(renpy.store, "orig_get_font"):
        renpy.store.orig_get_font = renpy.text.font.get_font
        def renlocalizer_get_font_hook(*args, **kwargs):
            if not args:
                return renpy.store.orig_get_font(*args, **kwargs)
            current_lang = _preferences.language
            fs = renpy.store.renlocalizer_fonts
            if current_lang in fs and args[0] != fs[current_lang].get("Default", ""):
                args = (fs[current_lang]["Default"],) + args[1:]
            return renpy.store.orig_get_font(*args, **kwargs)
        renpy.text.font.get_font = renlocalizer_get_font_hook

translate {lang_code} python:
    if not hasattr(renpy.store, "renlocalizer_fonts"):
        renpy.store.renlocalizer_fonts = {{}}
    renpy.store.renlocalizer_fonts["{lang_code}"] = {{"Default": "{font_rel}"}}
    for _f in {list(GUI_FONT_FIELDS)}:
        try:
            if hasattr(gui, _f): setattr(gui, _f, "{font_rel}")
        except: pass
    for _s in {list(STYLE_FONT_NAMES)}:
        try:
            _st = getattr(style, _s, None)
            if _st: _st.font = "{font_rel}"
        except: pass
    if {is_rtl!r}:
        try: gui.language = "unicode"; config.rtl = True
        except: pass
        for _rs in {list(RTL_STYLE_NAMES)}:
            try:
                _rst = getattr(style, _rs, None)
                if _rst: _rst.language = "unicode"; _rst.reading_order = "wrtl"
            except: pass
    try:
        if hasattr(renpy.text.font, "font_cache"): renpy.text.font.font_cache.clear()
        if hasattr(renpy.text.font, "font_names"): renpy.text.font.font_names.clear()
    except: pass
    style.rebuild()
    try: renpy.restart_interaction()
    except: pass
'''

    with open(rpy_path, 'w', encoding='utf-8') as f:
        f.write(block)

    return {
        "success": True,
        "message": f"Font {font_family} injected for {lang_code}",
        "font": font_family,
        "path": str(rpy_path),
    }
