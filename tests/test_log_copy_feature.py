import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.backend.app_backend import AppBackend


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


def test_homepage_copy_button_contract():
    qml = Path("src/gui/qml/pages/HomePage.qml").read_text(encoding="utf-8")
    assert "enabled: logModel.count > 0" in qml
    assert 'backend.getText("copy_log")' in qml
    assert 'backend.getText("log_copy_success")' in qml
    assert 'backend.getText("log_copy_failed")' in qml
    assert "backend.copyTextToClipboard(lines.join" in qml


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
