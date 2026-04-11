import os
import json
import pytest

class MockRenpyLoader:
    class MockApk:
        def open(self, path):
            return None
    game_apks = [MockApk()]

class MockRenpy:
    def __init__(self):
        self.loader = MockRenpyLoader()

class MockPreferences:
    def __init__(self):
        self.language = "tr"

class MockStore:
    _preferences = MockPreferences()

import sys
sys.modules["renpy"] = MockRenpy()
sys.modules["renpy.store"] = MockStore()

from src.core import runtime_hook_template as rht

def test_template_logic(tmp_path):
    tmap = {
        "Score: [score]": "Skor: [score]",
        "Hello {name}!": "Merhaba {name}!",
        "HP: %d": "SH: %d",
        "Just a test": "Sadece test",
        "Invalid [a] and [b]": "Gecersiz [a] [b]",
        "S [x]": "S [x]",
        "I won't say goodbye.": "Vedalaşmayacağım.",
        "The continuation of this story is being created right now. So I won't say goodbye.": "Bu hikayenin devamı şu anda hazırlanıyor. Bu yüzden vedalaşmayacağım."
    }
    
    json_path = tmp_path / "strings.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(tmap, f)
        
    # Render hook string
    hook_code = rht.render_runtime_hook("tr", runtime_string_diagnostics=True)
    
    # Strip init -999 python: and dedent
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
    
    body = "\n".join(body_lines)
    
    # Remove top-level global declaration that breaks python module exec
    body = body.replace("global _rl_prev_say_menu_filter, _rl_prev_replace_text", "")
    
    # Create namespace map
    class MockConfig:
        gamedir = str(tmp_path)
        say_menu_text_filter = None
        replace_text = None
        all_character_callbacks = []
    
    ns = {
        "renpy": sys.modules["renpy"],
        "config": MockConfig(),
        "_preferences": MockPreferences()
    }
    exec(body, ns)
    
    old_finder = ns["_rl_find_strings_json"]
    ns["_rl_find_strings_json"] = lambda: str(json_path)
    
    try:
        loaded = ns["_rl_load_translations"]()
        assert loaded is True
        
        # Test templates loaded
        assert len(ns["_rl_template_map"]) == 3
        assert ns["_rl_template_prefix_index"]
        assert ns["_rl_phrase_index"]
        assert ns["_rl_replace_cache"] == {}
        
        assert ns["_rl_replace_text"]("Score: 1500") == "Skor: 1500"
        assert ns["_rl_replace_text"]("Hello Melih!") == "Merhaba Melih!"
        assert ns["_rl_replace_text"]("HP: 99") == "SH: 99"
        assert ns["_rl_replace_text"]("I won’t say goodbye.") == "Vedalaşmayacağım."
        assert ns["_rl_replace_text"]("And the continuation of this story is being created right now. So I won't say goodbye.") == "And Bu hikayenin devamı şu anda hazırlanıyor. Bu yüzden vedalaşmayacağım."
        assert ns["_rl_replace_cache"]
        assert ns["_rl_normalized_lookup_cache"]

        assert ns["_rl_replace_text"]("Invalid 1 and 2") == "Invalid 1 and 2"
    finally:
        ns["_rl_find_strings_json"] = old_finder


def test_runtime_hook_enables_rtl_for_persian(tmp_path):
    tmap = {"Settings": "تنظیمات"}
    json_path = tmp_path / "strings.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(tmap, f)

    hook_code = rht.render_runtime_hook("persian", runtime_string_diagnostics=True)
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

    body = "\n".join(body_lines)
    body = body.replace("global _rl_prev_say_menu_filter, _rl_prev_replace_text", "")

    class MockConfig:
        gamedir = str(tmp_path)
        say_menu_text_filter = None
        replace_text = None
        all_character_callbacks = []
        rtl = False

    class MockStyleObj:
        language = None
        reading_order = None

    class MockStyle:
        default = MockStyleObj()
        say_dialogue = MockStyleObj()

    class MockPersianPreferences:
        language = "persian"

    ns = {
        "renpy": sys.modules["renpy"],
        "config": MockConfig(),
        "_preferences": MockPersianPreferences(),
        "style": MockStyle(),
    }
    exec(body, ns)

    old_finder = ns["_rl_find_strings_json"]
    ns["_rl_find_strings_json"] = lambda: str(json_path)
    try:
        assert ns["_rl_load_translations"]() is True
        assert ns["config"].rtl is True
        assert ns["style"].default.reading_order == "wrtl"
    finally:
        ns["_rl_find_strings_json"] = old_finder
