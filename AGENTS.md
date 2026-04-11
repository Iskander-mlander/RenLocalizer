# AGENTS.md — RenLocalizer Proje Kılavuzu (AI Agent Bağlamı)

> Bu dosya, AI kodlama asistanlarının (GitHub Copilot, Cursor, Claude vb.) projeyi hızla anlaması için hazırlanmıştır.
> Son güncelleme: 2026-04-06 | Versiyon: 2.8.2

---

## 1. Proje Özeti

**RenLocalizer**, Ren'Py görsel novel oyunlarının çeviri sürecini otomatikleştiren bir masaüstü uygulamadır.
- `.rpy` / `.rpyc` / `.rpymc` dosyalarından çevrilebilir metinleri çıkarır
- 8 farklı çeviri motoruyla otomatik çevirir
- Ren'Py uyumlu `tl/<dil>/` çıktı yapısı üretir (dosya-bazlı `.rpy` + `strings.json` + runtime hook)
- PyQt6 + QML tabanlı GUI ve headless CLI modu sunar
- Windows, Linux (AppImage), macOS (DMG) platformlarını destekler

**Dil:** Python 3.10+ | **GUI Framework:** PyQt6 + Qt Quick (QML) | **Lisans:** Açık kaynak

---

## 2. Dizin Yapısı

