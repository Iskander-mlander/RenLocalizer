"""
Tests for Deep Extraction module (v2.7.1).

Covers:
- DeepExtractionConfig tier classification
- DeepVariableAnalyzer heuristic scoring
- FStringReconstructor template extraction
- MultiLineStructureParser detection and extraction
- Parser integration (bare define/default, tooltip, f-string, API calls)
- RPYC reader integration (new DeepStringVisitor handlers)
- False positive prevention
"""

import ast
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.deep_extraction import (
    DeepExtractionConfig,
    DeepVariableAnalyzer,
    FStringReconstructor,
    MultiLineStructureParser,
    confidence_band,
    resolve_minimum_extraction_confidence,
    score_extraction_confidence,
)
from src.core.parser import RenPyParser
from src.utils.config import TranslationSettings


# =============================================================================
# DeepExtractionConfig Tests
# =============================================================================

class TestDeepExtractionConfig(unittest.TestCase):
    """Test tier classification of API calls."""

    def test_tier1_contains_renpy_notify(self):
        self.assertIn("renpy.notify", DeepExtractionConfig.TIER1_TEXT_CALLS)

    def test_tier1_contains_confirm(self):
        self.assertIn("Confirm", DeepExtractionConfig.TIER1_TEXT_CALLS)

    def test_tier2_contains_quicksave(self):
        self.assertIn("QuickSave", DeepExtractionConfig.TIER2_CONTEXTUAL_CALLS)

    def test_tier3_blacklists_jump(self):
        self.assertIn("Jump", DeepExtractionConfig.TIER3_BLACKLIST_CALLS)

    def test_tier3_blacklists_play(self):
        self.assertIn("Play", DeepExtractionConfig.TIER3_BLACKLIST_CALLS)

    def test_tier3_blacklists_preference(self):
        self.assertIn("Preference", DeepExtractionConfig.TIER3_BLACKLIST_CALLS)

    def test_config_text_vars(self):
        self.assertIn("config.name", DeepExtractionConfig.CONFIG_TEXT_VARS)
        self.assertIn("config.window_title", DeepExtractionConfig.CONFIG_TEXT_VARS)

    def test_config_skip_vars(self):
        self.assertIn("config.version", DeepExtractionConfig.CONFIG_SKIP_VARS)
        self.assertIn("config.save_directory", DeepExtractionConfig.CONFIG_SKIP_VARS)


class TestExtractionConfidence(unittest.TestCase):
    def test_dialogue_scores_high(self):
        score = score_extraction_confidence(
            "Hello, world!",
            text_type="dialogue",
            context="say",
            context_path=["label:start"],
        )
        self.assertGreaterEqual(score, 0.85)
        self.assertEqual(confidence_band(score), "confirmed")

    def test_technical_string_scores_low(self):
        score = score_extraction_confidence(
            "images/bg/forest.png",
            text_type="string",
            context="config",
        )
        self.assertLess(score, 0.2)
        self.assertEqual(confidence_band(score), "candidate")

    def test_mode_to_threshold_mapping(self):
        self.assertAlmostEqual(
            resolve_minimum_extraction_confidence(TranslationSettings()),
            0.58,
        )
        self.assertAlmostEqual(
            resolve_minimum_extraction_confidence(TranslationSettings(extraction_mode="strict")),
            0.85,
        )
        self.assertAlmostEqual(
            resolve_minimum_extraction_confidence(TranslationSettings(extraction_mode="balanced")),
            0.58,
        )
        self.assertAlmostEqual(
            resolve_minimum_extraction_confidence(TranslationSettings(extraction_mode="aggressive")),
            0.35,
        )


class TestDeepScanStructure(unittest.TestCase):
    def test_tagged_data_value_is_meaningful(self):
        parser = RenPyParser()
        self.assertTrue(parser._is_meaningful_data_value("{color=#5175ea}*giggle*{/w}", "title"))
        self.assertTrue(parser._is_deep_scan_candidate("{color=#5175ea}*giggle*{/w}", True, "renpy.notify('x')"))


# =============================================================================
# DeepVariableAnalyzer Tests
# =============================================================================

