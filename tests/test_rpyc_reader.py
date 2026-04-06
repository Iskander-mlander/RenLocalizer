import unittest

from src.core import rpyc_reader as rr


def test_fake_pycode_setstate_various_forms():
    states = [
        {"source": "print('hi')", "location": (1, 2), "mode": "exec", "py": 1},
        (None, "print('a')", (10, 20), "eval", 2),
        ({"source": "s1"}, {"location": (3, 4), "mode": "exec"}),
        ["x", "some source", (5, 6), "exec", 3],
    ]

    for st in states:
        pc = rr.FakePyCode()
        # Should not raise
        pc.__setstate__(st)
        # After setting state, attributes should exist and bytecode should be cleared
        assert hasattr(pc, "source")
        assert pc.bytecode is None


def test_fake_argument_and_parameter_info_setstate():
    ai = rr.FakeArgumentInfo()
    ai.__setstate__(({"arguments": [("a", 1)]},))
    assert isinstance(ai.arguments, list)

    pi = rr.FakeParameterInfo()
    pi.__setstate__(({"parameters": [("p", None)]},))
    assert isinstance(pi.parameters, list)


def test_renpy_unpickler_blocks_malicious_reduce(tmp_path):
    """RenpyUnpickler should reject payloads that try to execute globals like os.system."""
    import io
    import os
    import pickle

    class Evil:
        def __reduce__(self):
            return (os.system, ("echo SHOULD_NOT_RUN",))

    payload = pickle.dumps(Evil())

    with unittest.TestCase().assertRaises(pickle.UnpicklingError):
        rr.RenpyUnpickler(io.BytesIO(payload)).load()


def test_renpy_unpickler_allows_defaultdict():
    import collections
    import io
    import pickle

    payload = pickle.dumps(collections.defaultdict(list, {"a": [1, 2]}))
    result = rr.RenpyUnpickler(io.BytesIO(payload)).load()

    assert isinstance(result, collections.defaultdict)
    assert result.default_factory is list
    assert result["a"] == [1, 2]


def test_is_technical_string_allows_screen_context():
    extractor = rr.ASTTextExtractor()
    assert extractor._is_technical_string("Start", "screen:main_menu") is False


def test_default_extracts_strings_from_code():
    extractor = rr.ASTTextExtractor()
    extractor.current_file = "test.rpyc"

    node = rr.FakeDefault()
    node.linenumber = 12
    code = rr.FakePyCode()
    code.source = "_(\"Hello default\")"
    node.code = code

    extractor._process_node(node)

    match = next(entry for entry in extractor.extracted if entry.text == "Hello default")
    assert match.confidence >= 0.85
    assert match.confidence_band in {"confirmed", "probable"}


def test_screen_keyword_unquoted_text_is_extracted():
    extractor = rr.ASTTextExtractor()
    extractor.current_file = "test.rpyc"

    node = rr.FakeSLDisplayable()
    node.keyword = [("text", "Start")]
    node.location = ("screens.rpy", 7)

    extractor._process_screen_node(node, "screen:main_menu")

    match = next(entry for entry in extractor.extracted if entry.text == "Start")
    assert match.confidence >= 0.6


def test_tagged_ui_text_uses_visible_content():
    extractor = rr.ASTTextExtractor()
    extractor.current_file = "test.rpyc"

    extractor._add_text(
        "{color=#5175ea}*giggle*{/w}",
        21,
        "ui",
        context="displayable",
        node_type="SLDisplayable",
    )

    match = next(entry for entry in extractor.extracted if "*giggle*" in entry.text)
    assert match.confidence >= 0.58
    assert match.text_type == "ui"
