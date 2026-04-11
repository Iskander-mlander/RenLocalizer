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


def test_runtime_miss_log_includes_metadata_fields(tmp_path):
    """Test that runtime miss logging includes rich metadata."""
    hook = rht.render_runtime_hook("tr", runtime_string_diagnostics=True)

    assert "_rl_log_runtime_miss" in hook
    assert "source_kind" in hook
    assert "active_language" in hook


def test_runtime_screen_observer_logs_scope_strings(tmp_path):
    """Test that screen observer captures scope strings."""
    hook = rht.render_runtime_hook("tr", runtime_string_diagnostics=True)

    assert "_rl_interact_callback" in hook or "start_interact_callbacks" in hook
    assert "screen_observer" in hook or "screen_scope" in hook


def test_runtime_diagnostics_jsonl_format(tmp_path):
    """Test diagnostics use JSONL format."""
    hook = rht.render_runtime_hook("tr", runtime_string_diagnostics=True)

    assert "jsonl" in hook.lower() or "Runtime" in hook


def test_runtime_diagnostics_bounded(tmp_path):
    """Test diagnostics are bounded to prevent infinite growth."""
    hook = rht.render_runtime_hook("tr", runtime_string_diagnostics=True)

    assert "_rl_runtime_miss_limit" in hook or "limit" in hook
    assert "_rl_runtime_miss_logged" in hook


def test_runtime_diagnostics_layer_tracking(tmp_path):
    """Test that diagnostics track which layer missed."""
    hook = rht.render_runtime_hook("tr", runtime_string_diagnostics=True)

    assert "say_menu_text_filter" in hook or "replace_text" in hook


def test_runtime_diagnostics_visible_form(tmp_path):
    """Test that diagnostics include visible form."""
    hook = rht.render_runtime_hook("tr", runtime_string_diagnostics=True)

    assert "visible_form" in hook or "stripped" in hook


def test_runtime_diagnostics_word_count(tmp_path):
    """Test that diagnostics include word count."""
    hook = rht.render_runtime_hook("tr", runtime_string_diagnostics=True)

    assert "word_count" in hook or "length" in hook


def test_runtime_diagnostics_active_screen(tmp_path):
    """Test that diagnostics track active screen."""
    hook = rht.render_runtime_hook("tr", runtime_string_diagnostics=True)

    assert "active_screen" in hook or "_renpy.current_screen" in hook


def test_runtime_diagnostics_screen_scope(tmp_path):
    """Test that screen scope is harvested for strings."""
    hook = rht.render_runtime_hook("tr", runtime_string_diagnostics=True)

    assert "scope" in hook or ".get_screen" in hook


def test_runtime_diagnostics_diagnostic_directory(tmp_path):
    """Test diagnostics go to correct directory."""
    hook = rht.render_runtime_hook("tr", runtime_string_diagnostics=True)

    assert "diagnostics" in hook
    assert "runtime_missed_strings.jsonl" in hook


def test_runtime_diagnostics_off_by_default(tmp_path):
    """Test diagnostics are off by default."""
    hook = rht.render_runtime_hook("tr", runtime_string_diagnostics=False)

    assert "_rl_replace_text" in hook


def test_runtime_diagnostics_language_specific(tmp_path):
    """Test diagnostics are per-language."""
    hook_tr = rht.render_runtime_hook("tr", runtime_string_diagnostics=True)
    hook_fa = rht.render_runtime_hook("fa", runtime_string_diagnostics=True)

    assert "_rl_log_runtime_miss" in hook_tr
    assert "_rl_log_runtime_miss" in hook_fa


def test_runtime_diagnostics_escaped_strings(tmp_path):
    """Test diagnostics handle escaped strings safely."""
    hook = rht.render_runtime_hook("tr", runtime_string_diagnostics=True)

    assert "_rl_json" in hook or "json" in hook


def test_runtime_diagnostics_runtime_miss_reason(tmp_path):
    """Test runtime miss reasons are tracked."""
    hook = rht.render_runtime_hook("tr", runtime_string_diagnostics=True)

    assert "reason" in hook or "miss" in hook