```
RenLocalizer/
├── run.py                  # GUI başlatıcı (PyQt6 + QML)
├── run_cli.py              # CLI başlatıcı (headless)
├── run.bat                 # Windows kısayolu
├── config.json             # Merkezi yapılandırma dosyası
├── glossary.json           # Kullanıcı sözlüğü (terim koruma)
├── requirements.txt        # Python bağımlılıkları
├── RenLocalizer.spec       # PyInstaller build spec
│
├── src/
│   ├── version.py          # VERSION = "2.8.2"
│   ├── cli_main.py         # CLI ana modülü (argparse + QCoreApplication)
│   │
│   ├── core/               # ★ Ana çeviri motoru (17 modül, ~17K satır)
│   │   ├── translation_pipeline.py  # 7-aşamalı orkestratör (QObject)
│   │   ├── parser.py                # Ren'Py metin çıkarıcı (3731 satır)
│   │   ├── translator.py            # Çeviri motorları taban + Google (2547 satır)
│   │   ├── syntax_guard.py          # Sözdizimi koruma/geri yükleme (1497 satır)
│   │   ├── ai_translator.py         # OpenAI/Gemini/LocalLLM motorları
│   │   ├── deep_extraction.py       # Derin metin çıkarma (Tier 1/2/3)
│   │   ├── rpyc_reader.py           # .rpyc binary AST okuyucu (2686 satır)
│   │   ├── rpymc_reader.py          # .rpymc dosya okuyucu
│   │   ├── renpy_lexer.py           # Satır-tabanlı lexer (token stream)
│   │   ├── pyparse_grammar.py       # SDK-bağımsız grammar
│   │   ├── tl_parser.py             # tl/ çeviri dosyası parser'ı
│   │   ├── output_formatter.py      # Çıktı biçimlendirici + false positive filtre
│   │   ├── exporter.py              # JSON → RPY dönüştürücü
│   │   ├── runtime_hook_template.py # Oyun içi çeviri hook şablonu (v4.1.1+)
│   │   ├── runtime_coverage.py      # Runtime miss scoring + alias promotion yardımcıları
│   │   ├── proxy_manager.py         # Proxy rotasyon yöneticisi
│   │   ├── constants.py             # Google mirror'ları, Lingva instance'ları, timeout'lar
│   │   ├── diagnostics.py           # Tanılama raporu üretici
│   │   ├── exceptions.py            # Özel istisna hiyerarşisi
│   │   └── data_extractors.py       # JSON/YAML veri çıkarma plugin sistemi
│   │
│   ├── backend/             # QML ↔ Python köprüsü
│   │   ├── app_backend.py           # AppBackend (ana backend, 1575 satır)
│   │   └── settings_backend.py      # SettingsBackend (ayarlar, 808 satır)
│   │
│   ├── gui/qml/             # QML arayüz dosyaları
│   │   ├── main.qml                 # Ana pencere (6 tema, navigation + stack)
│   │   ├── components/
│   │   │   └── NavigationBar.qml    # Sol kenar navigasyon
│   │   └── pages/
│   │       ├── HomePage.qml         # Ana çeviri sayfası
│   │       ├── SettingsPage.qml     # Ayarlar (6 grup)
│   │       ├── ToolsPage.qml       # Yardımcı araçlar
│   │       ├── GlossaryPage.qml    # Sözlük yönetimi
│   │       ├── CachePage.qml       # Çeviri belleği (TM)
│   │       └── AboutPage.qml       # Hakkında
│   │
│   ├── utils/               # Yardımcı modüller
│   │   ├── config.py               # ConfigManager — merkezi yapılandırma
│   │   ├── encoding.py             # Güvenli metin okuma/yazma (atomik, multi-encoding)
│   │   ├── logger.py               # API key maskelemeli loglama
│   │   ├── data_transfer.py        # Glossary import/export (JSON, XLSX, CSV)
│   │   ├── font_injector.py        # Google Fonts otomatik enjeksiyon
│   │   ├── project_io.py           # .rlproj proje arşivi import/export
│   │   ├── rpa_packer.py           # RPA-3.0 arşiv oluşturucu
│   │   ├── rpa_parser.py           # RPA arşiv çıkarıcı (native)
│   │   ├── unrpa_adapter.py        # RPA çıkarma birleşik adaptör
│   │   ├── translation_crypto.py   # Obfuscation (Base64) + AES-256-GCM şifreleme
│   │   ├── update_checker.py       # GitHub sürüm kontrolü
│   │   └── constants.py            # AI timeout'ları, pencere boyutları
│   │
│   └── tools/               # Opsiyonel araçlar
│       ├── renpy_lint.py            # Çeviri sonrası doğrulama (10 hata kodu)
│       ├── health_check.py          # Proje sağlık kontrolü
│       ├── fuzzy_matcher.py         # Bulanık eşleştirme
│       ├── context_viewer.py        # Bağlam görüntüleyici
│       ├── font_helper.py           # Font uyumluluk testi
│       ├── deferred_loading.py      # Ertelenmiş yükleme üretici
│       └── glossary_extractor/      # Otomatik sözlük çıkarma
│
├── locales/                 # UI çevirileri (8 dil)
│   ├── en.json, tr.json, de.json, es.json
│   ├── fr.json, ru.json, fa.json, zh-CN.json
│
├── tests/                   # Test suite (520+ test)
│   ├── test_parser.py, test_edge_cases.py, test_false_positives.py
│   ├── test_rpyc_reader.py, test_atomic_segments.py, ...
│
├── docs/                    # Dokümantasyon
│   ├── CLI_USAGE.md, DETAILS.md, RPY_PATTERN_ANALYSIS.md
│
├── tools/                   # Geliştirici analiz araçları
│   ├── analyze_false_positives.py, debug_parser_case.py, ...
│
├── cache/                   # Çeviri önbelleği (oyun bazlı)
├── build/                   # Platform build scriptleri (linux/, macos/)
└── examples/                # Örnek .rpy dosyaları
```

---

## 3. Mimari & Veri Akışı

### 3.1 Katmanlı Mimari

```
┌─────────────────────────────────────────────┐
│              QML UI Katmanı                  │
│  main.qml → NavigationBar + StackLayout     │
│  6 Sayfa: Home, Tools, Glossary, Cache,     │
│           Settings, About                    │
└──────────────────┬──────────────────────────┘
                   │ pyqtSignal / @pyqtSlot
┌──────────────────▼──────────────────────────┐
│           Backend Köprü Katmanı              │
│  AppBackend ←→ SettingsBackend              │
└──────────┬───────────────┬──────────────────┘
           │               │
┌──────────▼───────┐ ┌─────▼──────────────────┐
│   Core Katmanı   │ │    Utils Katmanı        │
│  Pipeline,       │ │  ConfigManager, encoding│
│  Parser, Lexer,  │ │  font_injector, rpa_*,  │
│  Translator(s),  │ │  translation_crypto,    │
│  SyntaxGuard,    │ │  project_io, logger,    │
│  AI Translators, │ │  update_checker,        │
│  RPYCReader      │ │  data_transfer          │
└──────────────────┘ └────────────────────────┘
           │
┌──────────▼──────────┐
│    CLI Katmanı       │
│  cli_main.py         │
│  (headless pipeline) │
└─────────────────────┘
```

