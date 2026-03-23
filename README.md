# RenLocalizer

<p align="center">
  <strong>Advanced translation and localization toolkit for Ren'Py games.</strong>
</p>

<p align="center">
  Extracts translatable text from <code>.rpy</code>, <code>.rpyc</code>, and <code>.rpymc</code> files, translates it with multiple engines, and generates Ren'Py-friendly output with a desktop GUI and full CLI workflow.
</p>

<p align="center">
  <a href="https://github.com/Lord0fTurk/RenLocalizer/releases">Releases</a> |
  <a href="https://github.com/Lord0fTurk/RenLocalizer/wiki">Wiki</a> |
  <a href="docs/CLI_USAGE.md">CLI Usage</a> |
  <a href="CHANGELOG.md">Changelog</a>
</p>

<p align="center">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-2d6cdf">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-3776ab">
  <img alt="GUI" src="https://img.shields.io/badge/gui-PyQt6%20%2B%20QML-41cd52">
  <img alt="Version" src="https://img.shields.io/badge/version-2.7.6-111827">
  <img alt="License" src="https://img.shields.io/badge/license-GPL--3.0-blue">
</p>

## Why RenLocalizer?

RenLocalizer is built for a very specific problem: translating Ren'Py projects without breaking game logic.

It is not just a text replacer. It understands Ren'Py syntax, protects placeholders, supports compiled script formats, filters technical false positives, and can output both file-based translation scripts and runtime translation data.

If you work with visual novels, fan patches, private localization workflows, or AI-assisted translation pipelines, this project is designed to reduce manual cleanup while keeping output usable inside real games.

## What It Does

- Extracts text from `game/` projects, loose `.rpy` files, compiled `.rpyc`, and `.rpymc`.
- Supports Google, DeepL, OpenAI, Gemini, DeepSeek-compatible endpoints, Local LLMs, LibreTranslate, Yandex, and pseudo-localization.
- Preserves Ren'Py placeholders, tags, interpolation blocks, and syntax-sensitive fragments.
- Generates Ren'Py-compatible `tl/<language>/` output, `strings.json`, and runtime hook files.
- Includes deep extraction for hidden strings inside `init python`, data structures, and non-standard patterns.
- Reuses prior work with cache, glossary, and external translation memory support.
- Runs through both a desktop UI and a headless CLI.

## Core Highlights

### Safe Ren'Py-aware translation

RenLocalizer protects:

- interpolation variables like `[player_name]`
- Ren'Py text tags like `{b}` and `{color=#fff}`
- technical strings that should never be translated
- delimited variant text such as `A|B|C` and `<A|B|C>`

This is handled through a dedicated syntax guard, output filtering, and integrity validation pipeline instead of relying on a single regex pass.

### Multiple translation engines

| Engine | Type | Notes |
| --- | --- | --- |
| Google Translate | Web/API-style | Fast, fallback-heavy, multi-endpoint |
| DeepL | API | Strong quality, formality support |
| OpenAI | LLM | XML-protected AI flow |
| Gemini | LLM | Safety controls and batch prompts |
| DeepSeek-compatible | LLM/API | OpenAI-style endpoint support |
| Local LLM | Offline | Ollama, LM Studio, OpenAI-compatible servers |
| LibreTranslate | Self-hosted/API | Useful for local or privacy-focused setups |
| Yandex | Web-based | Extra free-engine option |
| Pseudo | Debug/testing | UI overflow and localization testing |

### Deep extraction and compiled-script support

The parser stack goes beyond ordinary `.rpy` dialogue lines.

- Reads compiled `.rpyc` directly when sources are missing.
- Scans `.rpymc` content.
- Performs deep AST-based extraction inside Python blocks.
- Parses existing `tl/` files and translation folders.
- Supports structured data extraction from formats like JSON and YAML.

### GUI and CLI in the same project

The GUI is built with PyQt6 + QML for day-to-day usage, while the CLI uses the same core pipeline for automation, batch processing, and server workflows.

That shared architecture matters: fixes in extraction, translation safety, and output generation benefit both interfaces.

## Project Architecture

```text
QML UI
  -> AppBackend / SettingsBackend
  -> TranslationPipeline
  -> Parser / RPYC Reader / Deep Extraction
  -> Translators / Syntax Guard / Output Formatter
  -> Exported tl/<lang>/ files + strings.json + runtime hook
```

