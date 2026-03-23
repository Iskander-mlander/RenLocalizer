# -*- coding: utf-8 -*-
"""
Tests for v2.7.1 features:
- Config validation (__post_init__ clamps)
- Ren'Py lint module
- Project import/export
- JSON/YAML data extractors
- Translation obfuscation
- RPA packer
"""

import json
import os
import tempfile
import shutil
import pytest
from pathlib import Path


# ════════════════════════════════════════════════════════════════════
# Config Validation Tests
# ════════════════════════════════════════════════════════════════════

class TestTranslationSettingsValidation:
    """TranslationSettings.__post_init__ clamp & allowlist checks."""

    def test_numeric_lower_clamp(self):
        from src.utils.config import TranslationSettings
        ts = TranslationSettings(
            max_batch_size=0,
            ai_concurrency=0,
            ai_batch_size=-5,
            timeout=1,
            max_retries=0,
            max_concurrent_threads=-1,
        )
        assert ts.max_batch_size == 1
        assert ts.ai_concurrency == 1
        assert ts.ai_batch_size == 1
        assert ts.timeout == 5
        assert ts.max_retries == 1
        assert ts.max_concurrent_threads == 1

    def test_numeric_upper_clamp(self):
        from src.utils.config import TranslationSettings
        ts = TranslationSettings(
            max_batch_size=9999,
            max_concurrent_threads=999,
            ai_temperature=99.0,
            ai_concurrency=999,
            ai_max_tokens=999999,
        )
        assert ts.max_batch_size == 9999
        assert ts.max_concurrent_threads == 64
        assert ts.ai_temperature == 2.0
        assert ts.ai_concurrency == 20
        assert ts.ai_max_tokens == 32768

    def test_batch_size_clamps_to_new_general_upper_bound(self):
        from src.utils.config import TranslationSettings
        ts = TranslationSettings(max_batch_size=50000)
        assert ts.max_batch_size == 10000

    def test_ai_batch_size_clamps_to_new_upper_bound(self):
        from src.utils.config import TranslationSettings
        ts = TranslationSettings(ai_batch_size=50000)
        assert ts.ai_batch_size == 10000

    def test_enum_fallback_deepl_formality(self):
        from src.utils.config import TranslationSettings
        ts = TranslationSettings(deepl_formality="INVALID")
        assert ts.deepl_formality == "default"

    def test_enum_valid_deepl_formality(self):
        from src.utils.config import TranslationSettings
        for val in ("default", "formal", "informal"):
            ts = TranslationSettings(deepl_formality=val)
            assert ts.deepl_formality == val

    def test_enum_fallback_gemini_safety(self):
        from src.utils.config import TranslationSettings
        ts = TranslationSettings(gemini_safety_settings="NOPE")
        assert ts.gemini_safety_settings == "BLOCK_NONE"

    def test_string_strip(self):
        from src.utils.config import TranslationSettings
        ts = TranslationSettings(source_language="  en  ", target_language="  ")
        assert ts.source_language == "en"
        assert ts.target_language == "tr"  # fallback

    def test_json_validation_invalid(self):
        from src.utils.config import TranslationSettings
        ts = TranslationSettings(custom_function_params="NOT JSON {{}")
        assert ts.custom_function_params == "{}"

    def test_json_validation_valid(self):
        from src.utils.config import TranslationSettings
        ts = TranslationSettings(custom_function_params='{"Quest": {"pos": [0]}}')
        assert json.loads(ts.custom_function_params) == {"Quest": {"pos": [0]}}

    def test_defaults_unchanged(self):
        from src.utils.config import TranslationSettings
        ts = TranslationSettings()
        assert ts.max_batch_size == 100
        assert ts.ai_concurrency == 2
        assert ts.ai_temperature == 0.3
        assert ts.deepl_formality == "default"


class TestApiKeysValidation:
    def test_strip_whitespace(self):
        from src.utils.config import ApiKeys
        ak = ApiKeys(
            deepl_api_key="  key123  ",
            openai_api_key=" sk-abc ",
        )
        assert ak.deepl_api_key == "key123"
        assert ak.openai_api_key == "sk-abc"