### 3.2 Pipeline Akışı (7 Aşama)

```
TranslationPipeline.run()
  │
  ├─ 1. VALIDATING   → Proje yolu, game/ klasörü, .rpy dosyaları doğrulama
  ├─ 2. UNRPA        → .rpa arşivlerini çıkarma (UnrpaAdapter)
  ├─ 3. GENERATING   → tl/<dil>/ klasör yapısı oluşturma
  ├─ 4. PARSING      → Metin çıkarma:
  │     ├── RenPyParser       (.rpy regex tabanlı)
  │     ├── renpy_lexer       (token tabanlı)
  │     ├── pyparse_grammar   (SDK-bağımsız)
  │     ├── rpyc_reader       (.rpyc AST tabanlı)
  │     └── tl_parser         (mevcut tl/ çevirileri)
  ├─ 5. TRANSLATING  → Çeviri:
  │     ├── syntax_guard.protect() → Ren'Py kodunu koruma
  │     ├── Motor seçimi: Google / DeepL / OpenAI / Gemini / LLM / LibreTranslate
  │     └── syntax_guard.restore() → Kodu geri yükleme
  ├─ 6. SAVING       → Çıktı üretme:
  │     ├── output_formatter   (glossary + false-positive filtre)
  │     ├── tl/<dil>/*.rpy     (dosya-bazlı çeviri blokları)
  │     ├── strings.json       (runtime hook için; visible-form + runtime-observed alias synthesis içerir)
  │     └── runtime hook       (oyun içi _rl_hook.rpy; normalized exact + guarded phrase fallback + screen-scope harvesting diagnostics)
  └─ 7. COMPLETED    → Tanılama raporu
```

---

## 4. Çeviri Motorları

| Motor | Sınıf | Dosya | Özellik |
|-------|-------|-------|---------|
| Google Translate | `GoogleTranslator` | `translator.py` | 13 mirror + 4 Lingva fallback, multi-q batch |
| DeepL | `DeepLTranslator` | `translator.py` | Formalite desteği, API key gerekli |
| OpenAI | `OpenAITranslator` | `ai_translator.py` | GPT modelleri, XML batch, NSFW fallback |
| Gemini | `GeminiTranslator` | `ai_translator.py` | Google AI (Flash/Pro), safety settings |
| DeepSeek | OpenAI uyumlu | `ai_translator.py` | OpenAI API uyumlu endpoint desteği |
| Local LLM | `LocalLLMTranslator` | `ai_translator.py` | Ollama / LM Studio, tamamen lokal |
| LibreTranslate | `LibreTranslateTranslator` | `translator.py` | Offline (Docker/Local), 3-tier retry |
| Yandex | `YandexTranslator` | `translator.py` | Free Widget API (SID-based rotation) |
| Pseudo | `PseudoTranslator` | `translator.py` | Test amaçlı sahte çeviri |

---

## 5. Anahtar Mekanizmalar

### 5.1 Syntax Guard (Sözdizimi Koruması)
- **Dosya:** `src/core/syntax_guard.py` (1497 satır)
- **Token Formatı:** `⟦N⟧` (Unicode bracket — alfabe bağımsız, transliterasyon güvenli)
- **Koruma Akışı:** `protect_renpy_syntax(text)` → `(korunan_metin, placeholder_dict)`
- **Geri Yükleme:** `restore_renpy_syntax(metin, placeholders)` → orijinal sözdizimli metin
- **Modlar:** Token mode (Google web), HTML mode (Cloud API), XML mode (AI/LLM)
- **Kurtarma Katmanları:** Aşama 0 (Unicode token), 0.1 (bracket-stripped), 0.5-0.6 (legacy uyum), 1 (generic)
- **Fuzzy Recovery:** Suffix eşleştirme, transliterasyon düzeltme (Kiril/Yunan), eksik placeholder enjeksiyonu

