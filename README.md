# RenLocalizer Lite: Visual Novel Localization Made Simple

<p align="center">
  <strong>Minimalist, Zero-Dependency Translation and Localization Toolkit for Ren'Py Games.</strong>
</p>

<p align="center">
  RenLocalizer Lite is a streamlined, single-page desktop application designed to translate Ren'Py games (.rpy, .rpyc, and tl/ directories) without breaking game code, formatting, or variables. 
</p>

<p align="center">
  <a href="https://github.com/Lord0fTurk/RenLocalizer/releases">Releases</a> |
  <a href="https://github.com/Lord0fTurk/RenLocalizer/wiki/LITE-RELEASE-GUIDE">Wiki & Wiki Guide</a> |
  <a href="CHANGELOG.md">Changelog</a>
</p>

<p align="center">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-2d6cdf">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-3776ab">
  <img alt="GUI" src="https://img.shields.io/badge/gui-PyQt6%20%2B%20QML-41cd52">
  <img alt="Build" src="https://img.shields.io/badge/build-Portable%20%2F%20Tak--Çalıştır-ff6b6b">
  <img alt="Version" src="https://img.shields.io/badge/version-2.8.6--LITE-111827">
  <img alt="License" src="https://img.shields.io/badge/license-GPL--3.0-blue">
</p>

---

## Why RenLocalizer Lite?

Visual Novel translations often fail because translation tools don't understand code. They accidentally translate variable names, corrupt formatting tags (`{i}`/`{b}`), or trigger duplicate translation key crashes. 

**RenLocalizer Lite solves this with zero hassle:**
*   **🔌 Zero Dependencies (Plug-and-Play):** All major machine translation and LLM submodules (including Google Translate, OpenAI, DeepSeek, and Local LLM support) are pre-bundled inside the application. No need to install Python or configure virtual environments.
*   **🎯 Minimalist UI:** Stripped of complex tabs and overwhelming settings. The single-page Material dashboard focuses strictly on: **Select Project -> Configure Engine -> Translate.**
*   **🛡️ Decoupled NMT & LLM Protection:** Google Translate is fed with custom Unicode brackets (`⟦N⟧`) which it preserves best, while LLMs (OpenAI/Local LLMs) receive structured XML tags (`<ph id="N">...</ph>`) to prevent subword tokenizer splitting and keep grammar markers contextually correct.

---

## Core Features

*   **Diverse Engines:** Translate via Google Translate (free, no API key), OpenAI (GPT models), DeepSeek API, or fully offline Local LLMs (Ollama / LM Studio).
*   **Smart TL Retranslation Mode:** Selecting an existing `tl/` folder automatically triggers a fallback retranslation mode. It preserves existing manual translations and only fills empty dialogue blocks (`new ""`).
*   **Technical Skipping & Filtering:** Over 200 pre-compiled regex guards prevent code parameters, font assignments, asset paths, and technical abbreviations from being translated.
*   **Compiled AST Reading:** Directly extracts and parses compiled bytecode `.rpyc` scripts when raw source `.rpy` files are missing.
*   **Structural Failsafes:** Captures broken/unclosed tags, edit-distance Levenshtein positioning alignment, and structural XML leakage checks to guarantee that the output compiles cleanly in Ren'Py.

---

## Quick Start (GUI Workflow)

1.  Download the latest packaged build from the [Releases page](https://github.com/Lord0fTurk/RenLocalizer/releases).
2.  Open **RenLocalizer**.
3.  Click **Browse** or **EXE** to select your game directory or executable.
4.  Choose your preferred **Translation Engine** and **Target Language**.
5.  Click **Translate** (▶) and watch the real-time logs.
6.  Launch your game and select the new language from the preferences menu!

---

## Running from Source

If you prefer executing from source:

```bash
git clone https://github.com/Lord0fTurk/RenLocalizer.git
cd RenLocalizer
python -m venv .venv
```

**Windows:**
```bash
.venv\Scripts\activate
pip install -r requirements.txt
python run_lite.py
```

**Linux / macOS:**
```bash
source .venv/bin/activate
pip install -r requirements.txt
python run_lite.py
```

---

## Technical Specifications

### GBNF Logit Schema Masking
For LLMs, the app passes strict schema constraints (`response_format` JSON schema). The API engine uses logit masking to enforce format matching, avoiding markdown code wrappers (` ```json `) or dropped item IDs.

### XML Corruption Checks
In the event that an LLM returns a corrupted translation or leaks XML tags, the pipeline performs a structural check:
*   If `<ph id=` or `</ph>` is found in the final restored translation, the string is flagged as a `placeholder_remnant` corruption, rejected, and safely reverted to the original source text to prevent game crashes.

---

## Contributing & Support

Issues, bug reports, and pull requests are welcome. Feel free to open a ticket on the GitHub Issues page.

*   [Wiki Guide](https://github.com/Lord0fTurk/RenLocalizer/wiki/LITE-RELEASE-GUIDE)
*   [Contributing Guidelines](CONTRIBUTING.md)
*   [License](LICENSE) (Licensed under the GPL-3.0 License)
