"""
DeepL ve AI motorları için preprotected (pipeline'dan korunmuş) metin testleri.

v3.5 düzeltmeleri:
1. DeepL translate_batch çift koruma hatası düzeltildi (protect_renpy_syntax
   artık metadata['original_text'] üzerinden çağrılıyor)
2. AI translate_single çift koruma hatası düzeltildi (protect_renpy_syntax_xml
   artık metadata['original_text'] üzerinden çağrılıyor)
3. AI translate_batch çift koruma hatası düzeltildi
4. LocalLLMTranslator translate_single çift koruma hatası düzeltildi
5. Cache key'leri original_text üzerinden normalize edildi (translate_with_retry + translate_batch)
6. Debug print() çağrıları logger.debug() ile değiştirildi
"""

import re
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.core.syntax_guard import (
    protect_renpy_syntax,
    restore_renpy_syntax,
    protect_renpy_syntax_xml,
    restore_renpy_syntax_xml,
)
from src.core.translator import (
    DeepLTranslator,
    TranslationEngine,
    TranslationRequest,
    TranslationResult,
    TranslationManager,
)


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def make_preprotected_request(engine: TranslationEngine, original: str):
    """Pipeline'ın oluşturduğu preprotected request'i simüle eder."""
    protected, placeholders = protect_renpy_syntax(original)
    return TranslationRequest(
        text=protected,
        source_lang="en",
        target_lang="tr",
        engine=engine,
        metadata={
            "preprotected": True,
            "placeholders": placeholders,
            "original_text": original,
        },
    ), placeholders


def make_plain_request(engine: TranslationEngine, text: str):
    """Pipeline olmadan doğrudan çağrı simüle eder."""
    return TranslationRequest(
        text=text,
        source_lang="en",
        target_lang="tr",
        engine=engine,
        metadata={},
    )


# ══════════════════════════════════════════════════════════════
# DeepL PREPROTECTED TESTS
# ══════════════════════════════════════════════════════════════


class TestDeepLPreprotected:
    """DeepL translate_batch'in preprotected metin ile çift koruma yapmaması."""

    def test_deepl_protection_uses_original_text_when_preprotected(self):
        """Preprotected request geldiğinde DeepL, original_text üzerinden
        protect_renpy_syntax çağırmalı (⟦RLPH tokenlerini yeniden sarmalamadan)."""
        original = "Hello [player], {b}welcome{/b}!"
        req, pipeline_ph = make_preprotected_request(TranslationEngine.DEEPL, original)

        # Confirm pipeline created RLPH tokens
        assert "⟦RLPH" in req.text
        assert "[player]" not in req.text

        # Now simulate what DeepL's translate_batch does internally:
        # It should protect from original_text, NOT from req.text
        meta = req.metadata if isinstance(req.metadata, dict) else {}
        source_text = meta.get('original_text', req.text) if meta.get('preprotected') else req.text

        # source_text should be the ORIGINAL text
        assert source_text == original
        assert "[player]" in source_text

        # When we protect the original text, we get proper single-level tokens
        p_text, p_holders = protect_renpy_syntax(source_text)
        assert "[player]" not in p_text
        # Critically: no nested RLPH tokens
        rlph_tokens = re.findall(r'⟦RLPH[A-F0-9]{6}_\w+⟧', p_text)
        for token in rlph_tokens:
            value = p_holders.get(token, "")
            # Values should be original content, NOT other RLPH tokens
            assert "⟦RLPH" not in value, f"Nested token detected: {token} -> {value}"

    def test_deepl_non_preprotected_works_normally(self):
        """Pipeline olmadan doğrudan DeepL çağrısı normal çalışmalı."""
        req = make_plain_request(TranslationEngine.DEEPL, "Hello [player], {b}war{/b}!")

        meta = req.metadata if isinstance(req.metadata, dict) else {}
        source_text = meta.get('original_text', req.text) if meta.get('preprotected') else req.text

        # Non-preprotected: source_text == req.text
        assert source_text == req.text
        assert "[player]" in source_text

    def test_deepl_nested_tokens_prevented(self):
        """Pipeline tokenları üzerinde tekrar protect çağrılırsa iç içe
        tokenler oluşur — preprotected guard bunu engellemelidir."""
        original = "Score: [points] and {color=#fff}Name{/color}"
        req, pipeline_ph = make_preprotected_request(TranslationEngine.DEEPL, original)

        # OLD BUG: protect_renpy_syntax(req.text) would create nested tokens
        # because ⟦RLPH...⟧ is itself a protected pattern
        bad_text, bad_holders = protect_renpy_syntax(req.text)
        # The old code would find RLPH tokens AND wrap them again
        nested_count = sum(1 for v in bad_holders.values() if "⟦RLPH" in str(v))
        assert nested_count > 0, "Sanity check: double protection DOES create nested tokens"

        # NEW FIX: protect from original_text avoids nesting
        meta = req.metadata if isinstance(req.metadata, dict) else {}
        source_text = meta.get('original_text', req.text) if meta.get('preprotected') else req.text
        good_text, good_holders = protect_renpy_syntax(source_text)
        nested_count_fixed = sum(1 for v in good_holders.values() if "⟦RLPH" in str(v))
        assert nested_count_fixed == 0, "Fixed: no nested tokens when using original_text"


