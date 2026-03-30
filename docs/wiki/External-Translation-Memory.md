# 🧠 External Translation Memory (TM)

> **Available since:** RenLocalizer v2.7.3  
> **Module:** `src/tools/external_tm.py`

---

## 📋 What is External TM?

**External Translation Memory** allows you to **reuse existing translations from one game in another game**. If you have already translated a Ren'Py game, you can import its `tl/<language>/` folder as a translation memory source. During future translations, RenLocalizer will first check the TM for an exact match before calling any translation API — **saving time and API costs**.

### Key Benefits
*   🚀 **Faster Translation:** Common UI strings ("Save", "Load", "Settings", "Return") are instantly matched.
*   💰 **Reduced API Costs:** Exact matches skip Google/DeepL/AI API calls entirely.
*   📊 **Consistency:** Translations from a proven, working game are reused consistently.
*   🔄 **Cumulative:** Import TM from multiple games — the memory grows over time.

---

## 🚀 Quick Start (v2.7.8+)

### Step 1: Navigate to Translation Reuse Center

1.  Open RenLocalizer and click on the **Çeviri Belleği / Cache** icon in the sidebar to open the **Translation Reuse Center**.
2.  Select the **"External TM"** tab at the top.

### Step 2: Import TM from Another Game

1.  In the **External TM** tab, click the **"📥 Import New Source"** button.
2.  A folder picker dialog appears — select the `tl/<language>/` folder from a **previously translated** Ren'Py game.
    *   Example: `C:\Games\MyOtherGame\game\tl\turkish`
3.  RenLocalizer will parse all `.rpy` translation files in that folder and extract original→translated pairs.
4.  The TM is saved as a JSON file under the `tm/` directory and will appear in the list.

### Step 3: Activate External TM

1.  At the top of the **External TM** tab, toggle the **"Activate External TM"** Switch to **ON**.
2.  Ensure the specific TM sources you want to use are **checked** in the list below the toggle.
3.  Go to the **Home** page and start your translation — TM matches will be applied automatically!

---

## ⚙️ How It Works (Pipeline Integration)

The External TM is integrated into **Stage 5 (TRANSLATING)** of the translation pipeline:

```
For each text to translate:
  │
  ├─ 1. Check External TM → Exact match found?
  │     ├─ YES → Use TM translation (no API call)
  │     └─ NO  → Continue to next step
  │
  ├─ 2. Check Translation Cache → Previously translated?
  │     ├─ YES → Use cached translation
  │     └─ NO  → Continue to next step
  │
  └─ 3. Call Translation API (Google / DeepL / AI / etc.)
```

**Important:** TM lookup happens **before** the translation cache and API calls. This means:
*   TM matches are the **fastest** path (pure dictionary lookup, zero latency).
*   The diagnostic report shows how many strings were matched via TM.

---

## 📂 Storage Format

TM files are stored in the `tm/` directory at the project root:

```
RenLocalizer/
├── tm/
│   ├── GameA_turkish.json
│   ├── GameB_turkish.json
│   └── GameC_spanish.json
```

### JSON Structure

```json
{
  "meta": {
    "source_name": "GameA",
    "language": "turkish",
    "entry_count": 8540,
    "created": "2026-03-08T14:30:00",
    "source_path": "C:/Games/GameA/game/tl/turkish"
  },
  "entries": {
    "Hello": "Merhaba",
    "Save": "Kaydet",
    "Load": "Yükle",
    "Are you sure?": "Emin misin?",
    "Chapter 1": "Bölüm 1"
  }
}
```

---

## 🛡️ Filtering & Quality Control

Not every string from a `tl/` folder should go into TM. RenLocalizer applies **6 filtering layers** to ensure only high-quality, meaningful translations are imported:

| Filter | What it catches | Example |
|--------|----------------|---------|
| **Empty translations** | Lines with no actual translation | `""` → skipped |
| **Same as original** | Untranslated lines (original == translated) | `"Save" → "Save"` → skipped |
| **Too short** | Single-character or meaningless strings | `"x"`, `"."` → skipped |
| **Technical strings** | Code identifiers, URLs, file paths | `"renpy.store"`, `"https://..."` → skipped |
| **Duplicate entries** | Already exists in the TM | Prevents bloat |
| **Hard limit** | Maximum 100,000 entries per TM file | Prevents memory issues |

