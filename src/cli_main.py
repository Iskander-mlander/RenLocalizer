# -*- coding: utf-8 -*-
"""
RenLocalizer CLI Main Module
Modern terminal interface powered by Rich
"""

import sys
import os
import argparse
import signal
import json
import logging
import time
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QCoreApplication, QObject, pyqtSlot

from src.utils.config import ConfigManager
from src.core.translation_pipeline import TranslationPipeline, PipelineResult, PipelineStage
from src.core.translator import TranslationManager, TranslationEngine, PseudoTranslator
from src.core.proxy_manager import ProxyManager
from src.version import VERSION

# Rich Library
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn, TaskProgressColumn, MofNCompleteColumn
    from rich.columns import Columns
    from rich.align import Align
    from rich.rule import Rule
    from rich import box
    from rich.traceback import install as install_rich_traceback
    install_rich_traceback(show_locals=False, width=100)
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# UTF-8 stdout
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

if RICH_AVAILABLE:
    console = Console(highlight=False)
else:
    class _FallbackConsole:
        def print(self, *args, **kwargs):
            text = ' '.join(str(a) for a in args)
            print(text)
        def rule(self, title="", **kwargs):
            print(f"\n{'─' * 20} {title} {'─' * 20}")
        def input(self, prompt=""):
            return input(prompt)
    console = _FallbackConsole()

# Theme
BRAND_PRIMARY = "bright_magenta"
BRAND_SECONDARY = "bright_cyan"
BRAND_ACCENT = "bright_yellow"
BRAND_SUCCESS = "bright_green"
BRAND_ERROR = "bright_red"
BRAND_WARNING = "yellow"
BRAND_DIM = "dim white"

ENGINES = [
    ("google",         "Google Translate",  "🌐", "Free — 13 mirror fallback"),
    ("openai",         "OpenAI (GPT)",      "🤖", "API key required"),
    ("deepseek",       "DeepSeek",          "🔮", "API key required — OpenAI compatible"),
    ("local_llm",      "Local LLM",         "🏠", "Ollama / LM Studio — fully local"),
    ("libretranslate", "LibreTranslate",    "🔓", "Self-hosted — Docker/Local"),
    ("custom",         "Custom Endpoint",   "🔗", "Any LibreTranslate-compatible API"),
]

LANGUAGES = [
    ("tr", "Turkish",    "🇹🇷"),
    ("en", "English",    "🇬🇧"),
    ("fr", "French",     "🇫🇷"),
    ("de", "German",     "🇩🇪"),
    ("es", "Spanish",    "🇪🇸"),
    ("ru", "Russian",    "🇷🇺"),
    ("ja", "Japanese",   "🇯🇵"),
    ("ko", "Korean",     "🇰🇷"),
    ("zh", "Chinese",    "🇨🇳"),
    ("pt", "Portuguese", "🇵🇹"),
    ("ar", "Arabic",     "🇸🇦"),
    ("it", "Italian",    "🇮🇹"),
    ("fa", "Persian",    "🇮🇷"),
]

ENGINE_MAP = {
    "google": TranslationEngine.GOOGLE,
    "openai": TranslationEngine.OPENAI,
    "deepseek": TranslationEngine.OPENAI,
    "local_llm": TranslationEngine.LOCAL_LLM,
    "libretranslate": TranslationEngine.LIBRETRANSLATE,
    "custom": TranslationEngine.CUSTOM,
}


# ============================================================
# UI Helpers
# ============================================================