class TestAppSettingsValidation:
    def test_theme_fallback(self):
        from src.utils.config import AppSettings
        app = AppSettings(app_theme="sunset")
        assert app.app_theme == "dark"

    def test_output_format_fallback(self):
        from src.utils.config import AppSettings
        app = AppSettings(output_format="xml")
        assert app.output_format == "old_new"

    def test_valid_themes(self):
        from src.utils.config import AppSettings
        for t in ("dark", "light", "red", "turquoise", "green", "neon", "auto"):
            assert AppSettings(app_theme=t).app_theme == t


class TestConfigManagerPersistence:
    @pytest.fixture
    def isolated_data_dir(self, tmp_path, monkeypatch):
        from src.utils import path_manager

        def fake_get_data_path() -> Path:
            return tmp_path

        def fake_ensure_data_directories(data_path: Path) -> None:
            data_path.mkdir(parents=True, exist_ok=True)
            (data_path / "logs").mkdir(exist_ok=True)
            (data_path / "tm").mkdir(exist_ok=True)

        monkeypatch.setattr(path_manager, "get_data_path", fake_get_data_path)
        monkeypatch.setattr(path_manager, "ensure_data_directories", fake_ensure_data_directories)
        return tmp_path

    def test_set_api_key_persists_without_auto_save_flag(self, isolated_data_dir):
        from src.utils.config import ConfigManager

        manager = ConfigManager()
        manager.set_api_key("openai", " sk-test ")

        reloaded = ConfigManager()
        assert reloaded.api_keys.openai_api_key == "sk-test"

    def test_set_setting_persists_custom_theme_via_legacy_alias(self, isolated_data_dir):
        from src.utils.config import ConfigManager

        manager = ConfigManager()
        manager.set_setting("app.theme", "neon")

        reloaded = ConfigManager()
        assert reloaded.app_settings.app_theme == "neon"

    def test_legacy_theme_key_migrates_to_app_theme(self, isolated_data_dir):
        from src.utils.config import ConfigManager

        config_path = isolated_data_dir / "config.json"
        config_path.write_text(
            json.dumps(
                {
                    "translation_settings": {},
                    "api_keys": {},
                    "app_settings": {"theme": "light"},
                    "proxy_settings": {},
                }
            ),
            encoding="utf-8",
        )

        manager = ConfigManager()
        manager.save_config()

        reloaded_data = json.loads(config_path.read_text(encoding="utf-8"))
        assert manager.app_settings.app_theme == "light"
        assert reloaded_data["app_settings"]["app_theme"] == "light"
        assert "theme" not in reloaded_data["app_settings"]


class TestProxySettingsValidation:
    def test_clamps(self):
        from src.utils.config import ProxySettings
        ps = ProxySettings(update_interval=5, max_failures=0, proxy_url="  http://x  ")
        assert ps.update_interval == 60
        assert ps.max_failures == 1
        assert ps.proxy_url == "http://x"


# ════════════════════════════════════════════════════════════════════
# Ren'Py Lint Tests
# ════════════════════════════════════════════════════════════════════

