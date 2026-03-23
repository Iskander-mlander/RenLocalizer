import asyncio

from src.core.translator import (
    TranslationEngine,
    TranslationManager,
    TranslationRequest,
    TranslationResult,
)


def test_translate_with_retry_projects_cross_engine_cache_hits_to_requested_engine() -> None:
    manager = TranslationManager()
    manager._cache[("libretranslate", "auto", "tr", "About")] = TranslationResult(
        original_text="About",
        translated_text="Hakkinda",
        source_lang="auto",
        target_lang="tr",
        engine=TranslationEngine.LIBRETRANSLATE,
        success=True,
    )

    request = TranslationRequest(
        text="About",
        source_lang="auto",
        target_lang="tr",
        engine=TranslationEngine.YANDEX,
        metadata={"original_text": "About"},
    )

    result = asyncio.run(manager.translate_with_retry(request))

    assert result.success is True
    assert result.engine == TranslationEngine.YANDEX
    assert result.metadata["cache_hit_type"] == "cross_engine"
    assert result.metadata["cache_source_engine"] == "libretranslate"
    assert ("yandex", "auto", "tr", "About") in manager._cache
    assert manager._cache[("yandex", "auto", "tr", "About")].engine == TranslationEngine.YANDEX


def test_translate_batch_projects_source_lang_fallback_cache_hits() -> None:
    manager = TranslationManager()
    manager._cache[("yandex", "en", "tr", "Save")] = TranslationResult(
        original_text="Save",
        translated_text="Kaydet",
        source_lang="en",
        target_lang="tr",
        engine=TranslationEngine.YANDEX,
        success=True,
    )

    request = TranslationRequest(
        text="Save",
        source_lang="auto",
        target_lang="tr",
        engine=TranslationEngine.YANDEX,
        metadata={"original_text": "Save"},
    )

    result = asyncio.run(manager.translate_batch([request]))[0]

    assert result.success is True
    assert result.engine == TranslationEngine.YANDEX
    assert result.source_lang == "auto"
    assert result.metadata["cache_hit_type"] == "source_lang_fallback"
    assert result.metadata["cache_source_lang"] == "en"
    assert ("yandex", "auto", "tr", "Save") in manager._cache