### Technical Pattern Detection
The following patterns are automatically skipped:
*   `ALL_CAPS_IDENTIFIERS` (e.g., `SAVE_SLOT`, `MAIN_MENU`)
*   Dotted paths (e.g., `renpy.store.variable`)
*   URLs (e.g., `https://example.com`)
*   File extensions (e.g., `background.png`, `music.ogg`)
*   Strings containing only numbers/symbols

---

## 📊 Import Statistics

After importing, RenLocalizer shows a detailed summary:

| Metric | Description |
|--------|-------------|
| **Total Parsed** | Total original→translated pairs found in the tl/ folder |
| **Imported** | Successfully added to TM |
| **Skipped (Empty)** | No translation present |
| **Skipped (Same)** | Original = Translated |
| **Skipped (Short)** | Too short to be meaningful |
| **Skipped (Technical)** | Technical string filtered |
| **Skipped (Duplicate)** | Already in TM |

---

## 💡 Best Practices

### ✅ Do
*   **Import from similar games.** Visual novels in the same genre share a lot of common UI text and dialogue patterns.
*   **Import from multiple games.** Each new TM source increases your hit rate.
*   **Keep TM enabled** once imported — there is virtually no performance cost.
*   **Use with any engine.** TM works with Google, DeepL, AI engines, and even CLI mode.

### ❌ Don't
*   **Don't import from untested translations.** Bad translations in TM will propagate to new games.
*   **Don't import from a different target language.** Turkish TM should only be used when translating to Turkish.
*   **Don't manually edit TM JSON files** unless you know what you're doing (format is strict).

---

## 🔧 Troubleshooting

### "No translatable pairs found" after import
*   **Cause:** The selected folder might not be a valid `tl/<language>/` directory, or the `.rpy` files inside don't follow Ren'Py's translation block format.
*   **Solution:** Make sure you select the **language subfolder** (e.g., `tl/turkish/`), not the `tl/` folder itself. The folder should contain `.rpy` files with `translate turkish ...` blocks.

### TM toggle not found on Home page
*   **Cause:** As of v2.7.8, the External TM management has moved to a dedicated tab.
*   **Solution:** Go to **Çeviri Belleği / Cache** (Translation Reuse Center) and toggle **"Activate External TM"** ON in the **External TM** tab.

### Low hit rate (few TM matches)
*   **Cause:** The games use very different text. TM only works with **exact** matches.
*   **Solution:** Import TM from more games, especially ones with similar UI (Ren'Py default interface strings are often identical across games).

### Import is slow for large games
*   **Cause:** Parsing thousands of `.rpy` translation files takes time.
*   **Solution:** This is normal for games with 50,000+ lines. The progress indicator shows current status.

---

## 🏗️ Technical Details (For Developers)

### Module: `src/tools/external_tm.py`

| Class | Purpose |
|-------|---------|
| `ExternalTMStore` | Main TM engine: import, load, lookup |
| `TMImportResult` | Import operation result (dataclass) |
| `TMSource` | TM source metadata (dataclass) |

### Key Methods

```python
store = ExternalTMStore(tm_dir="tm")

# Import from a tl/ folder
result = store.import_from_tl_directory(
    tl_lang_dir="/path/to/game/tl/turkish",
    source_name="GameA",
    language="turkish",
    progress_callback=fn   # optional: fn(current, total, message)
)

# Load sources for lookup
store.load_sources(["tm/GameA_turkish.json", "tm/GameB_turkish.json"])

# Exact match lookup
translation = store.get_exact("Hello")  # → "Merhaba" or None

# Statistics
hits, misses = store.get_stats()
```

### Pipeline Integration Points
*   **`src/core/translation_pipeline.py`**: Loads TM sources at pipeline start, performs lookup before API calls.
*   **`src/backend/app_backend.py`**: 8 `@pyqtSlot` methods for QML↔Python bridge (import, list, delete, toggle).
*   **`src/utils/config.py`**: 4 config fields (`use_external_tm`, `external_tm_sources`, `external_tm_dir`, `external_tm_auto_apply`).

---

## 🔗 Related Pages
*   [[Performance-Optimization]] — TM reduces API calls and speeds up translation
*   [[Settings-UI-Reference]] — TM toggle in Settings
*   [[FAQ]] — Common TM questions
*   [[Developer-Guide]] — Contributing to TM module

---
*Last updated: March 2026 | RenLocalizer v2.7.8*