class TestRenpyLint:
    
    @pytest.fixture
    def linter(self):
        from src.tools.renpy_lint import RenpyTranslationLint
        return RenpyTranslationLint()

    @pytest.fixture
    def make_rpy(self, tmp_path):
        """Create a temp .rpy file with given content."""
        def _make(content: str, name: str = "test.rpy") -> str:
            p = tmp_path / name
            p.write_text(content, encoding="utf-8")
            return str(p)
        return _make

    def test_clean_file(self, linter, make_rpy):
        content = (
            'translate turkish test_abc:\n'
            '    old "Hello [name]"\n'
            '    new "Merhaba [name]"\n'
        )
        r = linter.lint_file(make_rpy(content))
        assert r.ok
        assert r.old_new_pairs == 1

    def test_missing_variable(self, linter, make_rpy):
        content = (
            'translate turkish test_abc:\n'
            '    old "Hello [name]"\n'
            '    new "Merhaba"\n'
        )
        r = linter.lint_file(make_rpy(content))
        assert not r.ok
        assert any(i.code == "E040" for i in r.issues)

    def test_missing_tag(self, linter, make_rpy):
        content = (
            'translate turkish test_abc:\n'
            '    old "Hello {b}world{/b}"\n'
            '    new "Merhaba dunya"\n'
        )
        r = linter.lint_file(make_rpy(content))
        assert any(i.code == "W040" for i in r.issues)

    def test_bad_indentation(self, linter, make_rpy):
        content = (
            'translate turkish test_abc:\n'
            'old "Bad indent"\n'
            '    new "Kotu"\n'
        )
        r = linter.lint_file(make_rpy(content))
        assert any(i.code == "E020" for i in r.issues)

    def test_unbalanced_quotes(self, linter, make_rpy):
        content = (
            'translate turkish test_abc:\n'
            '    old "Hello\n'
            '    new "Merhaba"\n'
        )
        r = linter.lint_file(make_rpy(content))
        assert any(i.code == "E050" for i in r.issues)

    def test_duplicate_translate_id(self, linter, make_rpy):
        content = (
            'translate turkish test_abc:\n'
            '    old "Hello"\n'
            '    new "Merhaba"\n'
            '\n'
            'translate turkish test_abc:\n'
            '    old "World"\n'
            '    new "Dunya"\n'
        )
        r = linter.lint_file(make_rpy(content))
        assert any(i.code == "W020" for i in r.issues)

    def test_tab_warning(self, linter, make_rpy):
        content = 'translate turkish test_abc:\n\told "Hello"\n\tnew "Merhaba"\n'
        r = linter.lint_file(make_rpy(content))
        assert any(i.code == "W010" for i in r.issues)

    def test_orphaned_old(self, linter, make_rpy):
        content = (
            'translate turkish test_abc:\n'
            '    old "Hello"\n'
            '    # missing new\n'
        )
        r = linter.lint_file(make_rpy(content))
        assert any(i.code == "E030" for i in r.issues)

    def test_lint_directory(self, linter, tmp_path):
        (tmp_path / "a.rpy").write_text(
            'translate turkish a1:\n    old "Hi"\n    new "Merhaba"\n',
            encoding="utf-8"
        )
        (tmp_path / "b.rpy").write_text(
            'translate turkish b1:\n    old "Bye [name]"\n    new "Hoscakal"\n',
            encoding="utf-8"
        )
        r = linter.lint_directory(str(tmp_path))
        assert r.files_scanned == 2
        assert r.old_new_pairs == 2
        # b.rpy should have missing [name]
        assert any(i.code == "E040" for i in r.issues)


# ════════════════════════════════════════════════════════════════════
# Project Import/Export Tests
# ════════════════════════════════════════════════════════════════════

class TestProjectIO:

    def _make_config_manager(self):
        from src.utils.config import (
            ConfigManager, TranslationSettings, ApiKeys, AppSettings, ProxySettings
        )
        cm = ConfigManager.__new__(ConfigManager)
        cm.translation_settings = TranslationSettings(target_language="tr", source_language="en")
        cm.app_settings = AppSettings(last_input_directory="C:/Games/TestGame")
        cm.api_keys = ApiKeys(openai_api_key="sk-secret")
        cm.proxy_settings = ProxySettings()
        cm.glossary = {"HP": "Can", "Save": "Kaydet"}
        cm.critical_terms = ["HP", "MP"]
        cm.never_translate_rules = {"regex": []}
        return cm

    def test_export_creates_file(self, tmp_path):
        from src.utils.project_io import export_project
        cm = self._make_config_manager()
        out = str(tmp_path / "test.rlproj")
        path = export_project(out, config_manager=cm)
        assert Path(path).exists()
        assert Path(path).stat().st_size > 0

    def test_import_reads_manifest(self, tmp_path):
        from src.utils.project_io import export_project, import_project
        cm = self._make_config_manager()
        out = str(tmp_path / "test.rlproj")
        export_project(out, config_manager=cm, project_name="MyGame")
        result = import_project(out)
        assert result.ok
        assert result.project_name == "MyGame"
        assert result.source_language == "en"
        assert result.target_language == "tr"

    def test_glossary_roundtrip(self, tmp_path):
        from src.utils.project_io import export_project, import_project
        cm = self._make_config_manager()
        out = str(tmp_path / "test.rlproj")
        export_project(out, config_manager=cm)
        result = import_project(out)
        assert result.glossary == {"HP": "Can", "Save": "Kaydet"}

    def test_cache_roundtrip(self, tmp_path):
        from src.utils.project_io import export_project, import_project
        cm = self._make_config_manager()
        cache = {"google": {"en": {"tr": {"Hello": "Merhaba"}}}}
        out = str(tmp_path / "test.rlproj")
        export_project(out, config_manager=cm, cache_data=cache)
        result = import_project(out)
        assert result.cache_data == cache

    def test_invalid_archive(self, tmp_path):
        from src.utils.project_io import import_project
        bad = tmp_path / "bad.rlproj"
        bad.write_text("not a zip")
        result = import_project(str(bad))
        assert not result.ok

    def test_missing_file(self):
        from src.utils.project_io import import_project
        result = import_project("/nonexistent/path.rlproj")
        assert not result.ok

    def test_api_keys_excluded_by_default(self, tmp_path):
        from src.utils.project_io import export_project, import_project
        cm = self._make_config_manager()
        out = str(tmp_path / "test.rlproj")
        export_project(out, config_manager=cm, include_api_keys=False)
        result = import_project(out)
        assert "api_keys" not in result.settings


