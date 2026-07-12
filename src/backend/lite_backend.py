# -*- coding: utf-8 -*-
"""
LiteBackend - RenLocalizer Lite için Slim Python-QML Köprüsü
=============================================================

Sadece "Oyun Seç → Google ile Çevir" akışına odaklanmış,
gereksiz her bağımlılıktan arındırılmış minimalist backend.

Ana sürümün AppBackend'ine hiç dokunmaz. Additive-first yaklaşım.
"""

import logging
import os
import sys
import threading
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, pyqtProperty, QUrl
from PyQt6.QtGui import QDesktopServices

from src.utils.config import ConfigManager
from src.version import VERSION
from src.core.translator import (
    TranslationManager,
    TranslationEngine,
    GoogleTranslator,
)
from src.core.ai_translator import (
    OpenAITranslator,
    DeepSeekTranslator,
    LocalLLMTranslator,
)
from src.core.proxy_manager import ProxyManager
from src.core.translation_pipeline import TranslationPipeline, PipelineWorker
from src.core.tl_parser import TLParser, get_translation_stats


def _normalize_path(raw: str) -> str:
    """QML file:// URI'sini veya ham yolu OS path'e dönüştür."""
    if not raw:
        return raw
    clean_raw = raw.strip('"')
    # Eğer girdi düz bir OS yolu ise (URL şeması içermiyorsa), doğrudan temizle ve dön
    if "://" not in clean_raw:
        return os.path.normpath(clean_raw)
    local = QUrl(clean_raw).toLocalFile()
    if local:
        return os.path.normpath(local)
    try:
        parsed = urllib.parse.urlparse(clean_raw)
        path_str = parsed.path
        if sys.platform == "win32" and path_str.startswith("/"):
            path_str = path_str[1:]
        return os.path.normpath(urllib.parse.unquote(path_str))
    except Exception:
        return os.path.normpath(urllib.parse.unquote(clean_raw))


