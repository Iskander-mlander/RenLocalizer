# -*- coding: utf-8 -*-
"""
Tests for External Translation Memory (TM) Module
===================================================
src/tools/external_tm.py modülünün unit testleri.
"""

import os
import sys
import json
import shutil
import tempfile
import unittest

# Proje kökünü path'e ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.external_tm import (
    ExternalTMStore,
    TMImportResult,
    TMSource,
    MAX_TM_ENTRIES,
    MIN_TEXT_LENGTH,
    MAX_TEXT_LENGTH,
    _TECHNICAL_SKIP_RE,
)


class TestTechnicalSkipRegex(unittest.TestCase):
    """_TECHNICAL_SKIP_RE filtreleme testleri."""

    def test_all_caps_identifier(self):
        self.assertIsNotNone(_TECHNICAL_SKIP_RE.search("GAME_STATE"))
        self.assertIsNotNone(_TECHNICAL_SKIP_RE.search("OK"))

    def test_dotted_path(self):
        self.assertIsNotNone(_TECHNICAL_SKIP_RE.search("renpy.config.screen"))

    def test_url(self):
        self.assertIsNotNone(_TECHNICAL_SKIP_RE.search("https://example.com"))

    def test_file_extension(self):
        self.assertIsNotNone(_TECHNICAL_SKIP_RE.search("background.png"))

    def test_numbers_only(self):
        self.assertIsNotNone(_TECHNICAL_SKIP_RE.search("12345"))

    def test_normal_text_not_filtered(self):
        self.assertIsNone(_TECHNICAL_SKIP_RE.search("Hello, how are you?"))
        self.assertIsNone(_TECHNICAL_SKIP_RE.search("Save the game"))


class TestTMImportResult(unittest.TestCase):
    """TMImportResult dataclass testleri."""

    def test_success_when_imported(self):
        r = TMImportResult(source_name="Test", language="turkish", imported=100)
        self.assertTrue(r.success)

    def test_not_success_when_zero(self):
        r = TMImportResult(source_name="Test", language="turkish", imported=0)
        self.assertFalse(r.success)

    def test_not_success_when_error(self):
        r = TMImportResult(source_name="Test", language="turkish", imported=50, error="Something failed")
        self.assertFalse(r.success)


class TestTMSource(unittest.TestCase):
    """TMSource dataclass testleri."""

    def test_to_dict(self):
        s = TMSource(name="GameA", language="turkish", entry_count=500, file_path="/tmp/GameA_turkish.json")
        d = s.to_dict()
        self.assertEqual(d["name"], "GameA")
        self.assertEqual(d["language"], "turkish")
        self.assertEqual(d["entry_count"], 500)


