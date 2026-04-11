# -*- coding: utf-8 -*-

import json
import sys
import tempfile
from types import ModuleType
from types import SimpleNamespace
from pathlib import Path
from typing import Any, cast

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
    assert '"source_kind": source_kind' in content
    assert '"active_screen": active_screen' in content
    assert '"statement_name": statement_name' in content
    assert '"normalized": normalized_text' in content
    assert 'def _rl_interact_callback():' in content
    assert '_rl_replace_cache = {}' in content
    assert "config.start_interact_callbacks.append(_rl_interact_callback)" in content


def _exec_runtime_hook_python_block(language: str = "turkish") -> dict:
    hook_code = render_runtime_hook(language, runtime_string_diagnostics=True, runtime_miss_limit=42)
    lines = hook_code.splitlines()
    body_lines = []
    in_python_block = False
    for line in lines:
        if line.startswith("init ") and "python:" in line:
            in_python_block = True
            continue
        if in_python_block:
            if line.startswith("    "):
                body_lines.append(line[4:])
            elif line.strip() == "":
                body_lines.append("")
            else:
                break

    class MockScreen:
        name = "say"

    mock_renpy = cast(Any, ModuleType("renpy"))
    mock_renpy.loader = SimpleNamespace(game_apks=[])
    mock_renpy.get_statement_name = lambda: "say"
    mock_renpy.current_screen = lambda: MockScreen()
    mock_renpy.get_screen = lambda name: MockScreen() if name == "say" else None

    MockPreferences = cast(Any, type("MockPreferences", (), {"language": language}))

    class MockConfig:
        gamedir = ""
        say_menu_text_filter = None
        replace_text = None
        all_character_callbacks = []

    sys.modules["renpy"] = mock_renpy
    ns = {
        "renpy": sys.modules["renpy"],
        "config": MockConfig(),
        "_preferences": MockPreferences(),
    }
    body = "\n".join(body_lines).replace("global _rl_prev_say_menu_filter, _rl_prev_replace_text", "")
    exec(body, ns)
    return ns


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

    pipeline = TranslationPipeline(cast(Any, config), cast(Any, object()))
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

    pipeline = TranslationPipeline(cast(Any, config), cast(Any, object()))
    pipeline.project_path = str(project_dir)
    pipeline.target_language = "turkish"
    pipeline._manage_runtime_hook()

    assert not (game_dir / "zzz_renlocalizer_runtime.rpy").exists()


def test_runtime_miss_log_includes_metadata_fields() -> None:
    ns = _exec_runtime_hook_python_block()

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        diag_dir = tmp_path / "tl" / "turkish" / "diagnostics"
        diag_dir.mkdir(parents=True)

        ns["config"].gamedir = str(tmp_path)
        ns["_rl_loaded"] = True
        ns["_rl_loaded_language"] = "turkish"
        ns["_rl_translated_values"] = set()
        ns["_rl_runtime_miss_logged"] = set()

        ns["_rl_log_runtime_miss"](
            "replace_text",
            "And the continuation of this story is being created right now.",
            "no_exact_match_post_interpolation",
        )

        log_path = diag_dir / "runtime_missed_strings.jsonl"
        payload = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
        assert payload["source_kind"] == "dialogue"
        assert payload["active_language"] == "turkish"
        assert payload["active_screen"] == "say"
        assert payload["statement_name"] == "say"
        assert payload["normalized"]
        assert payload["word_count"] >= 8
        assert payload["sentence_count"] == 1
        assert payload["alnum_count"] > 20


def test_runtime_screen_observer_logs_scope_strings() -> None:
    ns = _exec_runtime_hook_python_block()

    class MockObservedScreen:
        name = "choice"
        scope = {
            "message": "The story continues here in a much longer visible form.",
            "count": 3,
        }

    ns["renpy"].current_screen = lambda: MockObservedScreen()
    ns["renpy"].get_screen = lambda name: MockObservedScreen() if name == "choice" else None

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        diag_dir = tmp_path / "tl" / "turkish" / "diagnostics"
        diag_dir.mkdir(parents=True)

        ns["config"].gamedir = str(tmp_path)
        ns["_rl_loaded"] = True
        ns["_rl_loaded_language"] = "turkish"
        ns["_rl_translated_values"] = set()
        ns["_rl_runtime_miss_logged"] = set()

        ns["_rl_interact_callback"]()

        log_path = diag_dir / "runtime_missed_strings.jsonl"
        payload = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
        assert payload["layer"] == "screen_observer"
        assert payload["reason"] == "screen_scope_observed"
        assert payload["source_kind"] == "screen_scope"
        assert payload["active_screen"] == "choice"