class LiteBackend(QObject):
    """
    RenLocalizer Lite — Python-QML köprüsü.

    Google Translate ve AI motorları (OpenAI, DeepSeek, LocalLLM) ile çeviri akışını yönetir.
    Glossary, Tools, Font özellikleri bu sürümde yoktur.
    """

    # ── Signals (QML tarafından dinlenir) ────────────────────────────────
    logMessage         = pyqtSignal(str, str, arguments=["level", "message"])
    progressChanged    = pyqtSignal(int, int, str, arguments=["current", "total", "text"])
    stageChanged       = pyqtSignal(str, str, arguments=["stage", "displayName"])
    translationStarted = pyqtSignal()
    translationFinished = pyqtSignal(bool, str, arguments=["success", "message"])
    statsReady         = pyqtSignal(int, int, int, arguments=["total", "translated", "untranslated"])
    completionSummary  = pyqtSignal(
        str, str, str, str, int,
        arguments=["title", "message", "outputPath", "diagnosticPath", "reviewNoteCount"],
    )
    warningMessage     = pyqtSignal(str, str, arguments=["title", "message"])
    updateAvailable    = pyqtSignal(str, str, str, arguments=["currentVersion", "latestVersion", "releaseUrl"])
    updateCheckFinished = pyqtSignal(bool, str, arguments=["hasUpdate", "message"])
    # ── Settings Signals (QML Two-way bindings) ────────────────────────
    maxThreadsChanged       = pyqtSignal()
    requestDelayChanged     = pyqtSignal()
    maxBatchSizeChanged     = pyqtSignal()
    multiEndpointChanged    = pyqtSignal()
    lingvaFallbackChanged   = pyqtSignal()
    aggressiveRetryChanged  = pyqtSignal()
    useCacheChanged         = pyqtSignal()
    uiTriggerChanged        = pyqtSignal()
    languageChanged         = pyqtSignal(str)
    themeChanged            = pyqtSignal(str)
    enableRpycReaderChanged  = pyqtSignal()
    enableDeepScanChanged    = pyqtSignal()
    selectedEngineChanged    = pyqtSignal(str)
    openaiApiKeyChanged      = pyqtSignal()
    openaiModelChanged       = pyqtSignal()
    openaiBaseUrlChanged     = pyqtSignal()
    localLlmUrlChanged       = pyqtSignal()
    localLlmModelChanged     = pyqtSignal()
    libretranslateUrlChanged = pyqtSignal()
    libretranslateApiKeyChanged = pyqtSignal()
    customEndpointUrlChanged = pyqtSignal()
    customEndpointApiKeyChanged = pyqtSignal()
    aiTemperatureChanged     = pyqtSignal()
    aiTimeoutChanged         = pyqtSignal()
    aiMaxTokensChanged       = pyqtSignal()
    aiBatchSizeChanged       = pyqtSignal()
    aiRetryCountChanged      = pyqtSignal()
    aiConcurrencyChanged     = pyqtSignal()
    aiRequestDelayChanged    = pyqtSignal()
    aiCustomSystemPromptChanged = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self._version = VERSION

        # ── ConfigManager ────────────────────────────────────────────────
        self.config = ConfigManager()

        # ── Migration to 2.8.6-LITE ──────────────────────────────────────
        # Reset previously forced-false settings to True once.
        migration_marker = Path(self.config.data_dir) / ".migrated_286"
        if not migration_marker.exists():
            self.config.translation_settings.enable_rpyc_reader = True
            self.config.translation_settings.enable_deep_scan = True
            try:
                self.config.save_config()
                migration_marker.touch()
            except Exception as e:
                self.logger.warning(f"Could not write migration marker: {e}")

        # Lite sürümde motor her zaman Google; config'e yazılmıyor (runtime override)
        self.config.translation_settings.selected_engine = "google"
        # Lite'ta gerekmeyen ağır özellikleri kapat (hız + bellek tasarrufu)
        self.config.translation_settings.enable_deep_extraction = False
        self.config.translation_settings.enable_unrpyc_decompile = False
        # ── State ────────────────────────────────────────────────────────
        self._project_path: str = self.config.app_settings.last_input_directory or ""
        self._target_language: str = self.config.translation_settings.target_language or "turkish"
        self._is_translating: bool = False
        self._ui_trigger: bool = False
        # TL retranslation mode (Ren'Py SDK-generated tl/ directory)
        self._tl_mode: bool = False
        self._tl_source_path: str = ""

        # ── Selected engine (default: Google unless config says otherwise) ─
        cfg_engine = self.config.translation_settings.selected_engine or "google"
        self._selected_engine: TranslationEngine = self._engine_from_str(cfg_engine)
        # Lite always forces Google engine back to google; AI engines are allowed
        if self._selected_engine not in (
            TranslationEngine.GOOGLE, TranslationEngine.OPENAI,
            TranslationEngine.LOCAL_LLM, TranslationEngine.LIBRETRANSLATE,
            TranslationEngine.CUSTOM,
        ):
            self._selected_engine = TranslationEngine.GOOGLE

        # ── Pipeline ─────────────────────────────────────────────────────
        self.pipeline: Optional[TranslationPipeline] = None
        self.pipeline_worker: Optional[PipelineWorker] = None

        # ── Translation Infrastructure ───────────────────────────────────
        self.proxy_manager = ProxyManager()
        # Lite'ta proxy devre dışı; config'den proxy_settings alsa bile override.
        self.proxy_manager.configure_from_settings(self.config.proxy_settings)

        self.translation_manager = TranslationManager(self.proxy_manager, self.config)

        # Google translator'ı her zaman hazırla (fallback)
        threading.Thread(target=self._setup_google_translator, daemon=True).start()
        # Seçili motora göre diğer translator'ları kur
        if self._selected_engine not in (TranslationEngine.GOOGLE,):
            if self._selected_engine in (TranslationEngine.OPENAI, TranslationEngine.LOCAL_LLM):
                threading.Thread(
                    target=self._setup_ai_translator,
                    args=(self._selected_engine,),
                    daemon=True,
                ).start()
            elif self._selected_engine == TranslationEngine.LIBRETRANSLATE:
                threading.Thread(target=self._setup_libretranslate, daemon=True).start()
            elif self._selected_engine == TranslationEngine.CUSTOM:
                threading.Thread(target=self._setup_custom_endpoint, daemon=True).start()

    # ── Private setup ────────────────────────────────────────────────────

    def _setup_google_translator(self) -> None:
        """Google Translate motorunu kurar."""
        try:
            google = GoogleTranslator(
                proxy_manager=self.proxy_manager,
                config_manager=self.config,
            )
            self.translation_manager.add_translator(TranslationEngine.GOOGLE, google)
            self.logger.info("[LiteBackend] Google Translate hazır.")
        except Exception as exc:
            self.logger.error("[LiteBackend] Google Translate kurulamadı: %s", exc)

    def _setup_libretranslate(self) -> None:
        """LibreTranslate motorunu kurar (kullanıcı tanımlı URL veya localhost:5000)."""
        try:
            from src.core.translator import LibreTranslateTranslator
            base_url = getattr(self.config.translation_settings, 'libretranslate_url', 'http://localhost:5000')
            api_key = getattr(self.config.translation_settings, 'libretranslate_api_key', '')
            lt = LibreTranslateTranslator(
                base_url=base_url,
                api_key=api_key,
                proxy_manager=self.proxy_manager,
                config_manager=self.config,
            )
            self.translation_manager.add_translator(TranslationEngine.LIBRETRANSLATE, lt)
            self.logger.info(f"[LiteBackend] LibreTranslate hazır: {base_url}")
        except Exception as exc:
            self.logger.error("[LiteBackend] LibreTranslate kurulamadı: %s", exc)

    def _setup_custom_endpoint(self) -> None:
        """Custom HTTP endpoint translator — herhangi bir çeviri API'sine uyumlu."""
        try:
            from src.core.translator import LibreTranslateTranslator
            base_url = getattr(self.config.translation_settings, 'custom_endpoint_url', '')
            if not base_url:
                self.logger.warning("[LiteBackend] Custom endpoint URL boş, Google fallback kullanılacak.")
                return
            api_key = getattr(self.config.translation_settings, 'custom_endpoint_api_key', '')
            ct = LibreTranslateTranslator(
                base_url=base_url,
                api_key=api_key,
                proxy_manager=self.proxy_manager,
                config_manager=self.config,
            )
            self.translation_manager.add_translator(TranslationEngine.CUSTOM, ct)
            self.logger.info(f"[LiteBackend] Custom endpoint hazır: {base_url}")
        except Exception as exc:
            self.logger.error("[LiteBackend] Custom endpoint kurulamadı: %s", exc)

    @staticmethod
    def _engine_from_str(engine_str: str) -> TranslationEngine:
        """Safely converts a string engine name to TranslationEngine enum."""
        mapping = {
            "google": TranslationEngine.GOOGLE,
            "openai": TranslationEngine.OPENAI,
            "local_llm": TranslationEngine.LOCAL_LLM,
            "deepseek": TranslationEngine.OPENAI,  # DeepSeek routed via OPENAI enum
            "libretranslate": TranslationEngine.LIBRETRANSLATE,
            "custom": TranslationEngine.CUSTOM,
        }
        return mapping.get(engine_str.lower(), TranslationEngine.GOOGLE)

    def _setup_ai_translator(self, engine: TranslationEngine) -> None:
        """Builds and registers the selected AI translator in the translation manager."""
        try:
            api_key = self.config.api_keys.openai_api_key or ""
            if engine == TranslationEngine.OPENAI:
                # Check if this is DeepSeek (openai_base_url points to deepseek)
                base_url = getattr(self.config.translation_settings, "openai_base_url", "") or ""
                if "deepseek" in base_url.lower():
                    translator = DeepSeekTranslator(
                        api_key=api_key,
                        proxy_manager=self.proxy_manager,
                        config_manager=self.config,
                    )
                    self.logger.info("[LiteBackend] DeepSeek translator hazır.")
                else:
                    translator = OpenAITranslator(
                        api_key=api_key,
                        proxy_manager=self.proxy_manager,
                        config_manager=self.config,
                    )
                    self.logger.info("[LiteBackend] OpenAI translator hazır.")
            elif engine == TranslationEngine.LOCAL_LLM:
                translator = LocalLLMTranslator(
                    proxy_manager=self.proxy_manager,
                    config_manager=self.config,
                )
                self.logger.info("[LiteBackend] Local LLM translator hazır.")
            else:
                return
            self.translation_manager.add_translator(engine, translator)
        except ImportError as exc:
            self.logger.error("[LiteBackend] AI paket eksik: %s", exc)
            self.logMessage.emit("error", str(exc))
        except Exception as exc:
            self.logger.error("[LiteBackend] AI translator kurulamadı: %s", exc)

    # ── pyqtProperty ─────────────────────────────────────────────────────

    @pyqtProperty(str, constant=True)
    def version(self) -> str:
        return self._version
    @pyqtProperty(bool, notify=translationStarted)
    def isTranslating(self) -> bool:
        return self._is_translating

    @pyqtProperty(bool, notify=uiTriggerChanged)
    def uiTrigger(self) -> bool:
        return self._ui_trigger
    # ── Settings Properties (Two-way binding support) ──────────────────
    @pyqtProperty(int, notify=maxThreadsChanged)
    def maxConcurrentThreads(self) -> int:
        return self.config.translation_settings.max_concurrent_threads

    @maxConcurrentThreads.setter
    def maxConcurrentThreads(self, val: int) -> None:
        self.config.translation_settings.max_concurrent_threads = max(1, int(val))
        self.maxThreadsChanged.emit()

    @pyqtProperty(float, notify=requestDelayChanged)
    def requestDelay(self) -> float:
        return self.config.translation_settings.request_delay

    @requestDelay.setter
    def requestDelay(self, val: float) -> None:
        self.config.translation_settings.request_delay = max(0.0, float(val))
        self.requestDelayChanged.emit()

    @pyqtProperty(int, notify=maxBatchSizeChanged)
    def maxBatchSize(self) -> int:
        return self.config.translation_settings.max_batch_size

    @maxBatchSize.setter
    def maxBatchSize(self, val: int) -> None:
        self.config.translation_settings.max_batch_size = max(1, int(val))
        self.maxBatchSizeChanged.emit()

    @pyqtProperty(bool, notify=multiEndpointChanged)
    def useMultiEndpoint(self) -> bool:
        return self.config.translation_settings.use_multi_endpoint

    @useMultiEndpoint.setter
    def useMultiEndpoint(self, val: bool) -> None:
        self.config.translation_settings.use_multi_endpoint = bool(val)
        self.multiEndpointChanged.emit()

    @pyqtProperty(bool, notify=lingvaFallbackChanged)
    def enableLingvaFallback(self) -> bool:
        return self.config.translation_settings.enable_lingva_fallback

    @enableLingvaFallback.setter
    def enableLingvaFallback(self, val: bool) -> None:
        self.config.translation_settings.enable_lingva_fallback = bool(val)
        self.lingvaFallbackChanged.emit()

    @pyqtProperty(bool, notify=aggressiveRetryChanged)
    def aggressiveRetry(self) -> bool:
        return self.config.translation_settings.aggressive_retry_translation

    @aggressiveRetry.setter
    def aggressiveRetry(self, val: bool) -> None:
        self.config.translation_settings.aggressive_retry_translation = bool(val)
        self.aggressiveRetryChanged.emit()

    @pyqtProperty(bool, notify=useCacheChanged)
    def useCache(self) -> bool:
        return self.config.translation_settings.use_cache

    @useCache.setter
    def useCache(self, val: bool) -> None:
        self.config.translation_settings.use_cache = bool(val)
        self.translation_manager.use_cache = bool(val)
        self.useCacheChanged.emit()

    @pyqtProperty(bool, notify=uiTriggerChanged)
    def checkForUpdatesOnStartup(self) -> bool:
        return self.config.app_settings.check_for_updates

    @checkForUpdatesOnStartup.setter
    def checkForUpdatesOnStartup(self, val: bool) -> None:
        self.config.app_settings.check_for_updates = bool(val)
        self.refreshUI()

    @pyqtProperty(bool, notify=enableRpycReaderChanged)
    def enableRpycReader(self) -> bool:
        return self.config.translation_settings.enable_rpyc_reader

    @enableRpycReader.setter
    def enableRpycReader(self, val: bool) -> None:
        self.config.translation_settings.enable_rpyc_reader = bool(val)
        self.enableRpycReaderChanged.emit()

    @pyqtProperty(bool, notify=enableDeepScanChanged)
    def enableDeepScan(self) -> bool:
        return self.config.translation_settings.enable_deep_scan

    @enableDeepScan.setter
    def enableDeepScan(self, val: bool) -> None:
        self.config.translation_settings.enable_deep_scan = bool(val)
        self.enableDeepScanChanged.emit()

    # ── AI Engine Settings Properties ────────────────────────────────────

    @pyqtProperty(str, notify=selectedEngineChanged)
    def selectedEngine(self) -> str:
        return self._selected_engine.value

    @pyqtSlot(str)
    def setSelectedEngine(self, engine_str: str) -> None:
        """Changes the active translation engine and sets it up if needed."""
        new_engine = self._engine_from_str(engine_str)
        # Update config so it persists
        self.config.translation_settings.selected_engine = engine_str.lower()
        self.config.save_config()
        if new_engine == self._selected_engine:
            return
        self._selected_engine = new_engine
        self.selectedEngineChanged.emit(engine_str)
        # Setup new engine in background if not Google (Google always active as fallback)
        if new_engine not in (TranslationEngine.GOOGLE,):
            if new_engine in (TranslationEngine.OPENAI, TranslationEngine.LOCAL_LLM):
                setup_target = self._setup_ai_translator
            elif new_engine == TranslationEngine.LIBRETRANSLATE:
                setup_target = self._setup_libretranslate
            elif new_engine == TranslationEngine.CUSTOM:
                setup_target = self._setup_custom_endpoint
            else:
                return
            threading.Thread(target=setup_target, daemon=True).start()

    @pyqtProperty(str, notify=openaiApiKeyChanged)
    def openaiApiKey(self) -> str:
        return self.config.api_keys.openai_api_key or ""

    @openaiApiKey.setter
    def openaiApiKey(self, val: str) -> None:
        self.config.api_keys.openai_api_key = val.strip()
        self.openaiApiKeyChanged.emit()

    @pyqtProperty(str, notify=openaiModelChanged)
    def openaiModel(self) -> str:
        return self.config.translation_settings.openai_model or "gpt-4o-mini"

    @openaiModel.setter
    def openaiModel(self, val: str) -> None:
        self.config.translation_settings.openai_model = val.strip()
        self.openaiModelChanged.emit()

    @pyqtProperty(str, notify=openaiBaseUrlChanged)
    def openaiBaseUrl(self) -> str:
        return getattr(self.config.translation_settings, "openai_base_url", "") or ""

    @openaiBaseUrl.setter
    def openaiBaseUrl(self, val: str) -> None:
        self.config.translation_settings.openai_base_url = val.strip()
        self.openaiBaseUrlChanged.emit()

    @pyqtProperty(str, notify=localLlmUrlChanged)
    def localLlmUrl(self) -> str:
        return getattr(self.config.translation_settings, "local_llm_url", "") or "http://localhost:11434/v1"

    @localLlmUrl.setter
    def localLlmUrl(self, val: str) -> None:
        self.config.translation_settings.local_llm_url = val.strip()
        self.localLlmUrlChanged.emit()

    @pyqtProperty(str, notify=localLlmModelChanged)
    def localLlmModel(self) -> str:
        return getattr(self.config.translation_settings, "local_llm_model", "") or "llama3.2"

    @localLlmModel.setter
    def localLlmModel(self, val: str) -> None:
        self.config.translation_settings.local_llm_model = val.strip()
        self.localLlmModelChanged.emit()

    # ── LibreTranslate Properties ─────────────────────────────────────────

    @pyqtProperty(str, notify=libretranslateUrlChanged)
    def libretranslateUrl(self) -> str:
        return getattr(self.config.translation_settings, "libretranslate_url", "") or "http://localhost:5000"

    @libretranslateUrl.setter
    def libretranslateUrl(self, val: str) -> None:
        self.config.translation_settings.libretranslate_url = val.strip()
        self.libretranslateUrlChanged.emit()

    @pyqtProperty(str, notify=libretranslateApiKeyChanged)
    def libretranslateApiKey(self) -> str:
        return getattr(self.config.translation_settings, "libretranslate_api_key", "")

    @libretranslateApiKey.setter
    def libretranslateApiKey(self, val: str) -> None:
        self.config.translation_settings.libretranslate_api_key = val.strip()
        self.libretranslateApiKeyChanged.emit()

    # ── Custom Endpoint Properties ────────────────────────────────────────

    @pyqtProperty(str, notify=customEndpointUrlChanged)
    def customEndpointUrl(self) -> str:
        return getattr(self.config.translation_settings, "custom_endpoint_url", "")

    @customEndpointUrl.setter
    def customEndpointUrl(self, val: str) -> None:
        self.config.translation_settings.custom_endpoint_url = val.strip()
        self.customEndpointUrlChanged.emit()

    @pyqtProperty(str, notify=customEndpointApiKeyChanged)
    def customEndpointApiKey(self) -> str:
        return getattr(self.config.translation_settings, "custom_endpoint_api_key", "")

    @customEndpointApiKey.setter
    def customEndpointApiKey(self, val: str) -> None:
        self.config.translation_settings.custom_endpoint_api_key = val.strip()
        self.customEndpointApiKeyChanged.emit()

    # ── Advanced AI Settings Properties ──────────────────────────────────

    @pyqtProperty(float, notify=aiTemperatureChanged)
    def aiTemperature(self) -> float:
        return self.config.translation_settings.ai_temperature

    @aiTemperature.setter
    def aiTemperature(self, val: float) -> None:
        self.config.translation_settings.ai_temperature = max(0.0, min(float(val), 2.0))
        self.aiTemperatureChanged.emit()

    @pyqtProperty(int, notify=aiTimeoutChanged)
    def aiTimeout(self) -> int:
        return self.config.translation_settings.ai_timeout

    @aiTimeout.setter
    def aiTimeout(self, val: int) -> None:
        self.config.translation_settings.ai_timeout = max(5, min(int(val), 600))
        self.aiTimeoutChanged.emit()

    @pyqtProperty(int, notify=aiMaxTokensChanged)
    def aiMaxTokens(self) -> int:
        return self.config.translation_settings.ai_max_tokens

    @aiMaxTokens.setter
    def aiMaxTokens(self, val: int) -> None:
        self.config.translation_settings.ai_max_tokens = max(64, min(int(val), 32768))
        self.aiMaxTokensChanged.emit()

    @pyqtProperty(int, notify=aiBatchSizeChanged)
    def aiBatchSize(self) -> int:
        return self.config.translation_settings.ai_batch_size

    @aiBatchSize.setter
    def aiBatchSize(self, val: int) -> None:
        self.config.translation_settings.ai_batch_size = max(1, min(int(val), 10000))
        self.aiBatchSizeChanged.emit()

    @pyqtProperty(int, notify=aiRetryCountChanged)
    def aiRetryCount(self) -> int:
        return self.config.translation_settings.ai_retry_count

    @aiRetryCount.setter
    def aiRetryCount(self, val: int) -> None:
        self.config.translation_settings.ai_retry_count = max(0, min(int(val), 20))
        self.aiRetryCountChanged.emit()

    @pyqtProperty(int, notify=aiConcurrencyChanged)
    def aiConcurrency(self) -> int:
        return self.config.translation_settings.ai_concurrency

    @aiConcurrency.setter
    def aiConcurrency(self, val: int) -> None:
        self.config.translation_settings.ai_concurrency = max(1, min(int(val), 20))
        self.aiConcurrencyChanged.emit()

    @pyqtProperty(float, notify=aiRequestDelayChanged)
    def aiRequestDelay(self) -> float:
        return self.config.translation_settings.ai_request_delay

    @aiRequestDelay.setter
    def aiRequestDelay(self, val: float) -> None:
        self.config.translation_settings.ai_request_delay = max(0.0, min(float(val), 60.0))
        self.aiRequestDelayChanged.emit()

    @pyqtProperty(str, notify=aiCustomSystemPromptChanged)
    def aiCustomSystemPrompt(self) -> str:
        return self.config.translation_settings.ai_custom_system_prompt or ""

    @aiCustomSystemPrompt.setter
    def aiCustomSystemPrompt(self, val: str) -> None:
        self.config.translation_settings.ai_custom_system_prompt = val.strip()
        self.aiCustomSystemPromptChanged.emit()


    # ── Utility Slots ────────────────────────────────────────────────────

    @pyqtSlot(str)
    def copyToClipboard(self, text: str) -> None:
        """Copies the given text to system clipboard."""
        from PyQt6.QtGui import QGuiApplication
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(text)

    @pyqtSlot(str, result=str)
    def urlToPath(self, url: str) -> str:
        """QML file:// URL'sini OS path'e çevirir."""
        return _normalize_path(url)

    @pyqtSlot(str, result=bool)
    def openLocalPath(self, path: str) -> bool:
        """Yerel dosya veya klasörü masaüstü kabuğuyla açar."""
        if not path:
            return False
        local = _normalize_path(path)
        if not local:
            return False
        return bool(QDesktopServices.openUrl(QUrl.fromLocalFile(local)))

    @pyqtSlot(result=str)
    def get_app_url(self) -> str:
        """Uygulamanın çalışma dizinini file:// URL olarak döndürür."""
        return QUrl.fromLocalFile(os.getcwd()).toString()

    @pyqtSlot(str, result=str)
    def get_asset_url(self, relative_path: str) -> str:
        """Asset'in tam dosya URL'sini döndürür (frozen bundle uyumlu)."""
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            base = Path(sys._MEIPASS)
        else:
            base = Path(os.getcwd())
        full = base / relative_path
        return QUrl.fromLocalFile(str(full)).toString()

    @pyqtSlot(result=bool)
    def clearTranslationCache(self) -> bool:
        """Seçili projenin yerel ve genel çeviri belleklerini (cache) temizler."""
        if not self._project_path:
            self.logMessage.emit("warning", "No project selected to clear cache.")
            return False
            
        try:
            # 1. Clear memory cache in translation manager
            self.translation_manager._cache.clear()
            self.translation_manager.cache_hits = 0
            self.translation_manager.cache_misses = 0
            
            # Resolve actual project root directory and EXE path
            if os.path.isfile(self._project_path):
                project_dir = os.path.dirname(self._project_path)
                exe_path = self._project_path
            else:
                project_dir = self._project_path
                exe_path = None
                
            from src.utils.path_manager import get_project_id
            project_name = get_project_id(project_dir, exe_path)
                
            # 2. Local cache deletion: <project_path>/game/tl/<lang>/translation_cache.json
            if self._target_language:
                local_cache = os.path.join(self._project_path, 'game', 'tl', self._target_language, "translation_cache.json")
                if os.path.exists(local_cache):
                    try:
                        os.remove(local_cache)
                        self.logMessage.emit("info", f"Local project cache removed: {os.path.basename(local_cache)}")
                    except Exception as ex:
                        self.logMessage.emit("warning", f"Could not remove local cache: {ex}")
            
            # 3. Global project cache deletion: <data_dir>/cache/<project_name>/
            base_cache_dir = os.path.join(self.config.data_dir, getattr(self.config.translation_settings, 'cache_path', 'cache'))
            global_project_cache = os.path.join(base_cache_dir, project_name)
            
            if os.path.exists(global_project_cache):
                import shutil
                try:
                    shutil.rmtree(global_project_cache)
                    self.logMessage.emit("info", f"Global cache for project '{project_name}' removed.")
                except Exception as ex:
                    self.logMessage.emit("warning", f"Could not remove global cache folder: {ex}")
                    
            self.logMessage.emit("info", "Translation memory (cache) cleared successfully.")
            return True
        except Exception as e:
            self.logger.exception("Failed to clear translation cache")
            self.logMessage.emit("error", f"Failed to clear cache: {e}")
            return False

    @pyqtSlot()
    def refreshUI(self) -> None:
        """Arayüzü yeniler ve uiTrigger sinyali gönderir."""
        self._ui_trigger = not self._ui_trigger
        self.uiTriggerChanged.emit()

    @pyqtSlot(str, result=str)
    def getText(self, key: str) -> str:
        return self.config.get_ui_text(key, key)

    @pyqtSlot(str, str, result=str)
    def getTextWithDefault(self, key: str, default: str) -> str:
        return self.config.get_ui_text(key, default)

    # ── UI Language Management ──
    @pyqtSlot(result=list)
    def getAvailableUILanguages(self) -> list:
        return [
            {"code": "tr", "name": "🇹🇷 Türkçe"},
            {"code": "en", "name": "🇬🇧 English"},
            {"code": "de", "name": "🇩🇪 Deutsch"},
            {"code": "fr", "name": "🇫🇷 Français"},
            {"code": "es", "name": "🇪🇸 Español"},
            {"code": "ru", "name": "🇷🇺 Русский"},
            {"code": "fa", "name": "🇮🇷 فارسی"},
            {"code": "zh-CN", "name": "🇨🇳 中文 (简体)"},
            {"code": "ja", "name": "🇯🇵 日本語"},
        ]

    @pyqtSlot(result=str)
    def getCurrentUILanguage(self) -> str:
        return self.config.app_settings.ui_language or "en"

    @pyqtSlot(str)
    def setUILanguage(self, lang_code: str) -> None:
        try:
            from src.utils.config import Language
            lang = Language(lang_code)
            self.config.load_locale(lang)
            self.config.save_config()
            self.languageChanged.emit(lang_code)
            self.refreshUI()
        except Exception as e:
            self.logger.warning(f"Error setting UI language: {e}")

    # ── UI Theme Management ──
    @pyqtSlot(result=list)
    def getAvailableThemes(self) -> list:
        return [
            {"code": "dark", "name": self.config.get_ui_text("theme_dark", "🌙 Dark")},
            {"code": "light", "name": self.config.get_ui_text("theme_light", "☀️ Light")},
            {"code": "red", "name": self.config.get_ui_text("theme_red", "🔴 Red")},
            {"code": "turquoise", "name": self.config.get_ui_text("theme_turquoise", "🔵 Turquoise")},
            {"code": "green", "name": self.config.get_ui_text("theme_green", "🌿 Green")},
            {"code": "neon", "name": self.config.get_ui_text("theme_neon", "🌈 Neon")},
        ]

    @pyqtSlot(result=str)
    def getCurrentTheme(self) -> str:
        return self.config.app_settings.app_theme or "dark"

    @pyqtSlot(str)
    def setTheme(self, theme: str) -> None:
        self.config.app_settings.app_theme = theme
        self.config.save_config()
        self.themeChanged.emit(theme)
        self.refreshUI()

    # ── Language Slots ───────────────────────────────────────────────────

    @pyqtSlot(result=list)
    def getTargetLanguages(self) -> list:
        """Hedef dil listesini döndürür."""
        languages = []
        for code, name in self.config.get_target_languages_for_ui():
            languages.append({"code": code, "name": name})
        return languages

    @pyqtSlot(result=str)
    def getTargetLanguage(self) -> str:
        return self._target_language

    @pyqtSlot(str)
    def setTargetLanguage(self, lang: str) -> None:
        """Hedef dili ayarlar (kalıcı olarak kaydeder)."""
        normalized = self.config.normalize_renpy_language_code(lang)
        self._target_language = normalized
        self.config.translation_settings.target_language = normalized
        self.config.save_config()
        self.logger.info("[LiteBackend] Hedef dil: %s", normalized)

    @pyqtSlot(result=list)
    def getSourceLanguages(self) -> list:
        """Kaynak dil listesini döndürür (Auto-detect + tüm diller)."""
        languages = []
        for code, name in self.config.get_source_languages_for_ui():
            languages.append({"code": code, "name": name})
        return languages

    @pyqtSlot(str)
    def setSourceLanguage(self, lang: str) -> None:
        """Kaynak dili ayarlar."""
        self.config.translation_settings.source_language = lang.strip() if lang.strip() else "auto"
        self.config.save_config()
        self.logger.info("[LiteBackend] Kaynak dil: %s", lang or "auto")

    # ── Project Slot ─────────────────────────────────────────────────────

    @pyqtSlot(str)
    def setProjectPath(self, path: str) -> None:
        """Oyun proje yolunu ayarlar ve Ren'Py projesi olup olmadığını doğrular."""
        path = _normalize_path(path)
        if not path:
            return

        self._project_path = path
        self._tl_mode = False
        self._tl_source_path = ""
        self.config.app_settings.last_input_directory = path
        self.config.save_config()
        self.logMessage.emit("info", f"📁 Proje yolu: {path}")

        # --- TL Retranslation mode detection ---
        # If the user selected a tl/ directory or a language subfolder inside tl/,
        # activate TL retranslation mode (fill empty translations in-place).
        norm = os.path.normpath(path)
        path_parts = norm.replace('\\', '/').split('/')
        is_tl_folder = (
            os.path.basename(norm).lower() == 'tl'
            or (len(path_parts) >= 2 and path_parts[-2].lower() == 'tl')
            or (
                os.path.isdir(path)
                and any(f.lower().endswith('.rpy') for _, _, fs in os.walk(path) for f in fs)
                and not os.path.isdir(os.path.join(path, 'game'))
                and 'tl' in norm.lower().replace('\\', '/').split('/')
            )
        )

        if is_tl_folder and os.path.isdir(path):
            self._tl_mode = True
            self._tl_source_path = path
            self.logMessage.emit(
                "info",
                "🔄 TL klasörü tespit edildi — Retranslation modu aktif. "
                "Sadece boş çeviriler doldurulacak, mevcut çeviriler korunacak."
            )
            return

        # Ren'Py projesi doğrulama
        project_dir = os.path.dirname(path) if os.path.isfile(path) else path
        game_dir = os.path.join(project_dir, "game")
        if not os.path.isdir(game_dir):
            alt = os.path.join(project_dir, "Game")
            if os.path.isdir(alt):
                game_dir = alt

        if os.path.isdir(game_dir):
            self.logMessage.emit("info", "✅ Geçerli Ren'Py projesi tespit edildi.")
        else:
            self.logMessage.emit("warning", "⚠️ game/ klasörü bulunamadı. Lütfen geçerli bir Ren'Py proje dizini seçin.")

    @pyqtSlot(result=str)
    def getLastProjectPath(self) -> str:
        return self.config.app_settings.last_input_directory or ""

    # ── Translation Control Slots ────────────────────────────────────────

    @pyqtSlot()
    def startTranslation(self) -> None:
        """Çeviri pipeline'ını başlatır (normal veya TL retranslation modu)."""
        if not self._project_path:
            self.logMessage.emit("error", "❌ Lütfen önce bir oyun klasörü veya EXE seçin.")
            return

        if self._is_translating:
            return

        self._is_translating = True
        self.translationStarted.emit()

        if self._tl_mode:
            threading.Thread(target=self._run_tl_retranslation, daemon=True).start()
        else:
            self._start_pipeline_translation()

    def _start_pipeline_translation(self) -> None:
        """Normal pipeline tabanlı çeviriyi başlatır."""
        try:
            # Pipeline oluştur ve yapılandır
            self.pipeline = TranslationPipeline(self.config, self.translation_manager)
            self.pipeline.configure(
                game_exe_path=self._project_path,
                target_language=self._target_language,
                source_language="auto",
                engine=self._selected_engine,
                auto_unren=self.config.app_settings.unren_auto_download,
                use_proxy=False,
                include_deep_scan=self.config.translation_settings.enable_deep_scan,
                include_rpyc=self.config.translation_settings.enable_rpyc_reader,
            )

            # Pipeline sinyallerini bu backend'e bağla
            self.pipeline.stage_changed.connect(self._on_stage_changed)
            self.pipeline.progress_updated.connect(self._on_progress_updated)
            self.pipeline.log_message.connect(self._on_log_message)
            self.pipeline.finished.connect(self._on_pipeline_finished)
            self.pipeline.show_warning.connect(self._on_show_warning)

            self.logMessage.emit("info", "🚀 Çeviri başlatılıyor...")

            # Worker thread'de pipeline'ı çalıştır
            self.pipeline_worker = PipelineWorker(self.pipeline)
            self.pipeline_worker.start()

        except Exception as exc:
            self.logger.exception("[LiteBackend] startTranslation hatası")
            self.logMessage.emit("error", f"❌ Başlatma hatası: {exc}")
            self._is_translating = False
            self.translationFinished.emit(False, str(exc))

    @pyqtSlot()
    def stopTranslation(self) -> None:
        """Çeviri pipeline'ını durdurur."""
        if self._tl_mode:
            # TL retranslation modunda thread'i durdur
            self._tl_stop_requested = True
            self.logMessage.emit("warning", "⏹ Durdurma isteği gönderildi...")
        elif self.pipeline and self._is_translating:
            self.pipeline.stop()
            self.logMessage.emit("warning", "⏹ Durdurma isteği gönderildi...")

    def _run_tl_retranslation(self) -> None:
        """
        TL retranslation modu: Ren'Py SDK'nın oluşturduğu tl/ klasörünü
        okur, boş çevirileri Google Translate ile doldurur ve in-place kaydeder.

        Bu metot bir arka plan thread'inde çalışır.
        """
        self._tl_stop_requested = False
        tl_parser = TLParser()
        total_translated = 0
        total_skipped = 0
        total_saved = 0
        total_failed = 0

        try:
            # ── 1. Klasörü tara ──────────────────────────────────────────
            tl_path = self._tl_source_path
            lang = self._target_language

            self.stageChanged.emit("parsing", "📂 TL Dosyaları Taranıyor")
            self.logMessage.emit("info", f"🔍 TL klasörü taranıyor: {tl_path}")

            # parse_directory: tl/lang/ klasörünü parse et.
            # Eğer kullanıcı zaten tl/lang/ içindeyse bu da desteklenir.
            tl_files = tl_parser.parse_directory(tl_path, lang)

            if not tl_files:
                # Fallback: kullanıcı doğrudan tl/lang/ klasörünü seçti
                # parse_directory, lang alt klasörünü aramaya çalışır;
                # ama tl_path=tl/lang/ ise zaten bu klasörü dener.
                # İkinci deneme: tl_path'i doğrudan parse etmeye çalış.
                import os
                rpy_files = []
                for root, _, fnames in os.walk(tl_path):
                    for fname in fnames:
                        if fname.lower().endswith('.rpy'):
                            rpy_files.append(os.path.join(root, fname))
                if rpy_files:
                    for fpath in rpy_files:
                        tf = tl_parser.parse_file(fpath)
                        if tf:
                            tl_files.append(tf)

            if not tl_files:
                self.logMessage.emit("error", "❌ TL klasöründe .rpy dosyası bulunamadı.")
                self._is_translating = False
                self.translationFinished.emit(False, "TL dosyası bulunamadı.")
                return

            stats = get_translation_stats(tl_files)
            total_entries = stats['total']
            untranslated = stats['untranslated']

            self.logMessage.emit(
                "info",
                f"📊 {len(tl_files)} dosya, {total_entries} giriş, "
                f"{untranslated} çeviri bekliyor, {stats['translated']} zaten çevrilmiş."
            )

            if untranslated == 0:
                self.logMessage.emit("success", "✅ Tüm çeviriler zaten tamamlanmış.")
                self.statsReady.emit(total_entries, stats['translated'], 0)
                self.completionSummary.emit(
                    "✅ Çeviri Tamamlandı",
                    "Tüm girişler zaten çevrilmiş durumda.",
                    tl_path, "", 0
                )
                self._is_translating = False
                self.translationFinished.emit(True, "Zaten çevrilmiş.")
                return

            # ── 2. Çeviri ────────────────────────────────────────────────
            self.stageChanged.emit("translating", "🌐 Çeviriliyor")

            google = self.translation_manager.translators.get(TranslationEngine.GOOGLE)
            if not google:
                self.logMessage.emit("error", "❌ Google Translate hazır değil.")
                self._is_translating = False
                self.translationFinished.emit(False, "Google Translate hazır değil.")
                return

            processed = 0
            for tl_file in tl_files:
                if self._tl_stop_requested:
                    self.logMessage.emit("warning", "⏹ Çeviri durduruldu.")
                    break

                untranslated_entries = tl_file.get_untranslated()
                if not untranslated_entries:
                    continue

                # Batch translate
                texts = [e.original_text for e in untranslated_entries]
                try:
                    results = google.translate_batch(
                        texts,
                        source_lang="auto",
                        target_lang=lang,
                    )
                except Exception as exc:
                    self.logMessage.emit("warning", f"⚠️ Çeviri hatası ({os.path.basename(tl_file.file_path)}): {exc}")
                    total_failed += len(texts)
                    processed += len(texts)
                    self.progressChanged.emit(processed, untranslated, f"Hata: {os.path.basename(tl_file.file_path)}")
                    continue

                # ID → translated_text sözlüğü oluştur
                translations: dict[str, str] = {}
                for entry, result in zip(untranslated_entries, results):
                    translated = getattr(result, 'translated_text', None) or getattr(result, 'text', None) or ""
                    if translated:
                        translations[entry.translation_id] = translated
                        translations[entry.original_text] = translated  # fallback key
                        total_translated += 1
                    else:
                        total_skipped += 1

                processed += len(texts)
                self.progressChanged.emit(
                    processed, untranslated,
                    f"Çevriliyor: {os.path.basename(tl_file.file_path)}"
                )

                # ── 3. Kaydet ────────────────────────────────────────────
                if translations:
                    success = tl_parser.save_translations(tl_file, translations)
                    if success:
                        total_saved += 1
                    else:
                        self.logMessage.emit("warning", f"⚠️ Kaydetme başarısız: {tl_file.file_path}")
                        total_failed += 1

            # ── 4. Özet ──────────────────────────────────────────────────
            self.stageChanged.emit("completed", "✅ Tamamlandı")
            self.statsReady.emit(
                total_entries,
                stats['translated'] + total_translated,
                max(0, untranslated - total_translated)
            )

            msg = (
                f"{total_translated} giriş çevrildi, "
                f"{stats['translated']} zaten çevriliydi, "
                f"{total_saved}/{len(tl_files)} dosya kaydedildi."
            )
            self.logMessage.emit("success", f"✅ TL Retranslation tamamlandı: {msg}")
            self.completionSummary.emit(
                "✅ TL Retranslation Tamamlandı",
                msg,
                tl_path, "", 0
            )
            self._is_translating = False
            self.translationFinished.emit(True, msg)

        except Exception as exc:
            self.logger.exception("[LiteBackend] _run_tl_retranslation hatası")
            self.logMessage.emit("error", f"❌ TL retranslation hatası: {exc}")
            self._is_translating = False
            self.translationFinished.emit(False, str(exc))


    # ── Pipeline Signal Handlers ─────────────────────────────────────────

    def _on_stage_changed(self, stage: str, display_name: str) -> None:
        self.stageChanged.emit(stage, display_name)

    def _on_progress_updated(self, current: int, total: int, text: str) -> None:
        self.progressChanged.emit(current, total, text)

    def _on_log_message(self, level: str, message: str) -> None:
        self.logMessage.emit(level, message)

    def _on_show_warning(self, title: str, message: str) -> None:
        self.warningMessage.emit(title, message)

    def _on_pipeline_finished(self, result: object) -> None:
        """Pipeline tamamlandığında veya hatayla bittiğinde çağrılır."""
        self._is_translating = False

        success = getattr(result, "success", False)
        message = getattr(result, "message", "")
        stats = getattr(result, "stats", None) or {}
        output_path = getattr(result, "output_path", "") or ""

        # İstatistikleri yayınla
        total = stats.get("total", 0)
        translated = stats.get("translated", 0)
        untranslated = stats.get("untranslated", total - translated)
        self.statsReady.emit(total, translated, untranslated)

        # Tamamlanma özeti
        if success:
            title = "✅ Çeviri Tamamlandı"
            diag_path = getattr(result, "error", "") or ""
            # Diagnostic path'i stats'tan almayı dene
            if stats and "diagnostic_path" in stats:
                diag_path = stats["diagnostic_path"]
            self.completionSummary.emit(title, message, output_path, diag_path, 0)
        else:
            error_detail = getattr(result, "error", "") or message
            self.logMessage.emit("error", f"❌ Çeviri başarısız: {error_detail}")

        self.translationFinished.emit(success, message)

    @pyqtSlot()
    def saveSettings(self) -> None:
        """Kayıtlı ayarları config.json'a kalıcı olarak kaydeder (Lite override'lar korunarak)."""
        try:
            # 1. Mevcut UI'dan değiştirilen ayarları yedekle
            threads = self.config.translation_settings.max_concurrent_threads
            delay = self.config.translation_settings.request_delay
            batch_size = self.config.translation_settings.max_batch_size
            multi = self.config.translation_settings.use_multi_endpoint
            lingva = self.config.translation_settings.enable_lingva_fallback
            aggressive = self.config.translation_settings.aggressive_retry_translation
            cache_enabled = self.config.translation_settings.use_cache
            chk_updates = self.config.app_settings.check_for_updates
            rpyc = self.config.translation_settings.enable_rpyc_reader
            deep_scan = self.config.translation_settings.enable_deep_scan
            # AI engine settings
            selected_engine_str = self._selected_engine.value
            openai_key = self.config.api_keys.openai_api_key or ""
            openai_model = self.config.translation_settings.openai_model or "gpt-4o-mini"
            openai_base_url = getattr(self.config.translation_settings, "openai_base_url", "") or ""
            local_llm_url = getattr(self.config.translation_settings, "local_llm_url", "") or ""
            local_llm_model = getattr(self.config.translation_settings, "local_llm_model", "") or "llama3.2"
            
            # Gelişmiş AI Ayarları
            ai_temp = self.config.translation_settings.ai_temperature
            ai_timeo = self.config.translation_settings.ai_timeout
            ai_tokens = self.config.translation_settings.ai_max_tokens
            ai_bsize = self.config.translation_settings.ai_batch_size
            ai_retries = self.config.translation_settings.ai_retry_count
            ai_concur = self.config.translation_settings.ai_concurrency
            ai_delay = self.config.translation_settings.ai_request_delay
            ai_sys_prompt = self.config.translation_settings.ai_custom_system_prompt

            # 2. Config dosyasını sıfırdan yükle (böylece tam sürüm ayarları bozulmaz)
            self.config.load_config()

            # 3. Sadece Lite'ta izin verilen ayarları üzerine yaz
            self.config.translation_settings.max_concurrent_threads = threads
            self.config.translation_settings.request_delay = delay
            self.config.translation_settings.max_batch_size = batch_size
            self.config.translation_settings.use_multi_endpoint = multi
            self.config.translation_settings.enable_lingva_fallback = lingva
            self.config.translation_settings.aggressive_retry_translation = aggressive
            self.config.translation_settings.use_cache = cache_enabled
            self.config.app_settings.check_for_updates = chk_updates
            self.config.translation_settings.enable_rpyc_reader = rpyc
            self.config.translation_settings.enable_deep_scan = deep_scan
            # AI engine settings
            self.config.translation_settings.selected_engine = selected_engine_str
            self.config.api_keys.openai_api_key = openai_key
            self.config.translation_settings.openai_model = openai_model
            self.config.translation_settings.openai_base_url = openai_base_url
            self.config.translation_settings.local_llm_url = local_llm_url
            self.config.translation_settings.local_llm_model = local_llm_model
            # Gelişmiş AI Ayarları
            self.config.translation_settings.ai_temperature = ai_temp
            self.config.translation_settings.ai_timeout = ai_timeo
            self.config.translation_settings.ai_max_tokens = ai_tokens
            self.config.translation_settings.ai_batch_size = ai_bsize
            self.config.translation_settings.ai_retry_count = ai_retries
            self.config.translation_settings.ai_concurrency = ai_concur
            self.config.translation_settings.ai_request_delay = ai_delay
            self.config.translation_settings.ai_custom_system_prompt = ai_sys_prompt

            # 4. Kaydet
            self.config.save_config()

            # 5. Lite-specific runtime override'ları tekrar uygula
            self.config.translation_settings.enable_deep_extraction = False
            self.config.translation_settings.enable_unrpyc_decompile = False

            # Pipeline ve manager parametrelerini anlık güncelle
            if self.translation_manager:
                self.translation_manager.max_concurrent_requests = threads
                self.translation_manager.max_batch_size = batch_size
                self.translation_manager.use_cache = cache_enabled
                # Manager altındaki Google translator'ı güncelle
                google_translator = self.translation_manager.translators.get(TranslationEngine.GOOGLE)
                if google_translator:
                    google_translator.multi_q_concurrency = threads
                    google_translator.max_texts_per_slice = batch_size
                    google_translator._google_request_delay = delay
                    google_translator.use_multi_endpoint = multi
                    google_translator.enable_lingva_fallback = lingva
                    google_translator.aggressive_retry = aggressive

                # Re-setup the active AI translator to apply newly saved settings (API keys, models, base URLs)
                if self._selected_engine != TranslationEngine.GOOGLE:
                    threading.Thread(
                        target=self._setup_ai_translator,
                        args=(self._selected_engine,),
                        daemon=True,
                    ).start()

            self.logMessage.emit("success", "💾 Ayarlar başarıyla kaydedildi.")
        except Exception as exc:
            self.logger.exception("[LiteBackend] saveSettings hatası")
            self.logMessage.emit("error", f"❌ Ayarlar kaydedilemedi: {exc}")

    @pyqtSlot(bool)
    def checkForUpdates(self, manual: bool = False) -> None:
        """Yeni güncellemeleri denetler (asenkron)."""
        if not manual and not self.config.app_settings.check_for_updates:
            return
        
        msg = self.config.get_ui_text("update_checking", "Checking for updates...")
        self.logMessage.emit("info", f"🔍 {msg}")
        threading.Thread(target=self._check_updates_thread, args=(manual,), daemon=True).start()

    def _check_updates_thread(self, manual: bool) -> None:
        try:
            from src.utils.update_checker import check_for_updates
            result = check_for_updates(self._version)
            if result.update_available:
                log_msg = self.config.get_ui_text("log_update_available", "Update available: {version}").replace("{version}", result.latest_version)
                self.logMessage.emit("success", f"🔔 {log_msg}")
                self.updateAvailable.emit(
                    result.current_version,
                    result.latest_version,
                    result.release_url,
                )
                self.updateCheckFinished.emit(True, f"Update found: {result.latest_version}")
            else:
                msg = self.config.get_ui_text("update_check_no_update", "You are up to date.")
                if manual:
                    self.logMessage.emit("info", f"ℹ️ {msg}")
                self.updateCheckFinished.emit(False, msg)
        except Exception as exc:
            err_msg = self.config.get_ui_text("log_update_check_failed", "Update check failed: {error}").replace("{error}", str(exc))
            self.logMessage.emit("error", f"❌ {err_msg}")
            self.updateCheckFinished.emit(False, f"Update Check Failed: {exc}")

