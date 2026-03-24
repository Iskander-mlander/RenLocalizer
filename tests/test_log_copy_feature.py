import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.backend.app_backend import AppBackend
from src.core.translator import TranslationEngine, TranslationManager, TranslationResult


def test_copy_text_to_clipboard_success():
    clipboard = MagicMock()
    with patch("src.backend.app_backend.QGuiApplication.clipboard", return_value=clipboard):
        ok = AppBackend.copyTextToClipboard(object(), "hello")
    assert ok is True
    clipboard.setText.assert_called_once_with("hello")


def test_copy_text_to_clipboard_none_input():
    clipboard = MagicMock()
    with patch("src.backend.app_backend.QGuiApplication.clipboard", return_value=clipboard):
        ok = AppBackend.copyTextToClipboard(object(), None)
    assert ok is True
    clipboard.setText.assert_called_once_with("")


def test_copy_text_to_clipboard_large_payload():
    clipboard = MagicMock()
    payload = "A" * (5 * 1024 * 1024)
    with patch("src.backend.app_backend.QGuiApplication.clipboard", return_value=clipboard):
        ok = AppBackend.copyTextToClipboard(object(), payload)
    assert ok is True
    clipboard.setText.assert_called_once_with(payload)


def test_copy_text_to_clipboard_exception():
    clipboard = MagicMock()
    clipboard.setText.side_effect = RuntimeError("clipboard unavailable")
    with patch("src.backend.app_backend.QGuiApplication.clipboard", return_value=clipboard):
        ok = AppBackend.copyTextToClipboard(object(), "x")
    assert ok is False


def test_open_local_path_success():
    with patch("src.backend.app_backend.QDesktopServices.openUrl", return_value=True) as open_url:
        ok = AppBackend.openLocalPath(object(), "C:/tmp/out")
    assert ok is True
    open_url.assert_called_once()


def test_update_cache_path_uses_config_data_dir_and_clears_stale_entries(tmp_path: Path):
    data_dir = tmp_path / "data"
    project_dir = tmp_path / "MyGame"
    project_dir.mkdir()
    cache_dir = data_dir / "cache" / "MyGame" / "tr"
    cache_dir.mkdir(parents=True)
    cache_file = cache_dir / "translation_cache.json"

    manager = TranslationManager()
    manager._cache[("google", "en", "tr", "Stale")] = TranslationResult(
        original_text="Stale",
        translated_text="Bayat",
        source_lang="en",
        target_lang="tr",
        engine=TranslationEngine.GOOGLE,
        success=True,
    )
    manager._cache.clear()
    manager._cache[("google", "en", "tr", "Fresh")] = TranslationResult(
        original_text="Fresh",
        translated_text="Taze",
        source_lang="en",
        target_lang="tr",
        engine=TranslationEngine.GOOGLE,
        success=True,
    )
    manager.save_cache(str(cache_file))

    fake = MagicMock()
    fake._project_path = str(project_dir)
    fake._target_language = "tr"
    fake.config = MagicMock()
    fake.config.data_dir = str(data_dir)
    fake.config.translation_settings.use_global_cache = True
    fake.config.translation_settings.cache_path = "cache"
    fake.translation_manager = TranslationManager()
    fake.translation_manager._cache[("google", "en", "tr", "OldProject")] = TranslationResult(
        original_text="OldProject",
        translated_text="Eski",
        source_lang="en",
        target_lang="tr",
        engine=TranslationEngine.GOOGLE,
        success=True,
    )
    fake.logger = MagicMock()
    fake._get_current_cache_file = lambda: AppBackend._get_current_cache_file(fake)

    AppBackend._update_cache_path(fake)

    texts = {key[3] for key in fake.translation_manager._cache.keys()}
    assert texts == {"Fresh"}


def test_get_cache_entries_refreshes_from_active_cache_file(tmp_path: Path):
    data_dir = tmp_path / "data"
    project_dir = tmp_path / "MyGame"
    project_dir.mkdir()
    cache_dir = data_dir / "cache" / "MyGame" / "tr"
    cache_dir.mkdir(parents=True)
    cache_file = cache_dir / "translation_cache.json"

    writer = TranslationManager()
    writer._cache[("google", "en", "tr", "About")] = TranslationResult(
        original_text="About",
        translated_text="Hakkinda",
        source_lang="en",
        target_lang="tr",
        engine=TranslationEngine.GOOGLE,
        success=True,
    )
    writer.save_cache(str(cache_file))

    fake = MagicMock()
    fake._project_path = str(project_dir)
    fake._target_language = "tr"
    fake.config = MagicMock()
    fake.config.data_dir = str(data_dir)
    fake.config.translation_settings.use_global_cache = True
    fake.config.translation_settings.cache_path = "cache"
    fake.translation_manager = TranslationManager()
    fake.logger = MagicMock()
    fake.logMessage = MagicMock()
    fake._get_current_cache_file = lambda: AppBackend._get_current_cache_file(fake)
    fake._update_cache_path = lambda: AppBackend._update_cache_path(fake)

    entries = AppBackend.getCacheEntries(fake, "about")

    assert len(entries) == 1
    assert entries[0]["original"] == "About"
    assert entries[0]["translated"] == "Hakkinda"


def test_homepage_copy_button_contract():
    qml = Path("src/gui/qml/pages/HomePage.qml").read_text(encoding="utf-8")
    assert "enabled: logModel.count > 0" in qml
    assert 'backend.getText("copy_log")' in qml
    assert 'backend.getText("log_copy_success")' in qml
    assert 'backend.getText("log_copy_failed")' in qml
    assert "backend.copyTextToClipboard(lines.join" in qml


def test_main_qml_uses_completion_dialog_contract():
    qml = Path("src/gui/qml/main.qml").read_text(encoding="utf-8")
    assert "function onCompletionSummary(" in qml
    assert "id: completionDialog" in qml
    assert 'backend.getTextWithDefault("translation_complete_title"' in qml
    assert 'backend.getTextWithDefault("translation_complete_open_output"' in qml
    assert 'backend.getTextWithDefault("translation_complete_open_report"' in qml
    assert "backend.openLocalPath(completionDialog.outputPath)" in qml
    assert "backend.openLocalPath(completionDialog.diagnosticPath)" in qml


def test_locales_have_log_copy_keys():
    locale_dir = Path("locales")
    locale_files = ["en", "tr", "de", "es", "fr", "ru", "fa", "zh-CN"]
    required_keys = ["copy_log", "log_copy_success", "log_copy_failed"]
    for code in locale_files:
        data = json.loads((locale_dir / f"{code}.json").read_text(encoding="utf-8"))
        for key in required_keys:
            assert key in data
            assert isinstance(data[key], str)
            assert data[key].strip() != ""


def test_locales_have_completion_dialog_keys():
    locale_dir = Path("locales")
    locale_files = ["en", "tr", "de", "es", "fr", "ru", "fa", "zh-CN"]
    required_keys = [
        "translation_complete_title",
        "translation_complete_with_notes",
        "translation_complete_no_notes",
        "translation_complete_hint",
        "translation_complete_open_output",
        "translation_complete_open_report",
    ]
    for code in locale_files:
        data = json.loads((locale_dir / f"{code}.json").read_text(encoding="utf-8"))
        for key in required_keys:
            assert key in data
            assert isinstance(data[key], str)
            assert data[key].strip() != ""