def print_banner():
    if not RICH_AVAILABLE:
        print(f"\n{'=' * 60}")
        print(f"       RenLocalizer CLI v{VERSION}")
        print(f"       Ren'Py Game Translation Tool")
        print(f"{'=' * 60}")
        return

    banner_lines = [
        "╔═══════════════════════════════════════════════════╗",
        "║                                                   ║",
        "║   ██████╗ ███████╗███╗   ██╗                      ║",
        "║   ██╔══██╗██╔════╝████╗  ██║                      ║",
        "║   ██████╔╝█████╗  ██╔██╗ ██║                      ║",
        "║   ██╔══██╗██╔══╝  ██║╚██╗██║                      ║",
        "║   ██║  ██║███████╗██║ ╚████║  LOCALIZER           ║",
        "║   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝                     ║",
        "║                                                   ║",
        f"║   CLI v{VERSION:<10s}  Ren'Py Translation Tool     ║",
        "║                                                   ║",
        "╚═══════════════════════════════════════════════════╝",
    ]

    gradient_colors = [
        "rgb(180,80,255)", "rgb(160,90,255)", "rgb(140,100,255)",
        "rgb(120,120,255)", "rgb(100,140,255)", "rgb(80,160,255)",
        "rgb(60,180,255)", "rgb(80,200,240)", "rgb(100,220,220)",
        "rgb(120,240,200)", "rgb(100,220,220)", "rgb(80,200,240)",
    ]

    text = Text()
    for i, line in enumerate(banner_lines):
        color = gradient_colors[i % len(gradient_colors)]
        text.append(line + "\n", style=color)
    console.print(Align.center(text))


def print_section_header(title: str, icon: str = ""):
    if RICH_AVAILABLE:
        label = f"{icon}  {title}" if icon else title
        console.print()
        console.rule(f"[bold {BRAND_PRIMARY}]{label}[/]", style=BRAND_DIM)
        console.print()
    else:
        print(f"\n{'─' * 20} {icon} {title} {'─' * 20}\n")


def print_key_value(key: str, value: str, icon: str = ""):
    prefix = f"{icon} " if icon else "  "
    if RICH_AVAILABLE:
        console.print(f"  {prefix}[{BRAND_DIM}]{key}:[/]  [{BRAND_SECONDARY}]{value}[/]")
    else:
        print(f"  {prefix}{key}: {value}")


def print_success(message: str):
    if RICH_AVAILABLE:
        console.print(f"  [bold {BRAND_SUCCESS}]✅ {message}[/]")
    else:
        print(f"  ✅ {message}")


def print_error(message: str):
    if RICH_AVAILABLE:
        console.print(f"  [bold {BRAND_ERROR}]❌ {message}[/]")
    else:
        print(f"  ❌ {message}")


def print_warning(message: str):
    if RICH_AVAILABLE:
        console.print(f"  [{BRAND_WARNING}]⚠  {message}[/]")
    else:
        print(f"  ⚠ {message}")


def print_info(message: str):
    if RICH_AVAILABLE:
        console.print(f"  [{BRAND_SECONDARY}]ℹ  {message}[/]")
    else:
        print(f"  ℹ {message}")


def get_user_input(prompt: str, default: str = "") -> str:
    if default:
        if RICH_AVAILABLE:
            result = console.input(f"  [{BRAND_PRIMARY}]❯[/] {prompt} [{BRAND_DIM}][{default}][/]: ").strip()
        else:
            result = input(f"  ❯ {prompt} [{default}]: ").strip()
        return result if result else default
    else:
        if RICH_AVAILABLE:
            return console.input(f"  [{BRAND_PRIMARY}]❯[/] {prompt}: ").strip()
        else:
            return input(f"  ❯ {prompt}: ").strip()


def print_menu(title: str, options: list, show_back: bool = True, icons: list = None) -> int:
    if RICH_AVAILABLE:
        console.print(f"\n  [bold {BRAND_PRIMARY}]{title}[/]")
        console.print(f"  [dim]{'─' * 44}[/]")
        for i, option in enumerate(options, 1):
            icon = icons[i-1] if icons and i-1 < len(icons) else "•"
            console.print(f"    [{BRAND_ACCENT}][{i}][/]  {icon}  {option}")
        if show_back:
            console.print(f"    [{BRAND_DIM}][0]  ←  Back[/]")
        console.print()
    else:
        print(f"\n  {title}")
        print(f"  {'─' * 44}")
        for i, option in enumerate(options, 1):
            print(f"    [{i}] {option}")
        if show_back:
            print(f"    [0] Back")
        print()

    while True:
        try:
            choice = get_user_input("Your choice")
            if choice == '0' and show_back:
                return 0
            num = int(choice)
            if 1 <= num <= len(options):
                return num
            print_warning("Invalid choice — please try again")
        except ValueError:
            print_warning("Please enter a number")


