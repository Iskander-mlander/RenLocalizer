
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(os.getcwd())

from src.core.parser import RenPyParser

def debug_extraction():
    parser = RenPyParser()
    test_file = Path("tests/fp_test.rpy")
    if not test_file.exists():
        print("Test file not found")
        return

    entries = parser.extract_text_entries(test_file)
    print("--- DETAILED EXTRACTION RESULTS ---")
    for e in entries:
        t_type = e.get("text_type", "unknown")
        text = e.get("text", "")
        ctx = e.get("context_path", [])
        print(f"TYPE: {t_type:20} | TEXT: {text:30} | CTX: {ctx}")

if __name__ == "__main__":
    debug_extraction()