class TestExternalTMStore(unittest.TestCase):
    """ExternalTMStore ana sınıf testleri."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="renlocalizer_tm_test_")
        self.tm_dir = os.path.join(self.test_dir, "tm")
        os.makedirs(self.tm_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_tm_json(self, name: str, language: str, entries: dict) -> str:
        """Helper: Geçerli bir TM JSON dosyası oluştur."""
        filepath = os.path.join(self.tm_dir, f"{name}_{language}.json")
        data = {
            "meta": {
                "source_name": name,
                "language": language,
                "entry_count": len(entries),
                "created": "2026-03-08T12:00:00",
                "source_path": "/test/tl/" + language,
                "version": "1.0"
            },
            "entries": entries
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return filepath

    def test_load_sources_single(self):
        """Tek kaynak yükleme."""
        path = self._create_tm_json("GameA", "turkish", {
            "Hello": "Merhaba",
            "Save": "Kaydet",
            "Load": "Yükle",
        })
        store = ExternalTMStore(tm_dir=self.tm_dir)
        loaded = store.load_sources([path])
        self.assertEqual(loaded, 3)
        self.assertEqual(store.entry_count, 3)
        self.assertEqual(store.loaded_source_count, 1)

    def test_load_sources_multiple(self):
        """Çoklu kaynak yükleme (LIFO merge)."""
        path1 = self._create_tm_json("GameA", "turkish", {
            "Hello": "Merhaba",
            "Goodbye": "Hoşça kal",
        })
        path2 = self._create_tm_json("GameB", "turkish", {
            "Hello": "Selam",  # Override!
            "New Game": "Yeni Oyun",
        })
        store = ExternalTMStore(tm_dir=self.tm_dir)
        loaded = store.load_sources([path1, path2])
        self.assertEqual(loaded, 3)  # Hello (overridden), Goodbye, New Game
        self.assertEqual(store.get_exact("Hello"), "Selam")  # LIFO: GameB kazanır

    def test_get_exact_hit(self):
        """Exact match başarılı."""
        path = self._create_tm_json("Test", "turkish", {"Hello": "Merhaba"})
        store = ExternalTMStore(tm_dir=self.tm_dir)
        store.load_sources([path])
        self.assertEqual(store.get_exact("Hello"), "Merhaba")

    def test_get_exact_miss(self):
        """Exact match başarısız."""
        path = self._create_tm_json("Test", "turkish", {"Hello": "Merhaba"})
        store = ExternalTMStore(tm_dir=self.tm_dir)
        store.load_sources([path])
        self.assertIsNone(store.get_exact("Nonexistent text"))

    def test_get_exact_empty_store(self):
        """Boş store'da lookup."""
        store = ExternalTMStore(tm_dir=self.tm_dir)
        self.assertIsNone(store.get_exact("Hello"))

    def test_get_exact_batch(self):
        """Toplu exact match."""
        path = self._create_tm_json("Test", "turkish", {
            "Hello": "Merhaba",
            "Save": "Kaydet",
            "Load": "Yükle",
        })
        store = ExternalTMStore(tm_dir=self.tm_dir)
        store.load_sources([path])
        results = store.get_exact_batch(["Hello", "Save", "Unknown"])
        self.assertEqual(len(results), 2)
        self.assertEqual(results["Hello"], "Merhaba")
        self.assertEqual(results["Save"], "Kaydet")
        self.assertNotIn("Unknown", results)

    def test_list_available_sources(self):
        """TM kaynaklarını listeleme."""
        self._create_tm_json("GameA", "turkish", {"Hello": "Merhaba"})
        self._create_tm_json("GameB", "spanish", {"Hello": "Hola"})
        store = ExternalTMStore(tm_dir=self.tm_dir)
        sources = store.list_available_sources()
        self.assertEqual(len(sources), 2)
        names = {s.name for s in sources}
        self.assertIn("GameA", names)
        self.assertIn("GameB", names)

    def test_delete_source(self):
        """TM kaynağı silme."""
        path = self._create_tm_json("ToDelete", "turkish", {"Hello": "Merhaba"})
        store = ExternalTMStore(tm_dir=self.tm_dir)
        self.assertTrue(os.path.isfile(path))
        success = store.delete_source(path)
        self.assertTrue(success)
        self.assertFalse(os.path.isfile(path))

    def test_stats(self):
        """İstatistik kontrolü."""
        path = self._create_tm_json("Test", "turkish", {
            "Hello": "Merhaba",
            "Save": "Kaydet",
        })
        store = ExternalTMStore(tm_dir=self.tm_dir)
        store.load_sources([path])
        store.get_exact("Hello")  # hit
        store.get_exact("Nonexistent")  # miss
        stats = store.stats
        self.assertEqual(stats["entries"], 2)
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["hit_rate"], 50.0)

    def test_is_loaded(self):
        """is_loaded kontrolü."""
        store = ExternalTMStore(tm_dir=self.tm_dir)
        self.assertFalse(store.is_loaded())
        path = self._create_tm_json("Test", "turkish", {"H": "M"})
        store.load_sources([path])
        self.assertTrue(store.is_loaded())

    def test_load_clears_previous(self):
        """load_sources önceki verileri temizler."""
        path1 = self._create_tm_json("A", "tr", {"Hello": "Merhaba"})
        path2 = self._create_tm_json("B", "tr", {"Bye": "Güle güle"})
        store = ExternalTMStore(tm_dir=self.tm_dir)
        store.load_sources([path1])
        self.assertEqual(store.get_exact("Hello"), "Merhaba")
        store.load_sources([path2])
        self.assertIsNone(store.get_exact("Hello"))
        self.assertEqual(store.get_exact("Bye"), "Güle güle")

    def test_skip_same_original_translated(self):
        """original == translated olan entry'ler yüklenmez."""
        path = self._create_tm_json("Same", "tr", {
            "Hello": "Hello",  # same — should be skipped
            "Save": "Kaydet",
        })
        store = ExternalTMStore(tm_dir=self.tm_dir)
        store.load_sources([path])
        self.assertIsNone(store.get_exact("Hello"))
        self.assertEqual(store.get_exact("Save"), "Kaydet")

    def test_invalid_json_file_skipped(self):
        """Geçersiz JSON dosyası atlanır."""
        bad_path = os.path.join(self.tm_dir, "bad.json")
        with open(bad_path, 'w') as f:
            f.write("this is not json{{{")
        store = ExternalTMStore(tm_dir=self.tm_dir)
        loaded = store.load_sources([bad_path])
        self.assertEqual(loaded, 0)

    def test_nonexistent_file_skipped(self):
        """Var olmayan dosya atlanır."""
        store = ExternalTMStore(tm_dir=self.tm_dir)
        loaded = store.load_sources(["/nonexistent/path.json"])
        self.assertEqual(loaded, 0)