class TestDeepVariableAnalyzer(unittest.TestCase):
    """Test variable name heuristic scoring."""

    def setUp(self):
        self.analyzer = DeepVariableAnalyzer()

    # --- Translatable variable names ---
    def test_quest_title_is_translatable(self):
        self.assertTrue(self.analyzer.is_likely_translatable("quest_title"))

    def test_player_name_is_translatable(self):
        self.assertTrue(self.analyzer.is_likely_translatable("player_name"))

    def test_chapter_description_is_translatable(self):
        self.assertTrue(self.analyzer.is_likely_translatable("chapter_description"))

    def test_greeting_is_translatable(self):
        self.assertTrue(self.analyzer.is_likely_translatable("greeting"))

    def test_npc_dialogue_is_translatable(self):
        self.assertTrue(self.analyzer.is_likely_translatable("npc_dialogue"))

    def test_tooltip_hint_is_translatable(self):
        self.assertTrue(self.analyzer.is_likely_translatable("tooltip_hint"))

    def test_config_name_is_translatable(self):
        self.assertTrue(self.analyzer.is_likely_translatable("config.name"))

    def test_config_window_title_is_translatable(self):
        self.assertTrue(self.analyzer.is_likely_translatable("config.window_title"))

    # --- Non-translatable variable names ---
    def test_audio_volume_not_translatable(self):
        self.assertFalse(self.analyzer.is_likely_translatable("audio_volume"))

    def test_save_path_not_translatable(self):
        self.assertFalse(self.analyzer.is_likely_translatable("save_path"))

    def test_image_file_not_translatable(self):
        self.assertFalse(self.analyzer.is_likely_translatable("image_file"))

    def test_persistent_flags_not_translatable(self):
        self.assertFalse(self.analyzer.is_likely_translatable("persistent.flags"))

    def test_config_version_not_translatable(self):
        self.assertFalse(self.analyzer.is_likely_translatable("config.version"))

    def test_style_color_not_translatable(self):
        self.assertFalse(self.analyzer.is_likely_translatable("style.color"))

    def test_font_size_not_translatable(self):
        self.assertFalse(self.analyzer.is_likely_translatable("font_size"))

    # --- Classification ---
    def test_classify_translatable(self):
        self.assertEqual(self.analyzer.classify("quest_title"), "translatable")

    def test_classify_non_translatable(self):
        self.assertEqual(self.analyzer.classify("persistent.flags"), "non_translatable")

    def test_classify_uncertain(self):
        # A generic variable like "counter" should be uncertain
        result = self.analyzer.classify("counter")
        self.assertIn(result, ("uncertain", "non_translatable"))

    # --- Technical strings ---
    def test_file_path_is_technical(self):
        self.assertTrue(self.analyzer.is_technical_string("images/bg.png"))

    def test_color_hex_is_technical(self):
        self.assertTrue(self.analyzer.is_technical_string("#ff0000"))

    def test_url_is_technical(self):
        self.assertTrue(self.analyzer.is_technical_string("https://example.com"))

    def test_snake_case_id_is_technical(self):
        self.assertTrue(self.analyzer.is_technical_string("my_variable"))

    def test_normal_text_not_technical(self):
        self.assertFalse(self.analyzer.is_technical_string("Hello, world!"))

    def test_sentence_not_technical(self):
        self.assertFalse(self.analyzer.is_technical_string("The dragon attacks!"))


# =============================================================================
# FStringReconstructor Tests
# =============================================================================

class TestFStringReconstructor(unittest.TestCase):
    """Test f-string template extraction."""

    def test_simple_fstring(self):
        result = FStringReconstructor.extract_template("Welcome {name}!")
        self.assertEqual(result, "Welcome [name]!")

    def test_fstring_multiple_exprs(self):
        result = FStringReconstructor.extract_template("Day {day}: {weather}")
        self.assertIn("[day]", result)
        self.assertIn("[weather]", result)

    def test_fstring_mostly_dynamic_returns_none(self):
        # More than 70% dynamic → skip
        result = FStringReconstructor.extract_template("{a}{b}{c}")
        self.assertIsNone(result)

    def test_fstring_no_exprs(self):
        # Plain string, no expressions → still valid template
        result = FStringReconstructor.extract_template("Hello world")
        self.assertEqual(result, "Hello world")

    def test_fstring_empty_returns_none(self):
        result = FStringReconstructor.extract_template("")
        self.assertIsNone(result)

    def test_fstring_only_numbers_returns_none(self):
        result = FStringReconstructor.extract_template("12345")
        self.assertIsNone(result)

    def test_ast_node_extraction(self):
        code = 'f"Welcome back, {player}!"'
        tree = ast.parse(code, mode='eval')
        node = tree.body  # JoinedStr
        template = FStringReconstructor.extract_from_ast_node(node, code)
        self.assertIsNotNone(template)
        self.assertIn("Welcome back", template)
        self.assertIn("[player]", template)


