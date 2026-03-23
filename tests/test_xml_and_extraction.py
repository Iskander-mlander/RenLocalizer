import unittest
import sys
import os
import ast
import re

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.syntax_guard import protect_renpy_syntax_xml, restore_renpy_syntax_xml
from src.core.pyparse_grammar import extract_with_pyparsing
import src.core.rpyc_reader as rpyc_reader

class MockParser:
    def preserve_placeholders(self, text):
        return text, {}

class MockExtractor:
    def __init__(self):
        self.extracted = []
        self.parser = MockParser()

    def _add_text(self, text, line, type, context='', character='', placeholder_map=None, node_type=''):
        self.extracted.append({
            'text': text,
            'line': line,
            'type': type,
            'context': context
        })
    
    def _is_technical_string(self, text, context=''):
        return False

    def _is_deep_feature_enabled(self, feature=None):
        return True
        
    # Inject our new method manually for testing since we can't easily instantiate the full RPYCReader with deps
    _extract_strings_from_code_ast = rpyc_reader.ASTTextExtractor._extract_strings_from_code_ast

class TestXMLAndExtraction(unittest.TestCase):

    def test_xml_protection_basic(self):
        text = "Hello [player]!"
        protected, ph = protect_renpy_syntax_xml(text)
        # Expected: Hello <ph id="0">[player]</ph>!
        self.assertIn('<ph id="0">[player]</ph>', protected)
        self.assertIn('0', ph)
        self.assertEqual(ph['0'], '[player]')

    def test_xml_protection_tags(self):
        text = "{b}Bold{/b} Text"
        protected, ph = protect_renpy_syntax_xml(text)
        # Expected: <ph id="0">{b}</ph>Bold<ph id="1">{/b}</ph> Text
        # Note: Order of IDs might vary but structure should match
        self.assertTrue('<ph' in protected)
        self.assertEqual(len(ph), 2)

    def test_xml_restoration(self):
        text = "Hello <ph id=\"0\">[player]</ph>!"
        ph = {'0': '[player]'}
        restored = restore_renpy_syntax_xml(text, ph)
        self.assertEqual(restored, "Hello [player]!")

    def test_xml_restoration_fuzzy(self):
        # Test AI modification: Spaces inside tags
        text = "Hello <ph id = \"0\"> [player] </ph>!"
        ph = {'0': '[player]'}
        restored = restore_renpy_syntax_xml(text, ph)
        self.assertEqual(restored, "Hello [player]!")

    def test_atl_extraction(self):
        content = """
transform my_anim:
    xalign 0.5
    text "Animated Text"
    linear 1.0 alpha 0.0
"""
        entries = extract_with_pyparsing(content, "test.rpy")
        found = any(e['text'] == "Animated Text" for e in entries)
        self.assertTrue(found, "Failed to extract text from ATL transform block")

    def test_f_string_extraction(self):
        extractor = MockExtractor()
        code = "msg = f\"Values: {x}, {y}\""
        extractor._extract_strings_from_code_ast(code, 10)
        
        found = False
        for e in extractor.extracted:
            # v2.7.1: FStringReconstructor converts {expr} to [expr] for Ren'Py compatibility
            if "Values:" in e['text'] and ("[x]" in e['text'] or "{x}" in e['text']):
                 found = True
                 break
        self.assertTrue(found, f"Failed to extract f-string. Extracted: {[e['text'] for e in extractor.extracted]}")

    def test_nested_dict_extraction(self):
        extractor = MockExtractor()
        code = """
my_data = {
    "title": "Chapter 1",
    "desc": f"The journey of {hero}"
}
"""
        extractor._extract_strings_from_code_ast(code, 20)
        
        titles = [e['text'] for e in extractor.extracted]
        self.assertIn("Chapter 1", titles)
        # Check f-string in dict
        # v2.7.1: FStringReconstructor converts {hero} to [hero] for Ren'Py compatibility
        f_str_found = any("The journey of" in t and ("[hero]" in t or "{hero}" in t) for t in titles)
        self.assertTrue(f_str_found, f"Failed to extract f-string inside dict. Extracted: {titles}")
        
        # Verify context
        # Context structure: /item for values, maybe var:my_data/title if my_data is assigned
        # Logic in vistor:
        # visit_Assign -> stack: var:my_data
        # visit_Dict -> stack: var:my_data/title
        for e in extractor.extracted:
            if e['text'] == "Chapter 1":
                self.assertIn("title", e['context'])

if __name__ == '__main__':
    unittest.main()