def build_summary_panel(data: dict, title: str = "Summary") -> None:
    if RICH_AVAILABLE:
        table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2), expand=False)
        table.add_column("Key", style=BRAND_DIM, min_width=18)
        table.add_column("Value", style=f"bold {BRAND_SECONDARY}")
        for key, value in data.items():
            table.add_row(key, str(value))
        panel = Panel(table, title=f"[bold {BRAND_PRIMARY}]{title}[/]", border_style=BRAND_DIM, padding=(1, 2))
        console.print(panel)
    else:
        print(f"\n  {title}")
        print(f"  {'─' * 40}")
        for key, value in data.items():
            print(f"    {key:<18s} {value}")
        print()


def clear_screen():
    if RICH_AVAILABLE:
        console.clear()
    else:
        os.system('cls' if os.name == 'nt' else 'clear')


# ============================================================
# CliHandler — Pipeline Signal Receiver
# ============================================================

class CliHandler(QObject):
    def __init__(self, pipeline: TranslationPipeline, verbose: bool = False):
        super().__init__()
        self.pipeline = pipeline
        self.verbose = verbose
        self._progress = None
        self._progress_task = None
        self._start_time = time.time()

        self.pipeline.stage_changed.connect(self.on_stage_changed)
        self.pipeline.progress_updated.connect(self.on_progress_updated)
        self.pipeline.log_message.connect(self.on_log_message)
        self.pipeline.finished.connect(self.on_finished)
        self.pipeline.show_warning.connect(self.on_warning)

    @pyqtSlot(str, str)
    def on_stage_changed(self, stage: str, message: str):
        if self._progress is not None:
            try: self._progress.stop()
            except Exception: pass
            self._progress = None
            self._progress_task = None

        if RICH_AVAILABLE:
            console.print()
            console.rule(f"[bold {BRAND_ACCENT}]⚡ {message}[/]", style=BRAND_DIM)
        else:
            print(f"\n>> STAGE: {message}")

    @pyqtSlot(int, int, str)
    def on_progress_updated(self, current: int, total: int, text: str):
        if total <= 0:
            return
        if RICH_AVAILABLE:
            if self._progress is None:
                self._progress = Progress(
                    SpinnerColumn("dots", style=BRAND_PRIMARY),
                    TextColumn("[bold]{task.description}[/]", justify="left"),
                    BarColumn(bar_width=30, style=BRAND_DIM, complete_style=BRAND_PRIMARY, finished_style=BRAND_SUCCESS),
                    MofNCompleteColumn(), TaskProgressColumn(), TimeRemainingColumn(),
                    console=console, transient=False,
                )
                self._progress.start()
                self._progress_task = self._progress.add_task(text[:60], total=total, completed=current)
            else:
                self._progress.update(self._progress_task, completed=current, total=total, description=text[:60])
        else:
            pct = int((current / total) * 100) if total > 0 else 0
            sys.stdout.write(f"\rProgress: [{current}/{total}] {pct}%")
            sys.stdout.flush()

    @pyqtSlot(str, str)
    def on_log_message(self, level: str, message: str):
        if not self.verbose and level in ("info", "debug"):
            return
        if RICH_AVAILABLE:
            level_styles = {"info": (BRAND_DIM, "ℹ"), "success": (BRAND_SUCCESS, "✅"),
                            "warning": (BRAND_WARNING, "⚠"), "error": (BRAND_ERROR, "❌")}
            style, icon = level_styles.get(level, (BRAND_DIM, "•"))
            console.print(f"  [{style}]{icon} {message}[/]")
        else:
            print(f"\n[{level.upper()}] {message}")

    @pyqtSlot(str, str)
    def on_warning(self, title: str, message: str):
        if RICH_AVAILABLE:
            console.print(Panel(f"[{BRAND_WARNING}]{message}[/]", title=f"[bold {BRAND_WARNING}]⚠ {title}[/]",
                                border_style=BRAND_WARNING, padding=(0, 2)))
        else:
            print(f"\n[WARNING] {title}: {message}")

    @pyqtSlot(object)
    def on_finished(self, result: PipelineResult):
        if self._progress is not None:
            try: self._progress.stop()
            except Exception: pass
            self._progress = None

        elapsed = time.time() - self._start_time
        elapsed_str = f"{elapsed:.1f}s" if elapsed < 60 else f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
        console.print()

        if result.success:
            if RICH_AVAILABLE:
                result_table = Table(show_header=False, box=box.ROUNDED, padding=(0, 2))
                result_table.add_column("", style=BRAND_DIM, min_width=16)
                result_table.add_column("", style=f"bold {BRAND_SECONDARY}")
                if result.stats:
                    result_table.add_row("Total items", str(result.stats.get('total', 0)))
                    result_table.add_row("Translated", str(result.stats.get('translated', 0)))
                    result_table.add_row("Untranslated", str(result.stats.get('untranslated', 0)))
                result_table.add_row("Duration", elapsed_str)
                panel = Panel(result_table, title=f"[bold {BRAND_SUCCESS}]✅ Translation Complete[/]",
                              subtitle=f"[{BRAND_DIM}]{result.message}[/]", border_style=BRAND_SUCCESS, padding=(1, 2))
                console.print(panel)
            else:
                print(f"\n{'=' * 60}\nSUCCESS\n{result.message}\nDuration: {elapsed_str}\n{'=' * 60}")
        else:
            if RICH_AVAILABLE:
                panel = Panel(f"[bold]{result.message}[/]",
                              title=f"[bold {BRAND_ERROR}]❌ Translation Failed[/]",
                              border_style=BRAND_ERROR, padding=(1, 2))
                console.print(panel)
            else:
                print(f"\n{'=' * 60}\nFAILED\n{result.message}\n{'=' * 60}")

        QCoreApplication.quit()


