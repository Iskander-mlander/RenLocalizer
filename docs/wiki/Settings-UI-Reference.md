# ⚙️ Settings & UI Reference

This guide provides a comprehensive overview of the RenLocalizer **Settings** tab. The settings are organized into logical groups to help you fine-tune the translation process, manage performance, and secure your connectivity.

---

## 🌐 General Settings
Core application behavior and data management.

*   **App Language:** Switches the RenLocalizer interface between supported languages (EN, TR, DE, FR, etc.).
*   **Theme:** Choose between Light, Dark, or System themes.
*   **Check Updates:** Enables automatic version checks on startup via GitHub.

### 📁 Smart Data Path (v2.7.4)
*   **Portable Mode Toggle:** 
    *   *Enabled:* Stores `config.json`, `cache/`, and `tm/` next to the executable.
    *   *Disabled:* Stores data in OS-standard locations (`%APPDATA%` on Windows).
*   **Automatic Migration:** Switching modes will securely **move** (not copies) your existing data to the new location to prevent duplication.
*   **Open Data Folder:** Instantly opens the active data directory in File Explorer.

---

## 🔌 Translation Engines & APIs
Configure your preferred translation providers.

### **DeepL API**
*   **API Key:** Supports both Free and Pro keys.
*   **Formality:** Control the tone (Formal, Informal, or Default) for supported languages like German, French, or Spanish.

### **AI Engines (OpenAI / Gemini / Local LLM)**
*   **Presets:** Quick-fill settings for OpenRouter, DeepSeek, Ollama, or LM Studio.
*   **Base URL:** Allows connecting to OpenAI-compatible proxies or local servers.
*   **Safety Settings (Gemini):** Adjust the strictness of Google's safety filters.
*   **Local LLM Timeout:** Extended timeouts (default 120s) for slower local generation.

### **LibreTranslate**
*   **Server URL:** Endpoint for your self-hosted instance (e.g., `http://localhost:5000`).
*   **API Key:** Optional key for professional managed instances.

---

## 🔍 Translation Filters (What to Translate?)
Fine-grained control over which Ren'Py elements are extracted.

*   **Dialogues & Menus:** Core game narrative and player choices.
*   **Buttons & Notifications:** UI elements and popup messages.
*   **Style Strings:** Text defined within Ren'Py styles (v2.6+).
*   **Ren'Py Functions:** Advanced technical strings inside function calls.
*   **Character Names:** Enable to translate names (requires `Auto-Protect` to be OFF).
*   **Config/Define Strings:** Strings found in `config.*` or `define` statements.

---

## ⚡ Network & Performance
Optimize speed and manage network constraints.

*   **Batch Size:** Number of lines sent in one request. (Recommended: 10-30 for AI, 100+ for Google).
*   **Concurrent Threads:** Parallel requests. Increase for speed, decrease if getting `429 Too Many Requests`.
*   **Multi-Endpoint:** Rotates between multiple Google Translate mirrors to avoid IP blocks.
*   **Proxy Settings (v2.7.1):** 
    *   **Single Proxy:** Use a standard HTTP/SOCKS proxy.
    *   **Manual Proxies:** Provide a list of proxies (one per line) for automatic rotation and testing.

---

## 🧠 AI Tuning & Parameters
Advanced controls for Large Language Models.

*   **Creativity (Temperature):** 
    *   `0.3` (Deterministic): Better for technical accuracy.
    *   `0.7 - 1.0` (Creative): Better for natural-sounding dialogue.
*   **AI Batch Size:** Specifically controls how many lines are grouped in an AI prompt block (independent of the global batch size).
*   **Custom System Prompt:** Override the default AI instructions to enforce specific styles, genres, or rules.

---

## 🛠️ System & Technical
Internal mechanics and advanced workflow options.

*   **HTML Wrap Protection:** Uses `<span class="notranslate">` tags to protect code placeholders (Ideal for DeepL/AI).
*   **External Translation Memory (v2.7.8):** *Moved to Translation Reuse Center (Cache page)*. Manage and activate imported `.tm` files for pre-API lookup.
*   **Auto-Hook Generation:** Automatically produces the `_rl_hook.rpy` after translation.
*   **Automatic RPA Extraction:** Uses the internal UnRen/UnRPA engine to extract game assets before parsing.
*   **Custom Function Params:** A JSON field to define which custom Ren'py functions (e.g., `my_custom_notify("text")`) should be scanned for strings.

---

> [!TIP]
> **Pro Tip:** If you are translating a game with heavy technical code, use **HTML Wrap Protection** and Keep **Batch Size** lower for better placeholder integrity.
