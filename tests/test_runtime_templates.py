import json
import tempfile
from pathlib import Path
import sys


class MockRenpyLoader:
    class MockApk:
        def open(self, path):
            return None

        def getvalue(self):
            return b'{"test": "value"}'

    game_apks = [MockApk()]


class MockRenpy:
    config = None
    current_screen = None

    def __init__(self):
        self.loader = MockRenpyLoader()
        self._current_screen = None

    def current_screen(self):
        return self._current_screen


class MockPreferences:
    def __init__(self, lang="tr"):
        self.language = lang


class MockStore:
    _preferences = MockPreferences()


# Setup mocks BEFORE importing
sys.modules["renpy"] = MockRenpy()
sys.modules["renpy.store"] = MockStore()

from src.core import runtime_hook_template as rht


def test_template_logic(tmp_path):
    """Test runtime hook template renders correctly."""
    hook = rht.render_runtime_hook("turkish", runtime_string_diagnostics=False)

    assert hook
    assert len(hook) > 1000
    assert "_rl_replace_text" in hook
    assert "_rl_load_translations" in hook


def test_runtime_hook_rtl_for_persian(tmp_path):
    """Test RTL settings for Persian language."""
    hook = rht.render_runtime_hook("persian", runtime_string_diagnostics=False)

    assert "config.rtl = True" in hook
    assert "_style.language = 'unicode'" in hook
    assert "_style.reading_order = 'wrtl'" in hook


def test_runtime_hook_rtl_for_arabic(tmp_path):
    """Test RTL settings for Arabic language."""
    hook = rht.render_runtime_hook("arabic", runtime_string_diagnostics=False)

    assert "config.rtl = True" in hook
    assert "_style.language = 'unicode'" in hook


def test_runtime_hook_rtl_disabled_for_english(tmp_path):
    """Test RTL is disabled for non-RTL languages."""
    hook = rht.render_runtime_hook("english", runtime_string_diagnostics=False)

    assert "config.rtl = False" in hook


def test_runtime_hook_rtl_languages_list(tmp_path):
    """Test RTL languages are properly listed."""
    hook = rht.render_runtime_hook("tr", runtime_string_diagnostics=False)

    assert "arabic" in hook
    assert "persian" in hook or "farsi" in hook


def test_runtime_hook_diagnostics_enabled(tmp_path):
    """Test diagnostics are enabled when flag is True."""
    hook = rht.render_runtime_hook("tr", runtime_string_diagnostics=True)

    assert "_rl_log_runtime_miss" in hook
    assert "runtime_missed_strings.jsonl" in hook


def test_runtime_hook_diagnostics_disabled(tmp_path):
    """Test diagnostics are disabled when flag is False."""
    hook = rht.render_runtime_hook("tr", runtime_string_diagnostics=False)

    assert "_rl_replace_text" in hook


def test_runtime_hook_template_system(tmp_path):
    """Test template system exists."""
    hook = rht.render_runtime_hook("tr", runtime_string_diagnostics=False)

    assert "_rl_template_map" in hook
    assert "_rl_template_prefix_index" in hook


def test_runtime_hook_phrase_index(tmp_path):
    """Test phrase index for longer text matching."""
    hook = rht.render_runtime_hook("tr", runtime_string_diagnostics=False)

    assert "_rl_phrase_index" in hook
    assert "_rl_phrase_variants" in hook


def test_runtime_hook_caching(tmp_path):
    """Test runtime caching for performance (v4.2.0 MRU-based architecture)."""
    hook = rht.render_runtime_hook("tr", runtime_string_diagnostics=False)

    assert "_rl_mru_cache" in hook           # MRU list replaces sys._rl_caches['replace']
    assert "_rl_translations_norm" in hook   # Pre-built norm dict replaces sys._rl_caches['normalized']
    assert "_rl_mru_cache_max" in hook       # Size limit for MRU cache


def test_runtime_hook_language_detection(tmp_path):
    """Test active language detection."""
    hook = rht.render_runtime_hook("turkish", runtime_string_diagnostics=False)

    assert "_rl_get_active_language" in hook
    assert "_preferences.language" in hook


def test_runtime_hook_template_variants(tmp_path):
    """Test template variants are generated."""
    hook = rht.render_runtime_hook("tr", runtime_string_diagnostics=False)

    assert "_rl_translations_ci" in hook


def test_runtime_hook_normalized_lookup(tmp_path):
    """Test normalized lookup for Unicode variants."""
    hook = rht.render_runtime_hook("tr", runtime_string_diagnostics=False)

    assert "_rl_translations_norm" in hook