# ============================================================
# Config & Engine Setup
# ============================================================

def load_config_override(config_path: str) -> dict:
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print_error(f"Loading config file: {e}")
        return {}


def setup_engines(config: ConfigManager, engine_id: str, lt_url: str = "", lt_key: str = ""):
    """Setup translation engines (Google always as fallback)."""
    proxy_manager = ProxyManager()
    proxy_manager.configure_from_settings(config.proxy_settings)
    translation_manager = TranslationManager(proxy_manager, config)

    from src.core.translator import GoogleTranslator
    google = GoogleTranslator(proxy_manager=proxy_manager, config_manager=config)
    translation_manager.add_translator(TranslationEngine.GOOGLE, google)

    engine = ENGINE_MAP.get(engine_id, TranslationEngine.GOOGLE)
    if engine == TranslationEngine.GOOGLE:
        return config, translation_manager

    try:
        if engine in (TranslationEngine.OPENAI, TranslationEngine.LOCAL_LLM):
            from src.core.ai_translator import OpenAITranslator, LocalLLMTranslator
            if engine == TranslationEngine.OPENAI:
                t = OpenAITranslator(proxy_manager=proxy_manager, config_manager=config)
                translation_manager.add_translator(TranslationEngine.OPENAI, t)
            else:
                t = LocalLLMTranslator(proxy_manager=proxy_manager, config_manager=config)
                translation_manager.add_translator(TranslationEngine.LOCAL_LLM, t)
        elif engine in (TranslationEngine.LIBRETRANSLATE, TranslationEngine.CUSTOM):
            from src.core.translator import LibreTranslateTranslator
            base_url = lt_url or getattr(config.translation_settings, "libretranslate_url", "http://localhost:5000")
            api_key = lt_key or getattr(config.translation_settings, "libretranslate_api_key", "")
            t = LibreTranslateTranslator(base_url=base_url, api_key=api_key,
                                         proxy_manager=proxy_manager, config_manager=config)
            translation_manager.add_translator(engine, t)
    except Exception as e:
        print_warning(f"Engine {engine_id} setup failed, using Google fallback: {e}")

    return config, translation_manager


# ============================================================
# Translate Command
# ============================================================