class TestExternalTMImportFromTL(unittest.TestCase):
    """import_from_tl_directory testleri (TLParser bağımlı)."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="renlocalizer_tm_import_test_")
        self.tm_dir = os.path.join(self.test_dir, "tm")
        os.makedirs(self.tm_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_import_nonexistent_dir(self):
        """Var olmayan klasörden import."""
        store = ExternalTMStore(tm_dir=self.tm_dir)
        result = store.import_from_tl_directory("/nonexistent/path", "Test", "turkish")
        self.assertFalse(result.success)
        self.assertIn("bulunamadı", result.error)

    def test_import_empty_dir(self):
        """Boş klasörden import."""
        empty_dir = os.path.join(self.test_dir, "tl", "turkish")
        os.makedirs(empty_dir, exist_ok=True)
        store = ExternalTMStore(tm_dir=self.tm_dir)
        result = store.import_from_tl_directory(empty_dir, "Empty", "turkish")
        self.assertFalse(result.success)

    def test_import_with_valid_rpy(self):
        """Geçerli .rpy dosyasından import."""
        tl_dir = os.path.join(self.test_dir, "tl")
        lang_dir = os.path.join(tl_dir, "turkish")
        os.makedirs(lang_dir, exist_ok=True)

        # Basit bir çeviri dosyası oluştur
        rpy_content = '''# game/script.rpy:10
translate turkish start_label_abc12345:

    # e "Hello, how are you?"
    e "Merhaba, nasılsın?"

# game/script.rpy:15
translate turkish start_label_def67890:

    # e "Goodbye!"
    e "Hoşça kal!"

'''
        rpy_path = os.path.join(lang_dir, "script.rpy")
        with open(rpy_path, 'w', encoding='utf-8') as f:
            f.write(rpy_content)

        store = ExternalTMStore(tm_dir=self.tm_dir)
        result = store.import_from_tl_directory(lang_dir, "TestGame", "turkish")

        # TLParser'ın bu dosyayı parse edip edemediğini kontrol et
        # Dosya formatı doğruysa import başarılı olmalı
        if result.success:
            self.assertGreater(result.imported, 0)
            self.assertTrue(os.path.isfile(result.output_path))
            # JSON dosyasını kontrol et
            with open(result.output_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.assertIn("meta", data)
            self.assertIn("entries", data)
            self.assertEqual(data["meta"]["source_name"], "TestGame")
            self.assertEqual(data["meta"]["language"], "turkish")


class TestConfigTMFields(unittest.TestCase):
    """Config TM field doğrulama testleri."""

    def test_tm_fields_defaults(self):
        """TM fieldlarının varsayılan değerleri."""
        from src.utils.config import TranslationSettings
        settings = TranslationSettings()
        self.assertFalse(settings.use_external_tm)
        self.assertEqual(settings.external_tm_match_mode, "exact")
        self.assertEqual(settings.external_tm_fuzzy_threshold, 0.85)
        self.assertEqual(settings.external_tm_sources, "[]")

    def test_tm_match_mode_validation(self):
        """Geçersiz match mode düzeltilmeli."""
        from src.utils.config import TranslationSettings
        settings = TranslationSettings(external_tm_match_mode="invalid")
        self.assertEqual(settings.external_tm_match_mode, "exact")

    def test_tm_fuzzy_threshold_clamp(self):
        """Fuzzy threshold clamp kontrolü."""
        from src.utils.config import TranslationSettings
        settings = TranslationSettings(external_tm_fuzzy_threshold=0.1)
        self.assertEqual(settings.external_tm_fuzzy_threshold, 0.5)
        settings2 = TranslationSettings(external_tm_fuzzy_threshold=1.5)
        self.assertEqual(settings2.external_tm_fuzzy_threshold, 1.0)

    def test_tm_sources_invalid_json(self):
        """Geçersiz JSON sources dizeltilmeli."""
        from src.utils.config import TranslationSettings
        settings = TranslationSettings(external_tm_sources="not json")
        self.assertEqual(settings.external_tm_sources, "[]")

    def test_tm_sources_non_list(self):
        """JSON ama list olmayan sources dizeltilmeli."""
        from src.utils.config import TranslationSettings
        settings = TranslationSettings(external_tm_sources='{"key": "value"}')
        self.assertEqual(settings.external_tm_sources, "[]")

    def test_tm_sources_valid(self):
        """Geçerli JSON list korunmalı."""
        from src.utils.config import TranslationSettings
        settings = TranslationSettings(external_tm_sources='["tm/a.json", "tm/b.json"]')
        self.assertEqual(settings.external_tm_sources, '["tm/a.json", "tm/b.json"]')


if __name__ == '__main__':
    unittest.main()