# =============================================================================
# MultiLineStructureParser Tests
# =============================================================================

class TestMultiLineStructureParser(unittest.TestCase):
    """Test multi-line define/default structure detection and extraction."""

    def test_detect_dict_start(self):
        line = 'define quest_data = {'
        info = MultiLineStructureParser.detect_multiline_start(line)
        self.assertIsNotNone(info)
        self.assertEqual(info["var_name"], "quest_data")
        self.assertEqual(info["start_char"], "{")

    def test_detect_list_start(self):
        line = 'default chapter_names = ['
        info = MultiLineStructureParser.detect_multiline_start(line)
        self.assertIsNotNone(info)
        self.assertEqual(info["var_name"], "chapter_names")
        self.assertEqual(info["start_char"], "[")

    def test_single_line_not_detected(self):
        line = 'define name = {"title": "X"}'
        info = MultiLineStructureParser.detect_multiline_start(line)
        self.assertIsNone(info)  # Closes on same line

    def test_collect_block(self):
        lines = [
            'define data = {',
            '    "title": "Hello",',
            '    "id": 5,',
            '}',
            'label start:',
        ]
        info = {"start_char": "{", "indent": 0, "var_name": "data"}
        code, end_idx = MultiLineStructureParser.collect_block(lines, 0, info)
        self.assertEqual(end_idx, 3)
        self.assertIn('"title"', code)

    def test_extract_whitelisted_keys(self):
        code = '''define quest = {
    "title": "Dragon Slayer",
    "desc": "Kill the dragon",
    "id": "q001",
}'''
        results = MultiLineStructureParser.extract_translatable_values("quest", code)
        texts = [r["text"] for r in results]
        self.assertIn("Dragon Slayer", texts)
        self.assertIn("Kill the dragon", texts)
        # "id" key is blacklisted → q001 should NOT be extracted
        self.assertNotIn("q001", texts)

    def test_extract_list_strings(self):
        code = '''define names = [
    "Alice",
    "Bob",
    "Charlie",
]'''
        results = MultiLineStructureParser.extract_translatable_values("names", code)
        texts = [r["text"] for r in results]
        self.assertIn("Alice", texts)
        self.assertIn("Bob", texts)
        self.assertIn("Charlie", texts)

    def test_nested_dict_in_list(self):
        code = '''define achievements = [
    {"name": "First Blood", "desc": "Win your first battle"},
    {"name": "Explorer", "desc": "Visit all locations"},
]'''
        results = MultiLineStructureParser.extract_translatable_values("achievements", code)
        texts = [r["text"] for r in results]
        self.assertIn("First Blood", texts)
        self.assertIn("Win your first battle", texts)
        self.assertIn("Explorer", texts)


# =============================================================================
# Parser Integration Tests
# =============================================================================