def run_translate_command(args) -> int:
    """Run translation pipeline."""
    print_banner()

    input_path = os.path.abspath(args.input_path) if args.input_path else None
    if not input_path or not os.path.exists(input_path):
        print_error(f"Path not found: {input_path}")
        return 1

    config = ConfigManager()
    if args.config and os.path.exists(args.config):
        override = load_config_override(args.config)
        for section, values in override.items():
            if hasattr(config, section):
                for key, val in values.items():
                    setattr(getattr(config, section), key, val)

    config.translation_settings.target_language = args.target_lang
    config.translation_settings.source_language = args.source_lang
    config.translation_settings.selected_engine = args.engine
    if getattr(args, 'deep_scan', False):
        config.translation_settings.enable_deep_scan = True

    print_section_header("Translation Settings", "⚙")
    print_key_value("Input", input_path, "📁")
    print_key_value("Engine", args.engine, "⚡")
    print_key_value("Source", args.source_lang, "🌍")
    print_key_value("Target", args.target_lang, "🌍")
    if getattr(args, 'deep_scan', False):
        print_key_value("Deep scan", "enabled", "🔍")

    lt_url = getattr(args, 'lt_url', '')
    lt_key = getattr(args, 'lt_key', '')
    if args.engine in ("libretranslate", "custom"):
        print_key_value("Endpoint", lt_url or "http://localhost:5000", "🔗")

    config, translation_manager = setup_engines(config, args.engine, lt_url, lt_key)

    print_section_header("Running Translation", "🚀")
    console.print()

    engine = ENGINE_MAP.get(args.engine, TranslationEngine.GOOGLE)
    pipeline = TranslationPipeline(config, translation_manager)
    handler = CliHandler(pipeline, verbose=args.verbose)
    pipeline.configure(
        game_exe_path=input_path, target_language=args.target_lang, source_language=args.source_lang,
        engine=engine, auto_unren=False, use_proxy=False,
        include_deep_scan=getattr(args, 'deep_scan', False),
        include_rpyc=False,
    )

    from src.core.translation_pipeline import PipelineWorker
    worker = PipelineWorker(pipeline)
    worker.start()

    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    return app.exec()


# ============================================================
# Interactive Mode
# ============================================================

def select_engine() -> str:
    options, icons = [], []
    for code, name, icon, desc in ENGINES:
        if RICH_AVAILABLE:
            options.append(f"{name}  [{BRAND_DIM}]{desc}[/]")
        else:
            options.append(f"{name} — {desc}")
        icons.append(icon)
    choice = print_menu("Select Translation Engine", options, show_back=True, icons=icons)
    if choice == 0: return ""
    return ENGINES[choice - 1][0]


def select_language(title: str = "Select Target Language") -> str:
    options, icons = [], []
    for code, name, icon in LANGUAGES:
        options.append(f"{name} ({code})")
        icons.append(icon)
    options.append("Other (enter manually)")
    icons.append("⌨")
    choice = print_menu(title, options, show_back=True, icons=icons)
    if choice == 0: return ""
    if choice <= len(LANGUAGES): return LANGUAGES[choice - 1][0]
    return get_user_input("Language code", "tr")


def select_source_language() -> str:
    """Source language selection with auto-detect as default."""
    options = ["Auto-detect (recommended)"]
    icons = ["🤖"]
    for code, name, icon in LANGUAGES:
        options.append(f"{name} ({code})")
        icons.append(icon)
    options.append("Other (enter manually)")
    icons.append("⌨")
    choice = print_menu("Select Source Language", options, show_back=True, icons=icons)
    if choice == 0: return ""
    if choice == 1: return "auto"
    if choice - 2 < len(LANGUAGES): return LANGUAGES[choice - 2][0]
    return get_user_input("Source language code", "auto")