# ════════════════════════════════════════════════════════════════════
# JSON/YAML Extractor Tests
# ════════════════════════════════════════════════════════════════════

class TestJsonExtractor:

    def test_basic_extraction(self, tmp_path):
        from src.core.data_extractors import JsonExtractor
        data = {
            "title": "Chapter 1",
            "dialogue": [
                {"speaker": "Alice", "text": "Hello world!"},
            ],
            "id": "ch01",
            "image": "bg.png",
        }
        p = tmp_path / "test.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        ext = JsonExtractor()
        entries = ext.extract(str(p))
        keys = {e.key_path for e in entries}
        assert "title" in keys
        assert "dialogue.0.text" in keys
        # id and image should be skipped
        assert "id" not in keys
        assert "image" not in keys

    def test_write_back(self, tmp_path):
        from src.core.data_extractors import JsonExtractor
        data = {"text": "Hello", "description": "A game"}
        p = tmp_path / "test.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        ext = JsonExtractor()
        ok = ext.write_back(str(p), {"text": "Merhaba", "description": "Bir oyun"})
        assert ok
        result = json.loads(p.read_text())
        assert result["text"] == "Merhaba"
        assert result["description"] == "Bir oyun"

    def test_nested_structure(self, tmp_path):
        from src.core.data_extractors import JsonExtractor
        data = {
            "levels": {
                "forest": {
                    "name": "Dark Forest",
                    "description": "A scary forest",
                    "enemies": ["Goblin", "Wolf", "Bear"],
                }
            }
        }
        p = tmp_path / "test.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        ext = JsonExtractor()
        entries = ext.extract(str(p))
        paths = {e.key_path for e in entries}
        assert "levels.forest.name" in paths
        assert "levels.forest.description" in paths

    def test_skip_technical_values(self, tmp_path):
        from src.core.data_extractors import JsonExtractor
        data = {
            "color": "#ff0000",
            "path": "/images/bg.png",
            "url": "https://example.com",
            "version": "1.0",
            "text": "Real text here",
        }
        p = tmp_path / "test.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        ext = JsonExtractor()
        entries = ext.extract(str(p))
        paths = {e.key_path for e in entries}
        assert "text" in paths
        assert "color" not in paths
        assert "path" not in paths
        assert "url" not in paths


class TestExtractorRegistry:
    
    def test_available_extractors(self):
        from src.core.data_extractors import ExtractorRegistry
        r = ExtractorRegistry()
        assert "json" in r.available
        assert "yaml" in r.available

    def test_auto_detect(self, tmp_path):
        from src.core.data_extractors import ExtractorRegistry
        data = {"text": "Hello world"}
        p = tmp_path / "test.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        r = ExtractorRegistry()
        entries = r.extract_file(str(p))
        assert len(entries) >= 1

    def test_custom_extractor(self):
        from src.core.data_extractors import ExtractorRegistry, BaseExtractor, ExtractedEntry
        
        class DummyExtractor(BaseExtractor):
            def extract(self, path):
                return [ExtractedEntry(file=path, key_path="test", original="dummy")]
        
        r = ExtractorRegistry()
        r.register("dummy", DummyExtractor())
        assert "dummy" in r.available
        e = r.get("dummy")
        assert e is not None


# ════════════════════════════════════════════════════════════════════
# Translation Crypto Tests
# ════════════════════════════════════════════════════════════════════

