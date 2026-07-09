"""
v2.7.2 Extraction Engine Verification Script
Tests both positive captures and false positive prevention.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())

from src.core.parser import RenPyParser
from src.core.deep_extraction import DeepVariableAnalyzer, DeepExtractionConfig

# ============================================================================
# 1) DeepVariableAnalyzer Score Tests
# ============================================================================
def test_variable_scores():
    """Verify variable name scoring logic."""
    analyzer = DeepVariableAnalyzer(DeepExtractionConfig())
    
    test_cases = [
        # (var_name, expected_pass, reason)
        ("MC_NAME",         True,  "Translatable suffix _NAME"),
        ("QUEST_DESC",      True,  "Translatable suffix _DESC"),
        ("QUEST_TITLE",     True,  "Translatable suffix _TITLE"),
        ("game_title",      True,  "Translatable suffix _title"),
        ("intro_text",      True,  "Translatable suffix _text"),
        ("VERSION",         False, "Short uppercase constant, no translatable suffix"),
        ("GAME_STATE",      False, "Uppercase constant without translatable suffix"),
        ("IMAGE_PATH",      False, "Non-translatable suffix _PATH"),
        ("config.name",     True,  "config.name is whitelisted"),
        ("_INTERNAL",       False, "Starts with underscore (private)"),
        ("persistent.flag", False, "persistent namespace penalized"),
    ]
    
    print("=" * 72)
    print("  VARIABLE SCORING TEST")
    print("=" * 72)
    
    all_pass = True
    for var_name, expected_pass, reason in test_cases:
        score = analyzer.score_var_name(var_name)
        actual_pass = analyzer.is_likely_translatable(var_name)
        status = "PASS" if actual_pass == expected_pass else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"  [{status}] {var_name:25s} | score={score:.2f} | likely={actual_pass} | expected={expected_pass} | {reason}")
    
    return all_pass


# ============================================================================
# 2) Full RenPyParser Extraction Test
# ============================================================================
def test_extraction():
    """Verify full extraction pipeline against edge cases."""
    parser = RenPyParser()

    # Build test file
    test_content = """
# === POSITIVE CASES (should extract) ===
define MC_NAME = "Rhiannon"
default QUEST_DESC = "Kill the dragon"

label start:
    "This is a narrator line."
    e "Hello, world!"

    menu:
        "Go left":
            pass
        "Go right":
            pass

    $ gallery.button("Unlockable Gallery Item")
    $ gallery_gup.button("Special Item")
    $ renpy.notify("Alert!")
    $ my_ui.notify("Something happened!")

# === NEGATIVE CASES (should NOT extract) ===
define VERSION = "1.2.3"
define IMAGE_PATH = "images/bg/forest.png"
$ renpy.play("audio/music.ogg")
$ gallery.image("images/gallery/pic1.webp")
$ config.developer = "auto"
"""
    
    test_file = Path("tests/_v272_test.rpy")
    test_file.write_text(test_content.strip(), encoding="utf-8")
    
    entries = parser.extract_text_entries(test_file)
    extracted_texts = set(e["text"] for e in entries)
    
    # After test, clean up
    test_file.unlink(missing_ok=True)
    
    # Define expectations
    must_extract = [
        ("Rhiannon",                 "MC_NAME constant"),
        ("Kill the dragon",          "QUEST_DESC constant"),
        ("This is a narrator line.", "Narrator text"),
        ("Hello, world!",            "Dialogue text"),
        ("Go left",                  "Menu choice"),
        ("Go right",                 "Menu choice"),
        ("Unlockable Gallery Item",  "gallery.button"),
        ("Special Item",             "gallery_gup.button"),
        ("Alert!",                   "renpy.notify"),
    ]
    
    must_not_extract = [
        ("1.2.3",                    "VERSION - technical constant"),
        ("images/bg/forest.png",     "IMAGE_PATH - file path"),
        ("audio/music.ogg",          "renpy.play - audio path"),
        ("images/gallery/pic1.webp", "gallery.image - image path"),
        ("auto",                     "config.developer - technical value"),
    ]
    
    print()
    print("=" * 72)
    print("  FULL EXTRACTION TEST")
    print("=" * 72)
    
    all_pass = True
    
    print("\n  [MUST EXTRACT]")
    for text, reason in must_extract:
        found = text in extracted_texts
        status = "PASS" if found else "FAIL"
        if not found:
            all_pass = False
        print(f"    [{status}] {text:35s} | {reason}")
    
    print("\n  [MUST NOT EXTRACT (false positives)]")
    for text, reason in must_not_extract:
        found = text in extracted_texts
        status = "PASS" if not found else "FAIL"
        if found:
            all_pass = False
        print(f"    [{status}] {text:35s} | {reason}")
    
    # Show all extracted for debug
    print(f"\n  --- All {len(extracted_texts)} unique extracted texts ---")
    for t in sorted(extracted_texts):
        print(f"    > {t}")
    
    return all_pass


# ============================================================================
# 3) is_meaningful_text Edge Cases
# ============================================================================
def test_meaningful_text():
    """Test is_meaningful_text heuristics."""
    parser = RenPyParser()
    
    test_cases = [
        # (text, expected_meaningful, reason)
        ("Hello, world!",       True,  "Normal text"),
        ("game_state",          False, "snake_case ID"),
        ("auto",                False, "Technical term in renpy_technical_terms"),
        ("config.developer",    False, "Dotted technical path"),
        ("images/bg/forest.png",False, "File path"),
        ("audio/music.ogg",     False, "Audio path"),
        ("This is a sentence.", True,  "Real sentence"),
        ("Kill the dragon",     True,  "Multi-word narrative text"),
        ("Unlockable Gallery Item", True, "Multi-word UI text"),
        ("{color=#f00}Red text{/color}", True, "Text with Ren'Py display tags"),
        ("{b}Bold text{/b}",    True,  "Text with bold tags"),
        ("{size=24}Big{/size}",  True,  "Text with size tags"),
        ("{0} items found",     True,  "Python format with text"),
        ("{}",                  False, "Empty format placeholder"),
        ("{:3d}",               False, "Python format spec only"),
        ("1.2.3",               False, "Version number"),
        ("clear",               False, "NVL command"),
        ("bg_forest",           False, "snake_case ID"),
        ("player_name",         False, "snake_case ID"),
    ]
    
    print()
    print("=" * 72)
    print("  IS_MEANINGFUL_TEXT TEST")
    print("=" * 72)
    
    all_pass = True
    for text, expected, reason in test_cases:
        actual = parser.is_meaningful_text(text)
        status = "PASS" if actual == expected else "FAIL"
        if actual != expected:
            all_pass = False
        print(f"  [{status}] {text:40s} | expected={expected!s:5s} | actual={actual!s:5s} | {reason}")
    
    return all_pass


# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    results = []
    results.append(("Variable Scoring",   test_variable_scores()))
    results.append(("Full Extraction",     test_extraction()))
    results.append(("Meaningful Text",     test_meaningful_text()))
    
    print()
    print("=" * 72)
    print("  FINAL SUMMARY")
    print("=" * 72)
    total_pass = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        if not passed:
            total_pass = False
        print(f"  [{status}] {name}")
    
    print()
    if total_pass:
        print("  ALL TESTS PASSED!")
    else:
        print("  SOME TESTS FAILED - review output above.")
    
    sys.exit(0 if total_pass else 1)