### 5.2 False Positive Filtreleme
- **Dosya:** `src/core/output_formatter.py` → `_should_skip_translation()`
- **~217 teknik terim** (`RENPY_TECHNICAL_TERMS` seti)
- **20+ pre-compiled regex:** Python koşulları, dotted-path, list comprehension, format template, kısa ALL_CAPS
- **Amacı:** Kod string'lerinin çevrilmesini engelleyerek Ren'Py crash'lerini önlemek

### 5.3 Deep Extraction (Derin Metin Çıkarma)
- **Dosya:** `src/core/deep_extraction.py`
- **Tier 1:** Her zaman metin içeren fonksiyonlar (`renpy.notify`, `Character`, `Text` vb.)
- **Tier 2:** Bağlama bağlı fonksiyonlar
- **Tier 3:** Asla çıkarılmayacak fonksiyonlar (blacklist)
- **Özel:** Custom function params (kullanıcı tanımlı, `config.json` → `custom_function_params`)

### 5.4 Runtime Hook (Oyun İçi Çeviri)
- **Dosya:** `src/core/runtime_hook_template.py` (v4.1.1+)
- **Mekanizma:** `init -999 python:` bloğu ile `strings.json` yüklenir; exact-match odaklı runtime çeviri yapılır
- **Katman 1:** `config.say_menu_text_filter` — pre-interpolation exact dict lookup
- **Katman 2:** `config.replace_text` — post-interpolation exact + case-insensitive + normalized exact + sınırlı template-aware eşleme
- **Ek:** Runtime miss diagnostics (`runtime_missed_strings.jsonl`), visible-form alias synthesis, runtime-observed alias promotion, screen-scope harvesting, RTL yön desteği ve dil değişiminde yeniden yükleme senkronu
- **Mod Davranışı:** `balanced` yalnızca yüksek güvenli exact/alias kurtarmalarına izin verir; `aggressive` orta güvenli runtime/screen adaylarını da exact alias üretimine dahil eder
- **Performans:** Template/phrase fallback adayları indexlenir; `replace_text` ve normalize lookup sonuçları bounded cache ile saklanır. Screen harvesting interaction-start tarafında tutulur, restart-heavy akışlarda tekrar tekrar çalışmaz. Bu özellikle büyük `strings.json` ve sandbox/custom-screen ağırlıklı oyunlarda rollback/UI gecikmesini azaltmayı hedefler.
- **Güvenlik:** Trie/substring replacement kullanılmaz; kısmi replacement yapılmaz (`[GAME.ship.name]` bozulma riski). Uzun phrase fallback yalnızca tek ve çakışmasız adaylarda çalışır. Screen harvesting yalnızca gözlem amaçlıdır; gameplay metnini değiştirmez.

### 5.5 Delimiter-Aware Translation
- **Pattern'ler:** `<A|B|C>` (angle-pipe) ve `A|B|C` (bare pipe)
- **Akış:** `split_angle_pipe_groups()` → her segment bağımsız çevrilir → `rejoin_angle_pipe_groups()`
- **Atomik Segment Kaydı:** Her segment strings.json'a ayrı ayrı yazılır (Ren'Py `vary()` uyumlu)

### 5.6 Font Injection
- **Dosya:** `src/utils/font_injector.py`
- **Mekanizma:** Google Fonts tabanlı font indirip `game/zzz_renlocalizer_font.rpy` üretir; hedef dil aktifken runtime font yükleyicisini kancalayarak istenen fontu öne geçirir
- **Ek:** `translate <lang> python:` bloğu ile temel `gui.*_font` alanlarını günceller ve `style.rebuild()` çağırır
- **Risk Alanı:** Oyunların custom stil/font akışları çok değişken olduğu için bu araç özellikle hardcoded custom displayable/font cache kullanan projelerde ek doğrulama gerektirebilir
- **Yardımcı Tarama:** `src/tools/font_helper.py` içindeki statik risk taraması `what_font=`, `Text(..., font=...)`, `{font=...}`, `FontGroup()`, `config.font_name_map`, `config.font_replacement_map` ve image-font registration gibi kör noktaları raporlayabilir

---

## 6. Yapılandırma Sistemi

### 6.1 Config Dosyası: `config.json`
4 ana bölüm (her biri `@dataclass` ile doğrulanır):

