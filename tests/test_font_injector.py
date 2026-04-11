from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from src.backend.app_backend import AppBackend
from src.utils.font_injector import FontInjector
from src.tools.font_helper import FontHelper, check_font_for_project


def test_font_injector_rpy_contains_style_and_cache_updates(tmp_path: Path) -> None:
    injector = FontInjector()
    rpy_path = tmp_path / "zzz_renlocalizer_font.rpy"

    injector._update_rpy_script(rpy_path, "vietnamese", "tl/renlocalizer_fonts/NotoSans-Regular.ttf", False)

    content = rpy_path.read_text(encoding="utf-8")
    assert "renpy.text.font.get_font = renlocalizer_get_font_hook" in content
    assert "for _gui_field in" in content
    assert "for _style_name in" in content
    assert "renpy.text.font.font_cache.clear()" in content
    assert "renpy.text.font.font_names.clear()" in content
    assert "renpy.restart_interaction()" in content
    assert "glyph_font" in content


def test_font_injector_rpy_sets_rtl_support_for_rtl_languages(tmp_path: Path) -> None:
    injector = FontInjector()
    rpy_path = tmp_path / "zzz_renlocalizer_font.rpy"

    injector._update_rpy_script(rpy_path, "persian", "tl/renlocalizer_fonts/Vazirmatn-Regular.ttf", True)

    content = rpy_path.read_text(encoding="utf-8")
    assert "config.rtl = True" in content
    assert 'reading_order = "wrtl"' in content
    assert 'language = "unicode"' in content


def test_font_map_list_uses_primary_fallback_candidate() -> None:
    injector = FontInjector()
    mapping = {item["lang"]: item for item in injector.get_font_map_list()}
    assert mapping["vi"]["font"] == "Be Vietnam Pro"
    assert mapping["ar"]["font"] == "Noto Sans Arabic"


def test_font_check_uses_selected_target_language() -> None:
    config = SimpleNamespace(
        translation_settings=SimpleNamespace(target_language="vietnamese"),
        get_ui_text=lambda key, default=None, **kwargs: default or key,
    )
    backend = cast(Any, AppBackend.__new__(AppBackend))
    backend.config = config

    captured = {}

    def fake_check(path: str, language: str, verbose: bool = False):
        captured["path"] = path
        captured["language"] = language
        return {"fonts_checked": 1, "compatible_fonts": 1, "incompatible_fonts": 0}

    import src.tools.font_helper as font_helper

    original = font_helper.check_font_for_project
    font_helper.check_font_for_project = fake_check
    try:
        summary = backend.fontCheck("D:/games/sample")
    finally:
        font_helper.check_font_for_project = original

    assert captured["language"] == "vietnamese"
    assert "Checked: 1" in summary


def test_font_helper_detects_static_font_risks(tmp_path: Path) -> None:
    game_dir = tmp_path / "game"
    game_dir.mkdir()
    script_path = game_dir / "screens.rpy"
    script_path.write_text(
        '\n'.join(
            [
                'style custom_text font "SomeFont.ttf"',
                'define e = Character("Eileen", what_font="VNFont.ttf")',
                'screen demo():',
                '    text "Hello" font "Direct.ttf"',
                '    text "{font=Tagged.ttf}Tagged{/font}"',
                'init python:',
                '    config.font_name_map["vn"] = "VN.ttf"',
            ]
        ),
        encoding="utf-8",
    )

    helper = FontHelper()
    report = helper.analyze_font_risks(str(game_dir))

    assert report["total_findings"] >= 4
    assert report["counts"]["style_font"] >= 1
    assert report["counts"]["what_font"] >= 1
    assert report["counts"]["font_tag"] >= 1
    assert report["counts"]["font_name_map"] >= 1


def test_check_font_for_project_includes_risk_report(tmp_path: Path) -> None:
    game_dir = tmp_path / "game"
    game_dir.mkdir()
    (game_dir / "script.rpy").write_text('define e = Character("Eileen", who_font="VN.ttf")', encoding="utf-8")

    summary = check_font_for_project(str(game_dir), "vietnamese", verbose=False)
    assert "risk_report" in summary
    assert summary["risk_report"]["total_findings"] >= 1
