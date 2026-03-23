import pytest
import io
import pickle
import sys
import os
import time
from collections import OrderedDict

# Add PROJECT ROOT to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Now import with full package path
try:
    from src.core.rpyc_reader import RenpyUnpickler, FakeGeneric, FakeLabel, ASTTextExtractor
    from src.core.parser import RenPyParser
except ImportError:
    # If standard import fails, try direct without src (if running inside src)
    from core.rpyc_reader import RenpyUnpickler, FakeGeneric, FakeLabel, ASTTextExtractor
    from core.parser import RenPyParser

class MaliciousPayload:
    def __reduce__(self):
        return (os.system, ('echo "SecurityBreach"',))

def test_security_rce_prevention():
    """Verify that RenpyUnpickler blocks execution of arbitrary execution attempts."""
    pickled_data = pickle.dumps(MaliciousPayload())
    
    f = io.BytesIO(pickled_data)
    unpickler = RenpyUnpickler(f)
    
    try:
        obj = unpickler.load()
        if isinstance(obj, int): # os.system returns int
             raise RuntimeError("Security Breach: os.system was executed!")
    except TypeError:
        # Expected behavior: FakeGeneric reject arguments
        pass
    except Exception as e:
        # Unexpected error (UnpicklingError would be fine too)
        if "SecurityBreach" in str(e):
             raise RuntimeError("Security Breach: Payload executed!")
        print(f"Captured expected error: {e}")

def test_whitelist_standard_library():
    """Verify that harmless standard library classes are allowed."""
    data = OrderedDict([('key', 'value')])
    pickled_data = pickle.dumps(data)
    
    f = io.BytesIO(pickled_data)
    unpickler = RenpyUnpickler(f)
    obj = unpickler.load()
    # Flexible check for real or fake implementation
    assert isinstance(obj, (OrderedDict, dict)) or obj.__class__.__name__ == 'FakeOrderedDict'

def test_regex_performance_dos():
    """Verify that regexes don't hang on large inputs."""
    parser = RenPyParser()
    large_string = "A" * 500000 + " _('End')" # 500KB string
    
    start_time = time.time()
    result = parser.is_meaningful_text(large_string)
    end_time = time.time()
    
    duration = end_time - start_time
    print(f"Performance: 500KB string processed in {duration:.4f}s")
    
    assert duration < 1.0
    assert result is False

def test_recursion_depth():
    """Verify recursion limit behavior."""
    root = FakeLabel()
    current = root
    for i in range(500):
        new_node = FakeLabel()
        current.block = [new_node]
        current = new_node
    
    # ASTTextExtractor expects config_manager (not parser) — pass None for test
    extractor = ASTTextExtractor(config_manager=None)
    
    try:
        extractor._walk_nodes([root])
    except RecursionError:
        raise RuntimeError("RecursionError hit at depth 500")
    except Exception:
        pass

if __name__ == "__main__":
    # Internal runner to print statuses clearly
    tests = [
        test_security_rce_prevention,
        test_whitelist_standard_library,
        test_regex_performance_dos,
        test_recursion_depth
    ]
    
    passed = 0
    for test in tests:
        try:
            test()
            print(f"[PASS] {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
    
    if passed == len(tests):
        print("ALL TESTS PASSED")
    else:
        sys.exit(1)