| Bölüm | İçerik |
|-------|--------|
| `translation_settings` | Diller, batch boyutu, motor ayarları, AI parametreleri, filtreler |
| `api_keys` | DeepL, OpenAI, Gemini, DeepSeek API anahtarları |
| `app_settings` | UI dili, tema, son açılan proje, güncelleme kontrolü |
| `proxy_settings` | Proxy URL, manuel proxy listesi, rotasyon ayarları |

### 6.2 ConfigManager (`src/utils/config.py`)
- Merkezi ayar yöneticisi, thread-safe (lock kullanır)
- `__post_init__` doğrulayıcılar: numeric clamp, enum allowlist, string sanitize
- 9 dil desteği: TR, EN, DE, FR, ES, RU, FA, ZH-CN (+ JA hazırlık)
- Locale dosyaları: `locales/<kod>.json`

---

## 7. Test Altyapısı

- **Framework:** `unittest` (standart Python)
- **Toplam:** 700+ test (40+ test dosyası)
- **Çalıştırma:** `python -m pytest tests/` veya `python -m unittest discover tests/`
- **Kapsam alanları:**
  - Parser doğruluğu, edge case'ler, false positive filtreleri
  - Syntax guard koruma/geri yükleme
  - RPYC okuyucu, placeholder bütünlüğü
  - Config doğrulama, ayar sanitizasyonu
  - Atomik segmentler, delimiter sistemleri
  - Google batch metadata, HTML mode guard
  - DeepL/AI preprotected flow
  - Çeviri ID hesaplama, robustness
  - Runtime hook diagnostics, visible-form/runtime-observed alias synthesis, mode-aware runtime promotion, cache/TM akışı, PyQt6 CI/workflow doğrulamaları

---

## 8. Build & Dağıtım

| Platform | Komut / Yöntem | Çıktı |
|----------|----------------|-------|
| Windows | `pyinstaller RenLocalizer.spec` | ZIP arşivi |
| Linux | `build/linux/` scriptleri | AppImage + tar.gz |
| macOS | `build/macos/` scriptleri | DMG |
| CI/CD | GitHub Actions | Release build + source compatibility matrix |

**Bağımlılıklar:** `requirements.txt` — PyQt6 (source: `>=6.6,<6.11`), aiohttp, requests, httpx, chardet, openai, google-genai, rapidfuzz, pandas, openpyxl, unrpa, PyYAML, fonttools, Pillow
**Release pin:** `constraints-release.txt` — PyQt6 6.10.1 stack

---

## 9. Geliştirici Notları

### Kod Stili
- Python 3.10+ (walrus operator, match-case nadiren)
- Type hint'ler tutarlı kullanılır
- Pre-compiled regex'ler modül seviyesinde (performans)
- Dataclass tabanlı veri modelleri
- QML tarafında Material 3 tarzı, custom tema sistemi
- Masaüstü tamamlanma bildirimi Qt system tray desteği varsa native notification olarak da gösterilebilir; destek yoksa mevcut QML completion dialog fallback olarak kalır

### Sık Düzenlenen Dosyalar (Hotspot'lar)
| Dosya | Satır | Neden sık değişir |
|-------|-------|-------------------|
| `translation_pipeline.py` | 3199 | Yeni motor entegrasyonu, bug fix, akış değişikliği |
| `parser.py` | 3731 | Yeni pattern ekleme, false positive düzeltme |
| `syntax_guard.py` | 1497 | Token format değişikliği, kurtarma katmanı ekleme |
| `output_formatter.py` | 1108 | Yeni filtre regex'leri, teknik terim ekleme |
| `translator.py` | 2547 | Motor optimizasyonu, rate limit, endpoint ekleme |
| `app_backend.py` | 1575 | QML slot ekleme, sinyal değişikliği |
| `SettingsPage.qml` | 924 | Yeni ayar grupları, UI düzenlemesi |

### Önemli Sabitler (Dokunurken Dikkat)
- `GOOGLE_ENDPOINTS` (13 mirror) → `src/core/constants.py`
- `RENPY_TECHNICAL_TERMS` (~217 terim) → `src/core/output_formatter.py`
- `TIER1_TEXT_CALLS` / `TIER3_BLACKLIST` → `src/core/deep_extraction.py`
- `RUNTIME_HOOK_TEMPLATE` → `src/core/runtime_hook_template.py`
- Pipeline stage enum → `src/core/translation_pipeline.py`