def interactive_mode() -> dict:
    """Run interactive setup wizard with Rich UI."""
    config = {'input_path': '', 'target_lang': 'tr', 'source_lang': 'auto',
              'engine': 'google', 'verbose': False, 'deep_scan': False}

    clear_screen()
    print_banner()

    while True:
        choice = print_menu("MAIN MENU", [
            "Full Translation (Game EXE/Project)",
            "Translate Existing TL Folder",
            "Settings", "Help", "Exit"
        ], show_back=False, icons=["🎮", "📁", "⚙", "❓", "👋"])

        if choice == 1:
            print_section_header("STEP 1 — File/Folder Selection", "📂")
            path = get_user_input("Path")
            if not path: print_warning("Path cannot be empty"); continue
            if not os.path.exists(path): print_error(f"File/folder not found: {path}"); continue
            config['input_path'] = os.path.abspath(path)

            print_section_header("STEP 2 — Target Language", "🌍")
            lang = select_language("Select Target Language")
            if not lang: continue
            config['target_lang'] = lang

            print_section_header("STEP 2b — Source Language", "🌐")
            src = select_source_language()
            if src:
                config['source_lang'] = src
            else:
                continue

            print_section_header("STEP 3 — Translation Engine", "⚡")
            engine = select_engine()
            if not engine: continue
            config['engine'] = engine

            clear_screen(); print_banner()
            build_summary_panel({
                "Path": config['input_path'], "Target": config['target_lang'],
                "Source": config['source_lang'], "Engine": config['engine'],
                "Deep scan": "On" if config['deep_scan'] else "Off",
            }, title="📋 Translation Summary")

            confirm = get_user_input("Start translation? (y/n)", "y")
            if confirm.lower() in ('y', 'yes'): return config

        elif choice == 2:
            print_section_header("TRANSLATE EXISTING TL FOLDER", "📁")
            path = get_user_input("TL Folder Path")
            if not path: print_warning("Path cannot be empty"); continue
            if not os.path.exists(path): print_error(f"Folder not found: {path}"); continue
            config['input_path'] = os.path.abspath(path)

            lang = select_language("Select Target Language")
            if not lang: continue
            config['target_lang'] = lang

            src = select_source_language()
            if src:
                config['source_lang'] = src
            else:
                continue

            engine = select_engine()
            if not engine: continue
            config['engine'] = engine

            clear_screen(); print_banner()
            build_summary_panel({
                "TL Folder": config['input_path'], "Target": config['target_lang'],
                "Source": config['source_lang'], "Engine": config['engine'],
            }, title="📋 Translation Summary")

            confirm = get_user_input("Start translation? (y/n)", "y")
            if confirm.lower() in ('y', 'yes'): return config

        elif choice == 3:
            while True:
                opts = [
                    f"Source Language  [{BRAND_SECONDARY}]{config['source_lang']}[/]" if RICH_AVAILABLE else f"Source: {config['source_lang']}",
                    f"Translation Engine  [{BRAND_SECONDARY}]{config['engine']}[/]" if RICH_AVAILABLE else f"Engine: {config['engine']}",
                    f"Deep scan  [{BRAND_SUCCESS if config['deep_scan'] else BRAND_ERROR}]{'On' if config['deep_scan'] else 'Off'}[/]" if RICH_AVAILABLE else f"Deep scan: {'On' if config['deep_scan'] else 'Off'}",
                    f"Verbose Logging  {f'[{BRAND_SUCCESS}]On[/]' if config['verbose'] else f'[{BRAND_ERROR}]Off[/]'}" if RICH_AVAILABLE else f"Verbose: {'On' if config['verbose'] else 'Off'}",
                ]
                c = print_menu("⚙  SETTINGS", opts, icons=["🌐", "⚡", "🔍", "📝"])
                if c == 0: break
                elif c == 1: config['source_lang'] = get_user_input("Source language code", config['source_lang'])
                elif c == 2: engine = select_engine(); config['engine'] = engine if engine else config['engine']
                elif c == 3: config['deep_scan'] = not config['deep_scan']; print_info(f"Deep scan {'enabled' if config['deep_scan'] else 'disabled'}")
                elif c == 4: config['verbose'] = not config['verbose']; print_info(f"Verbose {'enabled' if config['verbose'] else 'disabled'}")

        elif choice == 4:
            clear_screen(); print_banner()
            if RICH_AVAILABLE:
                help_text = (
                    f"[bold {BRAND_PRIMARY}]RenLocalizer[/] automatically translates Ren'Py visual novels.\n\n"
                    f"[bold {BRAND_ACCENT}]ENGINES[/]\n"
                    f"  [bold]Google Translate[/] — Fast, free, 13 mirrors\n"
                    f"  [bold]OpenAI / DeepSeek[/] — API key required, best quality\n"
                    f"  [bold]Local LLM[/] — Ollama / LM Studio, fully offline\n"
                    f"  [bold]LibreTranslate / Custom[/] — Self-hosted translation servers\n\n"
                    f"[bold {BRAND_ACCENT}]COMMAND LINE[/]\n"
                    f"  [dim]$[/] python run_cli.py \"C:\\Games\\MyVN.exe\"\n"
                    f"  [dim]$[/] python run_cli.py \"C:\\Games\\MyVN.exe\" -e libretranslate -t en\n"
                    f"  [dim]$[/] python run_cli.py --interactive\n"
                    f"  [dim]$[/] python run_cli.py --version\n"
                )
                console.print(Panel(help_text, title=f"[bold {BRAND_PRIMARY}]❓ Help[/]", border_style=BRAND_DIM, padding=(1, 2)))
            else:
                print("""
  HELP ───────────────────────────────────
  RenLocalizer CLI translates Ren'Py games.
  
  ENGINES: Google, OpenAI, DeepSeek, Local LLM, LibreTranslate, Custom
  
  USAGE:
    python run_cli.py <path>
    python run_cli.py <path> -e libretranslate -t en
    python run_cli.py --interactive
  ─────────────────────────────────────────""")
            console.input(f"\n  [{BRAND_DIM}]Press Enter to continue...[/]" if RICH_AVAILABLE else "\n  Press Enter...")

        elif choice == 5:
            if RICH_AVAILABLE: console.print(f"\n  [{BRAND_DIM}]Goodbye! 👋[/]\n")
            else: print("\n  Goodbye!\n")
            sys.exit(0)

    return config