Main entry points:

- `run.py` -> GUI launcher
- `run_cli.py` -> CLI launcher
- `src/core/translation_pipeline.py` -> orchestration layer
- `src/core/parser.py` -> extraction engine
- `src/core/translator.py` and `src/core/ai_translator.py` -> translation engines

## Installation

### Windows

Download the latest packaged build from the [Releases page](https://github.com/Lord0fTurk/RenLocalizer/releases).

- `RenLocalizer.exe` -> GUI
- `RenLocalizerCLI.exe` -> CLI

### Run from source

```bash
git clone https://github.com/Lord0fTurk/RenLocalizer.git
cd RenLocalizer
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
# flexible source install
pip install -r requirements.txt

# optional: match the exact packaged-build Qt stack
# pip install -c constraints-release.txt -r requirements.txt
python run.py
```

Linux / macOS:

```bash
source .venv/bin/activate
# flexible source install (CI-smoke-tested across PyQt6 6.6-6.10 on Linux)
pip install -r requirements.txt

# optional: match the exact packaged-build Qt stack
# pip install -c constraints-release.txt -r requirements.txt
python run.py
```

CLI launch:

```bash
python run_cli.py
```

## Quick Start

### GUI workflow

1. Open RenLocalizer.
2. Select a game folder or executable.
3. Choose source language, target language, and engine.
4. Enable optional deep scan / compiled script support if needed.
5. Start translation.
6. Review generated files under `game/tl/<language>/`.

### CLI workflow

Interactive mode:

```bash
python run_cli.py
```

Direct command examples:

```bash
python run_cli.py "C:\Games\MyRenPyGame" --target-lang tr --engine google --mode full
python run_cli.py "/path/to/game" --target-lang es --engine local_llm --mode translate
python run_cli.py "/path/to/game" --target-lang ru --engine gemini --deep-scan
```

## Output Format

RenLocalizer can generate:

- file-based `tl/<language>/*.rpy` translation files
- `strings.json` for runtime lookups
- runtime hook scripts for in-game forced translation scenarios

This makes it usable for both conventional Ren'Py localization and more aggressive runtime-assisted patching.

## Configuration

The main configuration lives in `config.json`.

Major configuration groups:

- `translation_settings`
- `api_keys`
- `app_settings`
- `proxy_settings`

Available controls include:

- engine and model selection
- AI timeout, retries, concurrency, batch size
- glossary and critical-term files
- translation type filters
- deep extraction toggles
- runtime hook generation
- proxy configuration
- external translation memory sources

## Documentation

If you want detailed usage or internal behavior, start here:

- [Wiki Home](https://github.com/Lord0fTurk/RenLocalizer/wiki)
- [CLI Usage](docs/CLI_USAGE.md)
- [Details](docs/DETAILS.md)
- [Advanced Parsing](docs/wiki/Advanced-Parsing.md)
- [AI Engines](docs/wiki/AI-Engines.md)
- [External Translation Memory](docs/wiki/External-Translation-Memory.md)
- [Technical Filtering](docs/wiki/Technical-Filtering.md)
- [Developer Guide](docs/wiki/Developer-Guide.md)

## Who This Is For

RenLocalizer is especially useful for:

- fan translators working on Ren'Py games
- developers localizing their own VN projects
- teams mixing MT + LLM + manual QA workflows
- users who need offline local-LLM translation
- projects where placeholder safety matters more than raw speed

## Current Status

- Active version: `2.7.6`
- Desktop GUI: supported
- CLI: supported
- Windows / Linux / macOS: supported
- Test suite: large multi-file regression coverage

Recent work includes stronger output safety, external translation memory, deeper extraction coverage, better packaging, and Windows HiDPI black-screen hardening for Qt Quick startup.

## Contributing

Issues, bug reports, and pull requests are welcome.

Useful links:

- [Contributing Guide](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Changelog](CHANGELOG.md)

When reporting a bug, include:

- operating system
- Python version or packaged build version
- translation engine
- whether the issue happens in GUI, CLI, or both
- a minimal sample file if possible

## License

RenLocalizer is licensed under the [GPL-3.0 License](LICENSE).
