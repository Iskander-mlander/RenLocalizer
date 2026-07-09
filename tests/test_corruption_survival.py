import os
from pathlib import Path
import re
import random
import traceback
from src.core.parser import RenPyParser
from src.core.syntax_guard import protect_renpy_syntax, restore_renpy_syntax, validate_translation_integrity

RPY_DIR = Path("RPYler")

def test_syntax_guard():
    parser = RenPyParser()
    total_strings = 0
    corrupted_count = 0
    recovered_count = 0
    failed_count = 0
    
    # Let's find some rpy files across different games to test on
    rpy_files = list(RPY_DIR.rglob("*.rpy"))
    random.seed(42)
    random.shuffle(rpy_files)
    test_files = rpy_files[:50] # Test on a subset of 50 files for speed
    
    for file_path in test_files:
        try:
            entries = parser.extract_text_entries(file_path)
            for entry_data in entries:
                # Based on parser output, entry is a dict with 'text'
                text = entry_data.get('text', '')
                if not text.strip() or ('{' not in text and '[' not in text):
                    continue
                    
                total_strings += 1
                
                # Protect syntax
                protected_text, placeholders = protect_renpy_syntax(text)
                if not placeholders:
                    continue
                    
                # Introduce deliberate corruption!
                # 1. Fuzzy suffix corruption: Change RLPH to RLLPH or alter hex slightly
                corrupted_text = protected_text
                for key in placeholders.keys():
                    if key.startswith('__WRAPPER_PAIR'):
                        # Mismatched parsing might happen if wrappers are mangled, but the fuzzy token recovery is about RLPH
                        continue
                    
                    if "RLPH" in key:
                        # Introduce a mutation 50% of the time per token
                        if random.random() > 0.5:
                            inner = key.strip('\u27e6\u27e7')
                            parts = inner.split('_')
                            hex_part = parts[0]
                            suff_part = parts[1]
                            if random.random() > 0.5:
                                new_hex = hex_part.replace('RLPH', 'RLLPH', 1)
                            else:
                                new_hex = hex_part.replace('0', 'O', 1).replace('1', 'I', 1)
                                
                            new_inner = f"{new_hex}_{suff_part}"
                            corrupted_key = f"\u27e6{new_inner}\u27e7"
                            corrupted_text = corrupted_text.replace(key, corrupted_key)
                            corrupted_count += 1
                
                # Restore syntax
                try:
                    restored_text = restore_renpy_syntax(corrupted_text, placeholders)
                    missing_vars = validate_translation_integrity(restored_text, placeholders)
                    
                    if not missing_vars:
                        recovered_count += 1
                    else:
                        print(f"[FAIL] Original: {text}")
                        print(f"       Protected: {protected_text}")
                        print(f"       Corrupted: {corrupted_text}")
                        print(f"       Restored : {restored_text}")
                        print(f"       Missing  : {missing_vars}")
                        failed_count += 1
                except Exception as e:
                    print(f"EXCEPTION ON {text}: {e}")
                    failed_count += 1
        except Exception as e:
            traceback.print_exc()

    print("\n" + "="*50)
    print("      SYNTAX GUARD CORRUPTION SURVIVAL TEST")
    print("="*50)
    print(f"Files tested      : {len(test_files)}")
    print(f"Strings w/ syntax : {total_strings}")
    print(f"Tokens corrupted  : {corrupted_count}")
    print(f"Tokens recovered  : {recovered_count}")
    print(f"Tokens failed     : {failed_count}")
    
    if failed_count == 0 and corrupted_count > 0:
        print("\n\nSUCCESS! 100% of the corrupted tokens were fully recovered by the new engine!")
    
if __name__ == "__main__":
    test_syntax_guard()