# ============================================================
# Main Entry Point
# ============================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description=f"RenLocalizer CLI v{VERSION} — Ren'Py Game Translation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # TRANSLATE
    t = subparsers.add_parser('translate', help='Translate a game or project')
    t.add_argument("input_path", nargs='?', default=None, help="Path to game executable, project directory, or TL folder")
    t.add_argument("--config", help="Path to JSON configuration file")
    t.add_argument("--target-lang", "-t", default="tr", help="Target language code (default: tr)")
    t.add_argument("--source-lang", "-s", default="auto", help="Source language code (default: auto)")
    t.add_argument("--engine", "-e", default="google", choices=[e[0] for e in ENGINES], help="Translation engine")
    t.add_argument("--lt-url", default="", help="LibreTranslate/Custom endpoint URL")
    t.add_argument("--lt-key", default="", help="LibreTranslate/Custom API key")
    t.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    t.add_argument("--interactive", "-i", action="store_true", help="Run in interactive menu mode")
    t.add_argument("--deep-scan", "-d", action="store_true", help="Enable deep scanning")

    # PSEUDO
    p = subparsers.add_parser('pseudo', help='Generate pseudo-localized text for UI testing')
    p.add_argument("input_path", help="Path to game directory or tl folder")
    p.add_argument("--mode", choices=["expand", "accent", "both"], default="both", help="Pseudo mode")
    p.add_argument("--output", "-o", help="Output directory")

    # Legacy direct mode
    parser.add_argument("legacy_input_path", nargs='?', default=None, metavar='input_path',
                        help="Path to game executable, project directory, or translation file")
    parser.add_argument("--config", help="Path to JSON configuration file")
    parser.add_argument("--target-lang", "-t", default="tr", help="Target language code")
    parser.add_argument("--source-lang", "-s", default="auto", help="Source language code")
    parser.add_argument("--engine", "-e", default="google", choices=[e[0] for e in ENGINES], help="Translation engine")
    parser.add_argument("--lt-url", default="", help="LibreTranslate/Custom endpoint URL")
    parser.add_argument("--lt-key", default="", help="LibreTranslate/Custom API key")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive menu mode")
    parser.add_argument("--deep-scan", "-d", action="store_true", help="Enable deep scanning")
    parser.add_argument("--version", action="version", version=f"RenLocalizer CLI v{VERSION}")

    args = parser.parse_args()

    # Normalize legacy mode
    if args.command is None and hasattr(args, 'legacy_input_path') and args.legacy_input_path:
        args.input_path = args.legacy_input_path

    # Interactive mode
    if getattr(args, 'interactive', False) or (args.command is None and not args.legacy_input_path):
        config = interactive_mode()
        if config['input_path']:
            from types import SimpleNamespace
            ns = SimpleNamespace(
                input_path=config['input_path'], target_lang=config['target_lang'],
                source_lang=config['source_lang'], engine=config['engine'],
                verbose=config.get('verbose', False), deep_scan=config.get('deep_scan', False),
                config=None, lt_url='', lt_key='', command='translate',
            )
            return run_translate_command(ns)
        return 0

    # Subcommands
    if args.command == 'translate' or args.command is None:
        return run_translate_command(args)

    if args.command == 'pseudo':
        return run_pseudo_command(args)

    return 0