### Dikkat Edilecek Bağımlılık Zinciri
```
ConfigManager ← Neredeyse her modül import eder
SyntaxGuard ← Tüm translator'lar (protect/restore)
RenPyParser ← Pipeline + RPYC reader (DATA_KEY_WHITELIST paylaşımı)
BaseTranslator ← Google, DeepL, AI translator'lar (soyut taban)
encoding.py ← Parser, pipeline, exporter (atomik dosya yazma)
strings.json ← Runtime hook davranışı için kritik index; yalnızca export artifaktı değildir
```

---

## 10. Sık Karşılaşılan Görevler

### Yeni Çeviri Motoru Ekleme
1. `src/core/translator.py` → `TranslationEngine` enum'a ekle
2. `BaseTranslator` alt sınıfı oluştur (`translate_single`, `translate_batch`)
3. `src/core/translation_pipeline.py` → motor init bloğuna ekle
4. `src/backend/app_backend.py` → `_setup_translation_engines()` içine ekle
5. `src/gui/qml/pages/HomePage.qml` → motor ComboBox'ına ekle
6. `src/gui/qml/pages/SettingsPage.qml` → motor ayar bölümü ekle
7. `locales/*.json` → motor adı çevirilerini ekle
8. `tests/` → en az parser/runtime/cache/CI etkisi olan alanlar için regresyon ekle

### Yeni False Positive Filtre Ekleme
1. `src/core/output_formatter.py` → Pre-compiled regex ekle
2. `_should_skip_translation()` içinde kontrol noktası ekle
3. `tests/test_false_positives.py` veya `test_false_positive_filters.py` → test ekle

### Yeni Locale (Dil) Desteği Ekleme
1. `locales/<kod>.json` oluştur (`en.json` şablonundan)
2. `src/utils/config.py` → `Language` enum'a ekle
3. `SettingsPage.qml` → dil ComboBox'ına ekle
4. `settings_backend.py` → dil listesine ekle

### Parser'a Yeni Ren'Py Pattern Ekleme
1. `src/core/parser.py` → Regex tanımla (modül seviyesi pre-compiled)
2. Uygun `parse_*` metoduna entegre et
3. `tests/test_parser.py` → test case ekle
4. `tests/test_edge_cases.py` → edge case ekle

---

## 11. Bilinen Sınırlamalar & Teknik Borç

- **Locale teknik borcu sürüyor:** Görünür anahtarların büyük kısmı temizlenmiş olsa da bazı dil dosyalarında eski fallback/üslup tutarsızlıkları kalmış olabilir
- **Exponential backoff sabit dizi:** LibreTranslate retry [2, 4, 8] saniye — adaptif jitter yok
- **Pyparsing opsiyonel:** `pyparse_grammar.py` pyparsing yoksa çalışır ama daha az kapsamlıdır
- **Test coverage:** Unit/regresyon kapsamı güçlü; gerçek Ren'Py engine ile uçtan uca runtime integration testleri hâlâ sınırlı
- **rpymc_reader.py:** Nispeten yeni, kapsamı `rpyc_reader.py` kadar geniş değil

---

## 12. Hızlı Referans — Dosya Boyutları

| Dosya | Satır | Kritiklik |
|-------|-------|-----------|
| `parser.py` | 3731 | ★★★★★ |
| `translation_pipeline.py` | 3199 | ★★★★★ |
| `rpyc_reader.py` | 2686 | ★★★★ |
| `translator.py` | 2547 | ★★★★★ |
| `app_backend.py` | 1575 | ★★★★ |
| `syntax_guard.py` | 1497 | ★★★★★ |
| `output_formatter.py` | 1108 | ★★★★ |
| `cli_main.py` | 1112 | ★★★ |
| `SettingsPage.qml` | 924 | ★★★ |
| `ai_translator.py` | 862 | ★★★★ |
| `config.py` | 864 | ★★★★ |
| `settings_backend.py` | 808 | ★★★ |
| `HomePage.qml` | 775 | ★★★ |
| `deep_extraction.py` | 696 | ★★★★ |
| `tl_parser.py` | 690 | ★★★ |
