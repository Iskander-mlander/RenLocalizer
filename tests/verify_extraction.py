
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(os.getcwd())

from src.core.parser import RenPyParser

def verify_extraction():
    parser = RenPyParser()
    sample_file = Path("tests/sample_edge_cases.rpy")
    
    print(f"--- Extracting from {sample_file} ---")
    entries = parser.extract_text_entries(sample_file)
    
    extracted_texts = [e['text'] for e in entries]
    
    print("\n[EXTRACTED TEXTS]")
    for t in extracted_texts:
        print(f"- {repr(t)}")
        
    targets = [
        "Unlockable Gallery Item",
        "This is a custom message",
        "Rhiannon",
        "Unwrapped String",
        "Wrapped String",
        "Hover Me",
        "I am a tooltip"
    ]
    
    print("\n[VERIFICATION]")
    for target in targets:
        status = "FOUND" if target in extracted_texts else "MISSING"
        print(f"{target:30} : {status}")

if __name__ == "__main__":
    verify_extraction()