# ============================================================
# Pseudo Command
# ============================================================

def run_pseudo_command(args) -> int:
    """Generate pseudo-localized translations for UI testing."""
    print_banner()
    print_section_header("PSEUDO-LOCALIZATION", "🧪")

    input_path = os.path.abspath(args.input_path)
    if not os.path.exists(input_path):
        print_error(f"Path not found: {input_path}")
        return 1

    print_key_value("Input", input_path, "📁")
    print_key_value("Mode", args.mode, "⚙")
    output_dir = args.output or os.path.join(input_path, "game", "tl", "pseudo") if os.path.isdir(input_path) else os.path.join(os.path.dirname(input_path), "pseudo")
    print_key_value("Output", output_dir, "📂")
    console.print()

    translator = PseudoTranslator(mode=args.mode)
    rpy_files = []
    if os.path.isfile(input_path) and input_path.lower().endswith('.rpy'):
        rpy_files = [input_path]
    else:
        game_dir = os.path.join(input_path, 'game') if os.path.isdir(os.path.join(input_path, 'game')) else input_path
        for root, dirs, files in os.walk(game_dir):
            if '/tl/' in root.replace('\\', '/') or '\\tl\\' in root:
                continue
            for f in files:
                if f.lower().endswith('.rpy'):
                    rpy_files.append(os.path.join(root, f))

    if not rpy_files:
        print_warning("No .rpy files found.")
        return 1

    print_info(f"Processing {len(rpy_files)} files...")
    console.print()

    import re
    pattern = re.compile(r'^(\s*)(\w+)?\s*"([^"]+)"', re.MULTILINE)
    translated_count = 0
    os.makedirs(output_dir, exist_ok=True)

    if RICH_AVAILABLE:
        with Progress(SpinnerColumn("dots", style=BRAND_PRIMARY),
                      TextColumn("[bold]{task.description}[/]"),
                      BarColumn(bar_width=30, style=BRAND_DIM, complete_style=BRAND_PRIMARY, finished_style=BRAND_SUCCESS),
                      MofNCompleteColumn(), console=console) as progress:
            task = progress.add_task("Processing", total=len(rpy_files))
            for rpy_file in rpy_files:
                rel = os.path.relpath(rpy_file, input_path)
                out = os.path.join(output_dir, rel)
                os.makedirs(os.path.dirname(out), exist_ok=True)
                try:
                    with open(rpy_file, 'r', encoding='utf-8') as f: content = f.read()
                    def replace(m):
                        nonlocal translated_count; translated_count += 1
                        return f'{m.group(1)}{m.group(2) or ""} "{translator._apply_pseudo(m.group(3))}"'
                    with open(out, 'w', encoding='utf-8') as f: f.write(pattern.sub(replace, content))
                except Exception as e: print_error(f"{rel}: {e}")
                progress.advance(task)
    else:
        for rpy_file in rpy_files:
            rel = os.path.relpath(rpy_file, input_path)
            out = os.path.join(output_dir, rel)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            try:
                with open(rpy_file, 'r', encoding='utf-8') as f: content = f.read()
                def replace(m):
                    nonlocal translated_count; translated_count += 1
                    return f'{m.group(1)}{m.group(2) or ""} "{translator._apply_pseudo(m.group(3))}"'
                with open(out, 'w', encoding='utf-8') as f: f.write(pattern.sub(replace, content))
            except Exception as e: print_error(f"{rel}: {e}")

    console.print()
    print_success(f"Pseudo-localized {translated_count} strings")
    print_key_value("Output", output_dir, "📂")
    return 0


if __name__ == "__main__":
    sys.exit(main())