class TestParserDeepExtraction(unittest.TestCase):
    """Integration tests for parser.py deep extraction features."""

    def setUp(self):
        from src.core.parser import RenPyParser
        self.parser = RenPyParser()

    def _extract_from_content(self, content: str) -> list:
        """Helper: write content to temp file and extract."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rpy', delete=False, encoding='utf-8') as f:
            f.write(content)
            f.flush()
            path = f.name
        try:
            return self.parser.extract_text_entries(path)
        finally:
            os.unlink(path)

    def _deep_extract(self, content: str) -> list:
        """Helper: write content and run full deep scan."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rpy', delete=False, encoding='utf-8') as f:
            f.write(content)
            f.flush()
            path = f.name
        try:
            return self.parser.extract_with_deep_scan(path)
        finally:
            os.unlink(path)

    def test_bare_define_translatable(self):
        """Bare define with translatable variable name should be extracted."""
        content = 'define quest_title = "The Dark Forest"\n'
        entries = self._extract_from_content(content)
        texts = [e['text'] for e in entries]
        self.assertIn("The Dark Forest", texts)

    def test_bare_define_technical_skipped(self):
        """Bare define with technical variable name should be skipped."""
        content = 'define audio_volume = "0.5"\n'
        entries = self._extract_from_content(content)
        texts = [e['text'] for e in entries]
        self.assertNotIn("0.5", texts)

    def test_bare_default_translatable(self):
        """Bare default with translatable variable name should be extracted."""
        content = 'default player_name = "Hero"\n'
        entries = self._extract_from_content(content)
        texts = [e['text'] for e in entries]
        self.assertIn("Hero", texts)

    def test_bare_default_nontranslatable_skipped(self):
        """Bare default with persistent prefix should be skipped."""
        content = 'default persistent.flags = "none"\n'
        entries = self._extract_from_content(content)
        texts = [e['text'] for e in entries]
        self.assertNotIn("none", texts)

    def test_tooltip_property_extraction(self):
        """Tooltip property in screen language should be extracted."""
        content = '''screen save_screen():
    textbutton "Save" action FileSave(1) tooltip "Quick save to slot 1"
'''
        entries = self._extract_from_content(content)
        texts = [e['text'] for e in entries]
        self.assertIn("Quick save to slot 1", texts)

    def test_fstring_extraction_in_main_pass(self):
        """f-string assignment should extract template."""
        content = '$ message = f"Welcome back, {player_name}!"\n'
        entries = self._extract_from_content(content)
        texts = [e['text'] for e in entries]
        found = any("Welcome back" in t for t in texts)
        self.assertTrue(found, f"Expected f-string template in: {texts}")

    def test_python_text_call_renpy_confirm(self):
        """$ renpy.confirm() should be extracted."""
        content = '$ renpy.confirm("Are you sure you want to delete?")\n'
        entries = self._extract_from_content(content)
        texts = [e['text'] for e in entries]
        self.assertIn("Are you sure you want to delete?", texts)

    def test_quicksave_message_extraction(self):
        """QuickSave(message=...) should be extracted."""
        content = '    textbutton "QS" action QuickSave(message="Game saved!")\n'
        entries = self._extract_from_content(content)
        texts = [e['text'] for e in entries]
        self.assertIn("Game saved!", texts)

    def test_call_screen_title_argument_extraction(self):
        """call screen helper titles should be extracted conservatively."""
        content = '    call screen menu_interactive_scr("COMMUNICATION UPLINK ESTABLISHED...", comOptions, [])\n'
        entries = self._extract_from_content(content)
        texts = [e['text'] for e in entries]
        self.assertIn("COMMUNICATION UPLINK ESTABLISHED...", texts)

    def test_call_screen_mode_argument_is_skipped(self):
        """Low-signal lowercase mode arguments should not become UI text."""
        content = '    call screen stasis_pod_mgr_scr("warehouse", GAME.base.storedGoods)\n'
        entries = self._extract_from_content(content)
        texts = [e['text'] for e in entries]
        self.assertNotIn("warehouse", texts)

    def test_displayable_helper_label_argument_extraction(self):
        """Displayable helper calls should extract user-facing labels but skip asset paths."""
        content = '''screen location_navigation():
    imagebutton:
        idle build_loc_icon("pool_icon.png", "Pool", pool_overlay)
        hover build_loc_icon(im.MatrixColor("pool_icon.png", im.matrix.brightness(0.35)), "Hot Springs", pool_overlay)
'''
        entries = self._extract_from_content(content)
        texts = [e['text'] for e in entries]
        self.assertIn("Pool", texts)
        self.assertIn("Hot Springs", texts)
        self.assertNotIn("pool_icon.png", texts)

    def test_multiline_dict_deep_scan(self):
        """Multi-line dict with whitelisted keys should be extracted in deep scan."""
        content = '''define quest_data = {
    "title": "Dragon Slayer",
    "desc": "Kill the mighty dragon",
    "id": "q001",
}
'''
        entries = self._deep_extract(content)
        texts = [e['text'] for e in entries]
        self.assertIn("Dragon Slayer", texts)
        self.assertIn("Kill the mighty dragon", texts)
        # id is blacklisted
        self.assertNotIn("q001", texts)

    def test_extract_with_deep_scan_reuses_primary_extraction_pass(self):
        content = '''define quest_data = {
    "title": "Dragon Slayer",
}
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rpy', delete=False, encoding='utf-8') as f:
            f.write(content)
            f.flush()
            path = f.name
        try:
            with patch.object(self.parser, "extract_text_entries", wraps=self.parser.extract_text_entries) as wrapped_extract:
                self.parser.extract_with_deep_scan(path)
            self.assertEqual(wrapped_extract.call_count, 1)
        finally:
            os.unlink(path)

    def test_excessive_length_warning_is_logged_once_per_parser_instance(self):
        content = "a" * 12000 + "\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rpy', delete=False, encoding='utf-8') as f:
            f.write(content)
            f.flush()
            path = f.name
        try:
            with patch.object(self.parser.logger, "warning") as warning_mock:
                self.parser.extract_text_entries(path)
                self.parser.extract_text_entries(path)
            self.assertEqual(warning_mock.call_count, 1)
        finally:
            os.unlink(path)

    def test_parse_directory_progress_callback_reports_each_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            first = Path(tmp_dir) / "one.rpy"
            second = Path(tmp_dir) / "two.rpy"
            first.write_text('label start:\n    "One"\n', encoding='utf-8')
            second.write_text('label next:\n    "Two"\n', encoding='utf-8')

            seen: list[tuple[int, int, str]] = []

            self.parser.parse_directory(
                tmp_dir,
                progress_callback=lambda current, total, path: seen.append((current, total, Path(path).name)),
            )

            self.assertEqual(len(seen), 2)
            self.assertEqual(seen[0][0], 1)
            self.assertEqual(seen[-1][1], 2)
            self.assertEqual({item[2] for item in seen}, {"one.rpy", "two.rpy"})

    def test_parse_directory_progress_totals_ignore_tl_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            game_dir = Path(tmp_dir) / "game"
            tl_dir = game_dir / "tl" / "turkish"
            game_dir.mkdir(parents=True)
            tl_dir.mkdir(parents=True)

            source_file = game_dir / "script.rpy"
            tl_file = tl_dir / "script.rpy"
            source_file.write_text('label start:\n    "Source"\n', encoding='utf-8')
            tl_file.write_text('translate turkish strings:\n    old "X"\n    new "Y"\n', encoding='utf-8')

            seen: list[tuple[int, int, str]] = []
            self.parser.parse_directory(
                tmp_dir,
                progress_callback=lambda current, total, path: seen.append((current, total, Path(path).name)),
            )

            self.assertEqual(seen, [(1, 1, "script.rpy")])

    def test_extract_combined_respects_root_level_exclude_dirs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            game_dir = Path(tmp_dir) / "game"
            allowed_dir = game_dir / "story"
            blocked_dir = game_dir / "blocked"
            allowed_dir.mkdir(parents=True)
            blocked_dir.mkdir(parents=True)

            allowed_file = allowed_dir / "scene.rpy"
            blocked_file = blocked_dir / "skip_me.rpy"
            allowed_file.write_text('label start:\n    "Allowed"\n', encoding='utf-8')
            blocked_file.write_text('label skip:\n    "Blocked"\n', encoding='utf-8')

            results = self.parser.extract_combined(
                tmp_dir,
                include_rpy=True,
                include_rpyc=False,
                include_deep_scan=False,
                exclude_dirs=["blocked"],
            )

            result_names = {Path(path).name for path in results}
            self.assertIn("scene.rpy", result_names)
            self.assertNotIn("skip_me.rpy", result_names)


# =============================================================================
# False Positive Prevention Tests
# =============================================================================

class TestFalsePositivePrevention(unittest.TestCase):
    """Ensure technical strings are not extracted."""

    def setUp(self):
        self.analyzer = DeepVariableAnalyzer()

    def test_jump_label_filtered(self):
        """Jump target labels should be technical."""
        self.assertTrue(self.analyzer.is_technical_string("start_chapter"))

    def test_file_extension_filtered(self):
        self.assertTrue(self.analyzer.is_technical_string("background.png"))

    def test_color_hex_filtered(self):
        self.assertTrue(self.analyzer.is_technical_string("#ffffff"))

    def test_url_filtered(self):
        self.assertTrue(self.analyzer.is_technical_string("https://renpy.org"))

    def test_empty_string_filtered(self):
        self.assertTrue(self.analyzer.is_technical_string(""))

    def test_single_char_filtered(self):
        self.assertTrue(self.analyzer.is_technical_string("x"))

    def test_real_sentence_not_filtered(self):
        self.assertFalse(self.analyzer.is_technical_string("The hero ventures forth."))

    def test_ui_label_not_filtered(self):
        self.assertFalse(self.analyzer.is_technical_string("Save Game"))

    def test_constant_name_filtered(self):
        self.assertTrue(self.analyzer.is_technical_string("MAX_HP"))

    def test_dotted_path_filtered(self):
        self.assertTrue(self.analyzer.is_technical_string("config.settings.value"))


# =============================================================================
# Config Toggle Gating Tests
# =============================================================================

class TestConfigToggleGating(unittest.TestCase):
    """Tests that _is_deep_feature_enabled() works correctly."""

    def _make_parser(self, **overrides):
        """Create a parser with mocked config toggles."""
        from src.core.parser import RenPyParser
        mock_config = MagicMock()
        ts = MagicMock()
        ts.enable_deep_extraction = overrides.get('enable_deep_extraction', True)
        ts.deep_extraction_bare_defines = overrides.get('deep_extraction_bare_defines', True)
        ts.deep_extraction_bare_defaults = overrides.get('deep_extraction_bare_defaults', True)
        ts.deep_extraction_fstrings = overrides.get('deep_extraction_fstrings', True)
        ts.deep_extraction_multiline_structures = overrides.get('deep_extraction_multiline_structures', True)
        ts.deep_extraction_extended_api = overrides.get('deep_extraction_extended_api', True)
        ts.deep_extraction_tooltip_properties = overrides.get('deep_extraction_tooltip_properties', True)
        ts.deep_extraction_screen_arguments = overrides.get('deep_extraction_screen_arguments', True)
        ts.deep_extraction_displayable_calls = overrides.get('deep_extraction_displayable_calls', True)
        mock_config.translation_settings = ts
        return RenPyParser(config_manager=mock_config)

    def test_no_config_returns_true(self):
        from src.core.parser import RenPyParser
        parser = RenPyParser(config_manager=None)
        self.assertTrue(parser._is_deep_feature_enabled())
        self.assertTrue(parser._is_deep_feature_enabled('deep_extraction_fstrings'))

    def test_master_toggle_off_disables_all(self):
        parser = self._make_parser(enable_deep_extraction=False)
        self.assertFalse(parser._is_deep_feature_enabled())
        self.assertFalse(parser._is_deep_feature_enabled('deep_extraction_bare_defines'))

    def test_specific_toggle_off(self):
        parser = self._make_parser(deep_extraction_fstrings=False)
        self.assertTrue(parser._is_deep_feature_enabled())  # overall still on
        self.assertFalse(parser._is_deep_feature_enabled('deep_extraction_fstrings'))
        self.assertTrue(parser._is_deep_feature_enabled('deep_extraction_bare_defines'))

    def test_master_on_specific_on(self):
        parser = self._make_parser()
        self.assertTrue(parser._is_deep_feature_enabled('deep_extraction_tooltip_properties'))

    def test_screen_argument_toggle_off(self):
        parser = self._make_parser(deep_extraction_screen_arguments=False)
        self.assertFalse(parser._is_deep_feature_enabled('deep_extraction_screen_arguments'))

    def test_displayable_call_toggle_off(self):
        parser = self._make_parser(deep_extraction_displayable_calls=False)
        self.assertFalse(parser._is_deep_feature_enabled('deep_extraction_displayable_calls'))

    def test_bare_define_skipped_when_disabled(self):
        parser = self._make_parser(deep_extraction_bare_defines=False)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rpy', delete=False, encoding='utf-8') as f:
            f.write('define quest_title = "The Dark Forest"\n')
            fname = f.name
        try:
            entries = parser.extract_text_entries(Path(fname))
            texts = [e['text'] for e in entries]
            self.assertNotIn("The Dark Forest", texts)
        finally:
            os.unlink(fname)

    def test_bare_define_extracted_when_enabled(self):
        parser = self._make_parser(deep_extraction_bare_defines=True)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rpy', delete=False, encoding='utf-8') as f:
            f.write('define quest_title = "The Dark Forest"\n')
            fname = f.name
        try:
            entries = parser.extract_text_entries(Path(fname))
            texts = [e['text'] for e in entries]
            self.assertIn("The Dark Forest", texts)
        finally:
            os.unlink(fname)


# =============================================================================
# Triple-Quote String Tracking Tests
# =============================================================================

class TestTripleQuoteHandling(unittest.TestCase):
    """Tests that triple-quoted strings don't break bracket counting."""

    def test_triple_quote_with_brace_inside(self):
        """Triple-quoted string containing } should not close the dict."""
        line = '    define data = {"desc": """A string with } inside""",'
        result = MultiLineStructureParser.detect_multiline_start(
            'define data = {"desc": """A string with } inside""",')
        # The dict has one { and no real }, so it's multiline
        self.assertIsNotNone(result)

    def test_single_line_triple_complete(self):
        """Single-line dict with triple-quote that properly closes."""
        line = 'define x = {"key": """value"""}'
        result = MultiLineStructureParser.detect_multiline_start(line)
        self.assertIsNone(result)  # Complete on one line

    def test_count_brackets_ignores_braces_in_triple(self):
        """_count_brackets_in_line should ignore brackets inside triple-quotes."""
        line = '    """This has { and } inside""", "normal"'
        count = MultiLineStructureParser._count_brackets_in_line(line, '{', '}')
        self.assertEqual(count, 0)

    def test_count_brackets_normal_string(self):
        """Regular string braces should still be ignored."""
        line = '    "text with }" data'
        count = MultiLineStructureParser._count_brackets_in_line(line, '{', '}')
        self.assertEqual(count, 0)


# =============================================================================
# FString Edge Case Tests
# =============================================================================

class TestFStringEdgeCases(unittest.TestCase):
    """Additional edge case tests for f-string extraction."""

    def test_format_specifier(self):
        """f-string with format specifier: {value:.2f}"""
        result = FStringReconstructor.extract_template("Score: {value:.2f} points")
        self.assertIsNotNone(result)
        self.assertIn("[", result)
        self.assertIn("points", result)

    def test_conversion_flag(self):
        """f-string with conversion flag: {name!r}"""
        result = FStringReconstructor.extract_template("Name: {name!r} entered")
        self.assertIsNotNone(result)
        self.assertIn("entered", result)

    def test_extract_from_ast_node_returns_none_on_failure(self):
        """When source segment is unavailable, extract_from_ast_node should return None."""
        # Create a minimal JoinedStr with FormattedValue that has no source mapping
        node = ast.JoinedStr(
            values=[
                ast.Constant(value="Hello "),
                ast.FormattedValue(
                    value=ast.Name(id="x", ctx=ast.Load()),
                    conversion=-1,
                    format_spec=None,
                ),
            ]
        )
        # Empty source code → get_source_segment will fail → should return None
        result = FStringReconstructor.extract_from_ast_node(node, "")
        self.assertIsNone(result)

    def test_pure_placeholder_rejected(self):
        """f-string that's all placeholder should be rejected."""
        self.assertIsNone(FStringReconstructor.extract_template("{x}{y}{z}"))

    def test_mostly_static_extracted(self):
        """f-string with mostly static text should be extracted."""
        result = FStringReconstructor.extract_template("Welcome back, {name}!")
        self.assertIsNotNone(result)
        self.assertEqual(result, "Welcome back, [name]!")


if __name__ == '__main__':
    unittest.main()