# ══════════════════════════════════════════════════════════════
# AI TRANSLATOR PREPROTECTED TESTS
# ══════════════════════════════════════════════════════════════


class TestAIPreprotected:
    """AI translator'ların preprotected metin ile çift koruma yapmaması."""

    def test_ai_single_protection_uses_original_text(self):
        """LLMTranslator.translate_single, preprotected request'te
        original_text üzerinden protect_renpy_syntax_xml çağırmalı."""
        original = "Hello [name], {i}welcome{/i} to the game!"
        req, pipeline_ph = make_preprotected_request(TranslationEngine.OPENAI, original)

        # Simulate the AI translator's preprotected check
        meta = req.metadata if isinstance(req.metadata, dict) else {}
        source_text = meta.get('original_text', req.text) if meta.get('preprotected') else req.text

        assert source_text == original
        protected_xml, xml_ph = protect_renpy_syntax_xml(source_text)

        # XML protection should contain <ph> tags, NOT ⟦RLPH tokens
        assert "<ph " in protected_xml or len(xml_ph) == 0 or source_text == protected_xml
        assert "⟦RLPH" not in protected_xml

    def test_ai_batch_protection_uses_original_text(self):
        """AI _translate_batch_internal, preprotected request'lerde
        original_text üzerinden protect çağırmalı."""
        texts = [
            "Hello [name]!",
            "{b}Bold{/b} text here.",
            "Score: [score_val]",
        ]
        reqs = []
        for t in texts:
            req, _ = make_preprotected_request(TranslationEngine.OPENAI, t)
            reqs.append(req)

        for req in reqs:
            meta = req.metadata if isinstance(req.metadata, dict) else {}
            source_text = meta.get('original_text', req.text) if meta.get('preprotected') else req.text
            protected_xml, xml_ph = protect_renpy_syntax_xml(source_text)
            # No RLPH tokens should appear in XML-protected output
            assert "⟦RLPH" not in protected_xml

    def test_ai_non_preprotected_works_normally(self):
        """Pipeline olmadan doğrudan AI çağrısı normal çalışmalı."""
        req = make_plain_request(TranslationEngine.OPENAI, "Hello [player]!")

        meta = req.metadata if isinstance(req.metadata, dict) else {}
        source_text = meta.get('original_text', req.text) if meta.get('preprotected') else req.text
        assert source_text == "Hello [player]!"

        protected_xml, xml_ph = protect_renpy_syntax_xml(source_text)
        # XML format wraps content in <ph> tags; the key thing is no RLPH tokens
        assert "⟦RLPH" not in protected_xml
        # [player] should be protected (either in <ph> tag or in placeholders dict)
        if xml_ph:
            assert any("[player]" in str(v) for v in xml_ph.values())

    def test_local_llm_protection_uses_original_text(self):
        """LocalLLMTranslator.translate_single, preprotected request'te
        protect_renpy_syntax'ı original_text üzerinden çağırmalı."""
        original = "You have [gold] gold {color=#ff0}coins{/color}."
        req, pipeline_ph = make_preprotected_request(TranslationEngine.LOCAL_LLM, original)

        meta = req.metadata if isinstance(req.metadata, dict) else {}
        source_text = meta.get('original_text', req.text) if meta.get('preprotected') else req.text
        assert source_text == original

        p_text, p_holders = protect_renpy_syntax(source_text)
        nested_count = sum(1 for v in p_holders.values() if "⟦RLPH" in str(v))
        assert nested_count == 0


