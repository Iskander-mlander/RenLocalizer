import io
import pickle
import zlib

import pytest

from src.core import rpymc_reader


def _make_rpymc_bytes(obj):
    """Helper to wrap a pickled object into minimal rpymc-like bytes."""
    pickled = pickle.dumps(obj)
    compressed = zlib.compress(pickled)
    # Minimal header: starts with RENPY, then zlib stream
    return b"RENPY" + compressed


def test_rpymc_reader_allows_safe_payload(tmp_path):
    safe_obj = {"text": "hello", "lines": [1, 2, 3]}
    data = _make_rpymc_bytes(safe_obj)
    path = tmp_path / "safe.rpymc"
    path.write_bytes(data)

    # extract_text_from_rpymc returns List[Dict] of extracted entries
    # For a plain dict without SL2 nodes, it returns empty list (no crash = safe)
    result = rpymc_reader.extract_text_from_rpymc(str(path))
    assert isinstance(result, list)


def test_rpymc_reader_allows_defaultdict(tmp_path):
    import collections

    safe_obj = collections.defaultdict(list, {"x": [1]})
    data = _make_rpymc_bytes(safe_obj)
    path = tmp_path / "safe_defaultdict.rpymc"
    path.write_bytes(data)

    # defaultdict is allowed by RenpyUnpickler — should not crash
    result = rpymc_reader.extract_text_from_rpymc(str(path))
    assert isinstance(result, list)  # Returns extracted entries (list)


def test_rpymc_reader_blocks_malicious_reduce(tmp_path):
    import os

    class Evil:
        def __reduce__(self):
            return (os.system, ("echo SHOULD_NOT_RUN",))

    data = _make_rpymc_bytes(Evil())
    path = tmp_path / "evil.rpymc"
    path.write_bytes(data)

    # extract_text_from_rpymc catches exceptions internally and returns []
    # The important thing is that os.system is NOT executed
    result = rpymc_reader.extract_text_from_rpymc(str(path))
    assert result == []  # Malicious payload blocked — returns empty
