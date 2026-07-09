import os
import sys
import re
from pathlib import Path
from collections import Counter

# Add src to path
sys.path.append(os.getcwd())

from src.core.parser import RenPyParser
from src.core.deep_extraction import _shared_analyzer

def get_all_literal_strings(file_path: Path):
    """Extremely raw regex extraction for anything inside double or single quotes."""
    all_strings = []
    try:
        content = file_path.read_text(encoding="utf-8")
        import ast
        matches = re.finditer(r'"(.*?)"|\'(.*?)\'', content)
        for m in matches:
            text = m.group(0) # Get the FULL quoted string
            if text:
                try:
                    eval_text = ast.literal_eval(text)
                    if isinstance(eval_text, str):
                        all_strings.append(eval_text)
                except Exception:
                    # Fallback
                    raw = m.group(1) if m.group(1) is not None else m.group(2)
                    raw = raw.replace('\\"', '"').replace("\\'", "'")
                    all_strings.append(raw)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return all_strings

def is_potentially_translatable(text: str) -> bool:
    """Filter out garbage using our existing deep extraction logic plus extra safeguards."""
    if not text or len(text.strip()) < 2:
        return False
    
    # 1. Skip paths
    if "/" in text or "\\\\" in text or text.endswith(".png") or text.endswith(".ogg") or text.endswith(".wav"):
        return False
    
    # 2. Skip technical strings via our own analyzer
    if _shared_analyzer.is_technical_string(text):
        return False
    
    # 3. Skip pure code expressions (e.g. game.day == 5, x+y, config.something)
    if re.match(r'^[a-zA-Z_]\w*\s*[=<>+\-*/].*$', text):
        return False
        
    # 4. Require at least one letter
    if not any(c.isalpha() for c in text):
        return False
        
    # 5. Skip snake_case or camelCase single words that look like IDs
    if re.match(r'^[a-z]+_[a-z_]+$', text) or re.match(r'^[a-z]+[A-Z][a-zA-Z]*$', text):
        return False
        
    return True

def analyze_misses():
    parser = RenPyParser()
    rpyler_dir = Path("RPYler")
    
    if not rpyler_dir.exists():
        print("RPYler directory not found.")
        return

    rpy_files = list(rpyler_dir.rglob("*.rpy"))
    print(f"Found {len(rpy_files)} .rpy files in RPYler.")
    
    all_missed = Counter()
    total_parsed_count = 0
    total_literal_count = 0
    
    for file_path in rpy_files[:50]: # Limit to first 50 files for speed initially
        parsed_entries = parser.extract_text_entries(file_path)
        parsed_texts = {e['text'] for e in parsed_entries}
        total_parsed_count += len(parsed_texts)
        
        raw_strings = get_all_literal_strings(file_path)
        
        filtered_literals = {s for s in raw_strings if is_potentially_translatable(s)}
        total_literal_count += len(filtered_literals)
        
        # Missed are the ones we filtered and thought look like text, but the parser didn't catch
        missed = filtered_literals - parsed_texts
        
        for m in missed:
            all_missed[m] += 1

    print("\n--- ANALYSIS COMPLETE ---")
    print(f"Processed 50 files.")
    print(f"Parser captured {total_parsed_count} unique strings.")
    print(f"Found {total_literal_count} potentially translatable string literals.")
    print(f"Total missed strings: {len(all_missed)}")
    
    print("\nTop 100 missed strings by frequency:")
    for text, count in all_missed.most_common(100):
        print(f"[{count}x] {text}")

if __name__ == "__main__":
    analyze_misses()