class TestObfuscation:

    def test_obfuscate_new_line(self):
        from src.utils.translation_crypto import obfuscate_rpy_content
        content = (
            'translate turkish abc:\n'
            '    old "Hello"\n'
            '    new "Merhaba"\n'
        )
        obf = obfuscate_rpy_content(content)
        assert "Merhaba" not in obf
        assert "_rl_deobf" in obf
        assert "init -999 python:" in obf

    def test_roundtrip(self):
        from src.utils.translation_crypto import obfuscate_rpy_content, deobfuscate_rpy_content
        content = (
            'translate turkish abc:\n'
            '    old "Hello"\n'
            '    new "Merhaba, hosgeldin!"\n'
        )
        obf = obfuscate_rpy_content(content)
        deobf = deobfuscate_rpy_content(obf)
        assert "Merhaba, hosgeldin!" in deobf

    def test_empty_translation_untouched(self):
        from src.utils.translation_crypto import obfuscate_rpy_content
        content = (
            'translate turkish abc:\n'
            '    old "Hello"\n'
            '    new ""\n'
        )
        obf = obfuscate_rpy_content(content)
        assert '    new ""' in obf

    def test_file_obfuscation(self, tmp_path):
        from src.utils.translation_crypto import obfuscate_rpy_file
        p = tmp_path / "test.rpy"
        p.write_text(
            'translate turkish abc:\n    old "Hello"\n    new "Merhaba"\n',
            encoding="utf-8-sig"
        )
        result = obfuscate_rpy_file(str(p))
        content = Path(result).read_text(encoding="utf-8-sig")
        assert "Merhaba" not in content
        assert "_rl_deobf" in content


# ════════════════════════════════════════════════════════════════════
# RPA Packer Tests
# ════════════════════════════════════════════════════════════════════

class TestRPAPacker:

    def test_pack_and_extract(self, tmp_path):
        from src.utils.rpa_packer import RPAPacker
        from src.utils.rpa_parser import RPAParser

        # Create source files
        src = tmp_path / "src"
        src.mkdir()
        (src / "script.rpy").write_text("translate turkish test:\n    old \"Hi\"\n    new \"Merhaba\"\n")
        (src / "gui.rpy").write_text("translate turkish strings:\n    old \"Start\"\n    new \"Basla\"\n")

        # Pack
        rpa = tmp_path / "test.rpa"
        packer = RPAPacker()
        path = packer.pack_directory(str(src), str(rpa))
        assert Path(path).exists()

        # Extract
        ext = tmp_path / "ext"
        parser = RPAParser()
        ok = parser.extract_archive(Path(path), ext)
        assert ok

        # Verify
        assert "Merhaba" in (ext / "script.rpy").read_text()
        assert "Basla" in (ext / "gui.rpy").read_text()

    def test_pack_with_prefix(self, tmp_path):
        from src.utils.rpa_packer import RPAPacker
        from src.utils.rpa_parser import RPAParser

        src = tmp_path / "src"
        src.mkdir()
        (src / "test.rpy").write_text("test content")

        rpa = tmp_path / "test.rpa"
        packer = RPAPacker()
        packer.pack_directory(str(src), str(rpa), base_prefix="tl/turkish/")

        ext = tmp_path / "ext"
        RPAParser().extract_archive(Path(rpa), ext)
        assert (ext / "tl" / "turkish" / "test.rpy").exists()

    def test_pack_files_explicit(self, tmp_path):
        from src.utils.rpa_packer import RPAPacker
        from src.utils.rpa_parser import RPAParser

        f = tmp_path / "hello.rpy"
        f.write_text("hello content")

        rpa = tmp_path / "test.rpa"
        packer = RPAPacker()
        packer.pack_files({"game/hello.rpy": str(f)}, str(rpa))

        ext = tmp_path / "ext"
        RPAParser().extract_archive(Path(rpa), ext)
        assert (ext / "game" / "hello.rpy").exists()
        assert (ext / "game" / "hello.rpy").read_text() == "hello content"

    def test_empty_directory(self, tmp_path):
        from src.utils.rpa_packer import RPAPacker
        src = tmp_path / "empty"
        src.mkdir()
        packer = RPAPacker()
        result = packer.pack_directory(str(src), str(tmp_path / "test.rpa"))
        assert result == ""  # no files found


# ════════════════════════════════════════════════════════════════════
# Convenience function
# ════════════════════════════════════════════════════════════════════

class TestPackTranslations:
    def test_auto_naming(self, tmp_path):
        from src.utils.rpa_packer import pack_translations
        src = tmp_path / "tl"
        src.mkdir()
        (src / "test.rpy").write_text("content")
        result = pack_translations(str(src), "", language="turkish")
        assert result.endswith(".rpa")
        assert "turkish" in result
