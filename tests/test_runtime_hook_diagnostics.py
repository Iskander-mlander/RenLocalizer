# -*- coding: utf-8 -*-

from types import SimpleNamespace
from pathlib import Path

from src.core.runtime_hook_template import render_runtime_hook
from src.core.translation_pipeline import TranslationPipeline


def test_render_runtime_hook_includes_runtime_diagnostics_flag() -> None:
    content = render_runtime_hook("turkish", runtime_string_diagnostics=True, runtime_miss_limit=42)

    assert "_rl_runtime_string_diagnostics = True" in content
    assert "_rl_runtime_miss_limit = 42" in content
    assert 'lang = "turkish"' in content
    assert 'runtime_missed_strings.jsonl' in content
    assert 'hotkey_visible_form_miss' in content
    assert 'corruption_driven_miss' in content
    assert 'def _rl_ensure_language_sync():' in content
    assert '_rl_loaded_language = _rl_get_active_language()' in content


def test_render_runtime_hook_disables_runtime_diagnostics_flag() -> None:
    content = render_runtime_hook("turkish", runtime_string_diagnostics=False)

    assert "_rl_runtime_string_diagnostics = False" in content


def test_manage_runtime_hook_writes_runtime_diagnostics_flag(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    game_dir = project_dir / "game"
    game_dir.mkdir(parents=True)

    config = SimpleNamespace(
        translation_settings=SimpleNamespace(
            auto_generate_hook=True,
            force_runtime_translation=False,
            target_language="tr",
            runtime_string_diagnostics=True,
        ),
        get_ui_text=lambda key: key,
    )

    pipeline = TranslationPipeline(config, object())
    pipeline.project_path = str(project_dir)
    pipeline.target_language = "turkish"
    pipeline._manage_runtime_hook()

    hook_path = game_dir / "zzz_renlocalizer_runtime.rpy"
    hook_text = hook_path.read_text(encoding="utf-8")
    assert "_rl_runtime_string_diagnostics = True" in hook_text


def test_manage_runtime_hook_respects_enable_runtime_hook_flag(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    game_dir = project_dir / "game"
    game_dir.mkdir(parents=True)

    config = SimpleNamespace(
        translation_settings=SimpleNamespace(
            auto_generate_hook=True,
            enable_runtime_hook=False,
            force_runtime_translation=False,
            target_language="tr",
            runtime_string_diagnostics=False,
        ),
        get_ui_text=lambda key: key,
    )

    pipeline = TranslationPipeline(config, object())
    pipeline.project_path = str(project_dir)
    pipeline.target_language = "turkish"
    pipeline._manage_runtime_hook()

    assert not (game_dir / "zzz_renlocalizer_runtime.rpy").exists()