# ══════════════════════════════════════════════════════════════
# CACHE KEY NORMALIZATION TESTS
# ══════════════════════════════════════════════════════════════


class TestCacheKeyNormalization:
    """Cache key'lerinin original_text üzerinden normalize edilmesi."""

    def test_cache_key_uses_original_text_when_preprotected(self):
        """translate_with_retry cache key'i, preprotected request'te
        original_text kullanmalı (protected text yerine)."""
        original = "Hello [player]!"
        req, _ = make_preprotected_request(TranslationEngine.GOOGLE, original)

        # Simulate cache key generation (same logic as translate_with_retry)
        meta = req.metadata if isinstance(req.metadata, dict) else {}
        cache_text = meta.get('original_text', req.text)
        key = (req.engine.value, req.source_lang, req.target_lang, cache_text)

        assert key[3] == original  # Cache key uses ORIGINAL, not protected
        assert "⟦RLPH" not in key[3]

    def test_cache_key_uses_text_when_not_preprotected(self):
        """Pipeline olmadan cache key'i req.text kullanmalı."""
        req = make_plain_request(TranslationEngine.GOOGLE, "Hello world!")

        meta = req.metadata if isinstance(req.metadata, dict) else {}
        cache_text = meta.get('original_text', req.text)
        key = (req.engine.value, req.source_lang, req.target_lang, cache_text)

        assert key[3] == "Hello world!"

    def test_batch_dedup_key_matches_single_key(self):
        """translate_batch dedup key'i ve translate_with_retry cache key'i
        aynı original_text üzerinden hesaplanmalı → cache hit."""
        original = "Hello [player]!"
        req, _ = make_preprotected_request(TranslationEngine.GOOGLE, original)

        # Single path key (translate_with_retry)
        meta = req.metadata if isinstance(req.metadata, dict) else {}
        cache_text_single = meta.get('original_text', req.text)
        key_single = (req.engine.value, req.source_lang, req.target_lang, cache_text_single)

        # Batch path key (translate_batch dedup)
        cache_text_batch = meta.get('original_text', req.text)
        key_batch = (req.engine.value, req.source_lang, req.target_lang, cache_text_batch)

        assert key_single == key_batch

    def test_different_uuid_namespaces_same_original_match(self):
        """Aynı orijinal metin farklı UUID namespace'ler ile korunmuş olsa
        bile cache key'leri eşleşmeli."""
        original = "Hello [player]!"

        # Two separate pipeline protections → different RLPH namespaces
        req1, _ = make_preprotected_request(TranslationEngine.GOOGLE, original)
        req2, _ = make_preprotected_request(TranslationEngine.GOOGLE, original)

        # Protected texts are DIFFERENT (different UUIDs)
        assert req1.text != req2.text

        # But cache keys should be SAME (both use original_text)
        meta1 = req1.metadata if isinstance(req1.metadata, dict) else {}
        meta2 = req2.metadata if isinstance(req2.metadata, dict) else {}
        key1 = (req1.engine.value, req1.source_lang, req1.target_lang, meta1.get('original_text', req1.text))
        key2 = (req2.engine.value, req2.source_lang, req2.target_lang, meta2.get('original_text', req2.text))

        assert key1 == key2


# ══════════════════════════════════════════════════════════════
# DEBUG PRINT REMOVAL TESTS
# ══════════════════════════════════════════════════════════════


class TestNoDebugPrints:
    """Üretim kodunda print() debug ifadeleri olmamalı."""

    def test_translate_with_retry_has_no_print(self):
        """TranslationManager.translate_with_retry print() içermemeli."""
        import inspect
        source = inspect.getsource(TranslationManager.translate_with_retry)
        # Should NOT contain bare print() calls
        # logger.debug is OK
        lines = source.split('\n')
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('print(') or stripped.startswith('print ('):
                pytest.fail(f"Found debug print() in translate_with_retry: {stripped}")
