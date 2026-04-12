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

from PyQt6.QtCore import QCoreApplication, QTimer, QObject, pyqtSlot

# Import core modules
from src.utils.config import ConfigManager
from src.core.translation_pipeline import TranslationPipeline, PipelineResult, PipelineStage
from src.core.translator import TranslationManager, TranslationEngine, PseudoTranslator
from src.core.proxy_manager import ProxyManager
from src.version import VERSION

# Import new tool modules
try:
    from src.tools.health_check import HealthChecker, run_health_check
    from src.tools.fuzzy_matcher import FuzzyMatcher, TranslationMemory, create_common_memory
    from src.tools.font_helper import FontHelper, check_font_for_project
    from src.tools.context_viewer import ContextAnalyzer
    from src.tools.deferred_loading import DeferredLoadingGenerator
    TOOLS_AVAILABLE = True
except ImportError as e:
    TOOLS_AVAILABLE = False

# ============================================================================
# Rich Library — Modern Terminal UI
# ============================================================================
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn, TaskProgressColumn, MofNCompleteColumn
    from rich.live import Live
    from rich.columns import Columns
    from rich.align import Align
    from rich.rule import Rule
    from rich import box
    from rich.traceback import install as install_rich_traceback
    install_rich_traceback(show_locals=False, width=100)
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# ============================================================================
# Console Setup — ensure UTF-8 stdout on Windows before Rich takes over
# ============================================================================
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
    # Minimal fallback console that delegates to print()
    class _FallbackConsole:
        def print(self, *args, **kwargs):
            # Strip Rich markup for plain output
            text = ' '.join(str(a) for a in args)
            print(text)
        def rule(self, title="", **kwargs):
            print(f"\n{'─' * 20} {title} {'─' * 20}")
        def input(self, prompt=""):
            return input(prompt)
    console = _FallbackConsole()

# ============================================================================
# Theme Colors & Constants
# ============================================================================
BRAND_PRIMARY = "bright_magenta"
BRAND_SECONDARY = "bright_cyan"
BRAND_ACCENT = "bright_yellow"
BRAND_SUCCESS = "bright_green"
BRAND_ERROR = "bright_red"
BRAND_WARNING = "yellow"
BRAND_DIM = "dim white"

ENGINES = [
    ("google",         "Google Translate",  "🌐", "Free — 13 mirror + Lingva fallback"),
    ("deepl",          "DeepL",             "📘", "API key required — high quality"),
    ("openai",         "OpenAI (GPT)",      "🤖", "API key required — GPT models"),
    ("gemini",         "Google Gemini",     "✨", "API key required — Flash/Pro"),
    ("deepseek",       "DeepSeek",          "🔮", "API key required — OpenAI compatible"),
    ("local_llm",      "Local LLM",         "🏠", "Ollama / LM Studio — fully local"),
    ("libretranslate",  "LibreTranslate",    "🔓", "Self-hosted — Docker/Local"),
    ("yandex",         "Yandex Translate",   "🟡", "Free widget API — SID rotation"),
    ("pseudo",         "Pseudo (Test)",      "🧪", "For testing — fake translations"),
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


# ============================================================================
# Banner & UI Helpers
# ============================================================================

def print_banner():
    """Print a styled banner with gradient effect."""
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
        "rgb(180,80,255)",   # purple
        "rgb(160,90,255)",
        "rgb(140,100,255)",
        "rgb(120,120,255)",  # blue-purple
        "rgb(100,140,255)",
        "rgb(80,160,255)",
        "rgb(60,180,255)",   # cyan
        "rgb(80,200,240)",
        "rgb(100,220,220)",
        "rgb(120,240,200)",  # teal
        "rgb(100,220,220)",
        "rgb(80,200,240)",
    ]

    text = Text()
    for i, line in enumerate(banner_lines):
        color = gradient_colors[i % len(gradient_colors)]
        text.append(line + "\n", style=color)

    console.print(Align.center(text))


def print_section_header(title: str, icon: str = ""):
    """Print a styled section header."""
    if RICH_AVAILABLE:
        label = f"{icon}  {title}" if icon else title
        console.print()
        console.rule(f"[bold {BRAND_PRIMARY}]{label}[/]", style=BRAND_DIM)
        console.print()
    else:
        print(f"\n{'─' * 20} {icon} {title} {'─' * 20}\n")


def print_key_value(key: str, value: str, icon: str = ""):
    """Print a formatted key-value pair."""
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
    """Get styled user input."""
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
    """Display a styled menu and get user selection."""
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
    """Display a summary panel with key-value pairs."""
    if RICH_AVAILABLE:
        table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2), expand=False)
        table.add_column("Key", style=BRAND_DIM, min_width=18)
        table.add_column("Value", style=f"bold {BRAND_SECONDARY}")

        for key, value in data.items():
            table.add_row(key, str(value))

        panel = Panel(
            table,
            title=f"[bold {BRAND_PRIMARY}]{title}[/]",
            border_style=BRAND_DIM,
            padding=(1, 2),
        )
        console.print(panel)
    else:
        print(f"\n  {title}")
        print(f"  {'─' * 40}")
        for key, value in data.items():
            print(f"    {key:<18s} {value}")
        print()


# ============================================================================
# CLI Handler — Pipeline Signal Receiver (Rich-powered)
# ============================================================================

class CliHandler(QObject):
    """Handles CLI events and pipeline signals with Rich output."""

    def __init__(self, pipeline: TranslationPipeline, verbose: bool = False):
        super().__init__()
        self.pipeline = pipeline
        self.verbose = verbose
        self._current_stage = ""
        self._progress = None
        self._progress_task = None
        self._start_time = time.time()

        # Connect signals
        self.pipeline.stage_changed.connect(self.on_stage_changed)
        self.pipeline.progress_updated.connect(self.on_progress_updated)
        self.pipeline.log_message.connect(self.on_log_message)
        self.pipeline.finished.connect(self.on_finished)
        self.pipeline.show_warning.connect(self.on_warning)

    @pyqtSlot(str, str)
    def on_stage_changed(self, stage: str, message: str):
        self._current_stage = stage

        # Close previous progress if any
        if self._progress is not None:
            try:
                self._progress.stop()
            except Exception:
                pass
            self._progress = None
            self._progress_task = None

        if RICH_AVAILABLE:
            console.print()
            console.rule(f"[bold {BRAND_ACCENT}]⚡ {message}[/]", style=BRAND_DIM)
        else:
            print(f"\n>> STAGE: {message} ({stage})")

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
                    MofNCompleteColumn(),
                    TaskProgressColumn(),
                    TimeRemainingColumn(),
                    console=console,
                    transient=False,
                )
                self._progress.start()
                self._progress_task = self._progress.add_task(
                    text[:60],
                    total=total,
                    completed=current,
                )
            else:
                self._progress.update(
                    self._progress_task,
                    completed=current,
                    total=total,
                    description=text[:60],
                )
        else:
            percent = int((current / total) * 100) if total > 0 else 0
            sys.stdout.write(f"\rProgress: [{current}/{total}] {percent}% — {text[:50].ljust(50)}")
            sys.stdout.flush()

    @pyqtSlot(str, str)
    def on_log_message(self, level: str, message: str):
        should_show = self.verbose or level in ("warning", "error", "critical", "success")
        if not should_show:
            return

        if RICH_AVAILABLE:
            level_styles = {
                "info": (BRAND_DIM, "ℹ"),
                "success": (BRAND_SUCCESS, "✅"),
                "warning": (BRAND_WARNING, "⚠"),
                "error": (BRAND_ERROR, "❌"),
                "critical": (BRAND_ERROR, "💥"),
            }
            style, icon = level_styles.get(level, (BRAND_DIM, "•"))
            console.print(f"  [{style}]{icon} {message}[/]")
        else:
            print(f"\n[{level.upper()}] {message}")

    @pyqtSlot(str, str)
    def on_warning(self, title: str, message: str):
        if RICH_AVAILABLE:
            console.print(Panel(
                f"[{BRAND_WARNING}]{message}[/]",
                title=f"[bold {BRAND_WARNING}]⚠ {title}[/]",
                border_style=BRAND_WARNING,
                padding=(0, 2),
            ))
        else:
            print(f"\n[WARNING] {title}: {message}")

    @pyqtSlot(object)
    def on_finished(self, result: PipelineResult):
        # Stop progress bar
        if self._progress is not None:
            try:
                self._progress.stop()
            except Exception:
                pass
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

                panel = Panel(
                    result_table,
                    title=f"[bold {BRAND_SUCCESS}]✅ Translation Complete[/]",
                    subtitle=f"[{BRAND_DIM}]{result.message}[/]",
                    border_style=BRAND_SUCCESS,
                    padding=(1, 2),
                )
                console.print(panel)
            else:
                print(f"\n{'=' * 60}")
                print("SUCCESS")
                print(result.message)
                if result.stats:
                    print(f"\n  Total: {result.stats.get('total', 0)}")
                    print(f"  Translated: {result.stats.get('translated', 0)}")
                    print(f"  Duration: {elapsed_str}")
                print(f"{'=' * 60}")
        else:
            if RICH_AVAILABLE:
                error_content = f"[bold]{result.message}[/]"
                if result.error:
                    error_content += f"\n\n[{BRAND_DIM}]{result.error}[/]"
                panel = Panel(
                    error_content,
                    title=f"[bold {BRAND_ERROR}]❌ Translation Failed[/]",
                    border_style=BRAND_ERROR,
                    padding=(1, 2),
                )
                console.print(panel)
            else:
                print(f"\n{'=' * 60}")
                print("FAILED")
                print(result.message)
                if result.error:
                    print(f"Details: {result.error}")
                print(f"{'=' * 60}")

        # Quit application
        QCoreApplication.quit()


# ============================================================================
# Setup & Config
# ============================================================================

def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

def load_config_override(config_path: str) -> dict:
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print_error(f"Loading config file {config_path}: {e}")
        return {}


# ============================================================================
# Command Handlers
# ============================================================================

def run_health_check_command(args) -> int:
    """Run health check (static analysis) on a project."""
    if not TOOLS_AVAILABLE:
        print_error("Health check tools not available")
        return 1

    print_banner()
    print_section_header("HEALTH CHECK", "🏥")

    input_path = os.path.abspath(args.input_path)
    if not os.path.exists(input_path):
        print_error(f"Path not found: {input_path}")
        return 1

    print_info(f"Scanning: {input_path}")
    console.print()

    report = run_health_check(input_path, verbose=args.verbose)

    if RICH_AVAILABLE:
        status_icon = "✅" if report.is_healthy else "⚠"
        status_color = BRAND_SUCCESS if report.is_healthy else BRAND_WARNING
        panel = Panel(
            report.summary(),
            title=f"[bold {status_color}]{status_icon} Health Report[/]",
            border_style=status_color,
            padding=(1, 2),
        )
        console.print(panel)
    else:
        print(f"\n{'=' * 60}")
        print(report.summary())
        print(f"{'=' * 60}")

    return 0 if report.is_healthy else 1


def run_font_check_command(args) -> int:
    """Check font compatibility for a target language."""
    if not TOOLS_AVAILABLE:
        print_error("Font check tools not available")
        return 1

    print_banner()
    print_section_header("FONT COMPATIBILITY CHECK", "🔤")

    input_path = os.path.abspath(args.input_path)
    if not os.path.exists(input_path):
        print_error(f"Path not found: {input_path}")
        return 1

    print_key_value("Directory", input_path, "📁")
    print_key_value("Language", args.lang, "🌐")
    console.print()

    summary = check_font_for_project(input_path, args.lang, verbose=args.verbose)

    if RICH_AVAILABLE:
        table = Table(title="Font Compatibility Results", box=box.ROUNDED, border_style=BRAND_DIM)
        table.add_column("Metric", style=BRAND_DIM)
        table.add_column("Count", style=f"bold {BRAND_SECONDARY}", justify="right")

        table.add_row("Fonts checked", str(summary['fonts_checked']))
        table.add_row("Compatible", f"[{BRAND_SUCCESS}]{summary['compatible_fonts']}[/]")
        table.add_row("Incompatible", f"[{BRAND_ERROR}]{summary['incompatible_fonts']}[/]" if summary['incompatible_fonts'] > 0 else "0")

        console.print(table)
    else:
        print(f"\n  Fonts checked: {summary['fonts_checked']}")
        print(f"  Compatible: {summary['compatible_fonts']}")
        print(f"  Incompatible: {summary['incompatible_fonts']}")

    return 0 if summary['incompatible_fonts'] == 0 else 1


def run_pseudo_command(args) -> int:
    """Generate pseudo-localized translations for UI testing."""
    print_banner()
    print_section_header("PSEUDO-LOCALIZATION", "🧪")

    input_path = os.path.abspath(args.input_path)
    if not os.path.exists(input_path):
        print_error(f"Path not found: {input_path}")
        return 1

    mode = args.mode
    print_key_value("Input", input_path, "📁")
    print_key_value("Mode", mode, "⚙")

    # Determine output directory
    if args.output:
        output_dir = os.path.abspath(args.output)
    else:
        if os.path.isfile(input_path):
            base = os.path.dirname(input_path)
        else:
            base = input_path
        output_dir = os.path.join(base, "game", "tl", "pseudo")

    print_key_value("Output", output_dir, "📂")
    console.print()

    # Create PseudoTranslator
    translator = PseudoTranslator(mode=mode)

    # Find .rpy files to process
    rpy_files = []
    if os.path.isfile(input_path) and input_path.lower().endswith('.rpy'):
        rpy_files = [input_path]
    else:
        game_dir = os.path.join(input_path, 'game')
        if os.path.isdir(game_dir):
            for root, dirs, files in os.walk(game_dir):
                if '/tl/' in root.replace('\\', '/') or '\\tl\\' in root:
                    continue
                for f in files:
                    if f.lower().endswith('.rpy'):
                        rpy_files.append(os.path.join(root, f))

    if not rpy_files:
        print_warning("No .rpy files found to process.")
        print_info("Hint: Run UnRen first if the game is still compiled.")
        return 1

    print_info(f"Found {len(rpy_files)} .rpy files")
    console.print()

    # Process each file
    import re
    dialogue_pattern = re.compile(r'^(\s*)(\w+)?\s*"([^"]+)"', re.MULTILINE)
    translated_count = 0

    os.makedirs(output_dir, exist_ok=True)

    if RICH_AVAILABLE:
        with Progress(
            SpinnerColumn("dots", style=BRAND_PRIMARY),
            TextColumn("[bold]{task.description}[/]"),
            BarColumn(bar_width=30, style=BRAND_DIM, complete_style=BRAND_PRIMARY, finished_style=BRAND_SUCCESS),
            MofNCompleteColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Processing files", total=len(rpy_files))
            for rpy_file in rpy_files:
                rel_path = os.path.relpath(rpy_file, input_path)
                output_file = os.path.join(output_dir, rel_path)
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                try:
                    with open(rpy_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    def pseudo_replace(match):
                        nonlocal translated_count
                        indent = match.group(1) or ""
                        speaker = match.group(2) or ""
                        text = match.group(3)
                        pseudo_text = translator._apply_pseudo(text)
                        translated_count += 1
                        if speaker:
                            return f'{indent}{speaker} "{pseudo_text}"'
                        else:
                            return f'{indent}"{pseudo_text}"'

                    pseudo_content = dialogue_pattern.sub(pseudo_replace, content)
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(pseudo_content)
                except Exception as e:
                    print_error(f"Error processing {rel_path}: {e}")
                progress.advance(task)
    else:
        for rpy_file in rpy_files:
            rel_path = os.path.relpath(rpy_file, input_path)
            output_file = os.path.join(output_dir, rel_path)
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            try:
                with open(rpy_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                def pseudo_replace(match):
                    nonlocal translated_count
                    indent = match.group(1) or ""
                    speaker = match.group(2) or ""
                    text = match.group(3)
                    pseudo_text = translator._apply_pseudo(text)
                    translated_count += 1
                    if speaker:
                        return f'{indent}{speaker} "{pseudo_text}"'
                    else:
                        return f'{indent}"{pseudo_text}"'

                pseudo_content = dialogue_pattern.sub(pseudo_replace, content)
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(pseudo_content)
            except Exception as e:
                print(f"  ✗ Error processing {rel_path}: {e}")

    console.print()
    print_success(f"Pseudo-localized {translated_count} strings")
    print_key_value("Output", output_dir, "📂")
    console.print()

    if RICH_AVAILABLE:
        panel = Panel(
            "[dim]1.[/] Copy the [bold]pseudo[/] folder to your game's [bold]tl/[/] directory\n"
            "[dim]2.[/] In game preferences, select [bold]pseudo[/] as language\n"
            "[dim]3.[/] Look for [bold yellow][!!! markers !!!][/] and [bold cyan]àccéntéd characters[/]",
            title=f"[bold {BRAND_PRIMARY}]Next Steps[/]",
            border_style=BRAND_DIM,
            padding=(1, 2),
        )
        console.print(panel)
    else:
        print("  To test in game:")
        print("  1. Copy the 'pseudo' folder to your game's tl/ directory")
        print("  2. In game preferences, select 'pseudo' as language")
        print("  3. Look for [!!! markers !!!] and àccéntéd characters")

    return 0


def run_fuzzy_command(args) -> int:
    """Run fuzzy matching to recover translations."""
    if not TOOLS_AVAILABLE:
        print_error("Fuzzy matching tools not available")
        return 1

    print_banner()
    print_section_header("FUZZY MATCHING — Smart Update", "🔍")

    old_tl = os.path.abspath(args.old_tl)
    new_tl = os.path.abspath(args.new_tl)

    if not os.path.exists(old_tl):
        print_error(f"Old TL path not found: {old_tl}")
        return 1
    if not os.path.exists(new_tl):
        print_error(f"New TL path not found: {new_tl}")
        return 1

    threshold = args.threshold
    print_key_value("Old translations", old_tl, "📁")
    print_key_value("New translations", new_tl, "📂")
    print_key_value("Auto-apply threshold", f"{threshold * 100:.0f}%", "🎯")
    console.print()

    # Parse old translations
    from src.core.tl_parser import TLParser
    parser = TLParser()

    print_info("Parsing old translations...")
    old_files = parser.parse_directory(os.path.dirname(old_tl), os.path.basename(old_tl))

    print_info("Parsing new translations...")
    new_files = parser.parse_directory(os.path.dirname(new_tl), os.path.basename(new_tl))

    # Build entry dicts
    old_entries = {}
    for tl_file in old_files:
        for entry in tl_file.entries:
            if entry.translated_text:
                old_entries[entry.translation_id] = (entry.original_text, entry.translated_text)

    new_entries = {}
    new_entries_by_file = {}
    for tl_file in new_files:
        new_entries_by_file[tl_file.file_path] = {}
        for entry in tl_file.entries:
            new_entries[entry.translation_id] = entry.original_text
            new_entries_by_file[tl_file.file_path][entry.translation_id] = entry

    print_key_value("Old entries", str(len(old_entries)), "📊")
    print_key_value("New entries", str(len(new_entries)), "📊")
    console.print()

    # Run fuzzy matching
    matcher = FuzzyMatcher(auto_threshold=threshold)
    report = matcher.match_translations(new_entries, old_entries)

    print(report.summary())

    if args.verbose:
        console.print()
        print_section_header("Matches Found", "🔗")
        if RICH_AVAILABLE:
            table = Table(box=box.SIMPLE, padding=(0, 1))
            table.add_column("", width=3)
            table.add_column("Similarity", justify="right", style=BRAND_ACCENT)
            table.add_column("Text", style=BRAND_DIM)

            for match in report.matches[:20]:
                status = f"[{BRAND_SUCCESS}]✓[/]" if match.is_confident() else f"[{BRAND_WARNING}]?[/]"
                table.add_row(status, f"{match.similarity_percent}%", match.new_original[:60])

            console.print(table)
        else:
            for match in report.matches[:20]:
                status = "✓" if match.is_confident() else "?"
                print(f"    [{status}] {match.similarity_percent}%: \"{match.new_original[:40]}...\"")

    if args.apply and report.auto_apply_count > 0:
        print_info(f"Applying {report.auto_apply_count} confident matches...")

        suggestions = {}
        for match in report.matches:
            if match.is_confident(threshold):
                suggestions[match.new_id] = match.old_translation

        applied_count = 0
        for file_path, entries in new_entries_by_file.items():
            file_modified = False
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                import re
                for trans_id, entry in entries.items():
                    if trans_id in suggestions:
                        new_translation = suggestions[trans_id]
                        old_pattern = re.escape(entry.original_text)

                        if entry.original_text in content:
                            pattern = rf'(old\s+"[^"]*"\s*\n\s*new\s+")({re.escape(entry.original_text)})(")' 
                            replacement = rf'\g<1>{new_translation}\g<3>'
                            new_content, count = re.subn(pattern, replacement, content)

                            if count > 0:
                                content = new_content
                                file_modified = True
                                applied_count += 1
                            else:
                                pattern2 = rf'(#\s*"{re.escape(entry.original_text)}"\s*\n\s*")({re.escape(entry.original_text)})(")' 
                                replacement2 = rf'\g<1>{new_translation}\g<3>'
                                new_content, count = re.subn(pattern2, replacement2, content)
                                if count > 0:
                                    content = new_content
                                    file_modified = True
                                    applied_count += 1

                if file_modified:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    if args.verbose:
                        print_success(f"Updated: {os.path.basename(file_path)}")

            except Exception as e:
                print_error(f"Error updating {file_path}: {e}")

        print_success(f"Applied {applied_count} translations")

        # Export suggestions to JSON
        suggestions_file = os.path.join(new_tl, "fuzzy_suggestions.json")
        try:
            with open(suggestions_file, 'w', encoding='utf-8') as f:
                export_data = [
                    {
                        "new_id": m.new_id,
                        "new_original": m.new_original,
                        "suggested": m.old_translation,
                        "similarity": m.similarity_percent,
                        "auto_applied": m.is_confident(threshold)
                    }
                    for m in report.matches
                ]
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            print_key_value("Suggestions exported", suggestions_file, "📁")
        except Exception as e:
            print_warning(f"Could not export suggestions: {e}")

    elif report.auto_apply_count > 0:
        console.print()
        print_info(f"💡 {report.auto_apply_count} translations can be auto-applied.")
        print_info(f"Use --apply flag: python run_cli.py fuzzy {args.old_tl} {args.new_tl} --apply")

    return 0


def run_extract_glossary_command(args) -> int:
    """Run glossary extraction."""
    try:
        from src.tools.glossary_extractor import GlossaryExtractor
    except ImportError:
        print_error("Glossary extractor tool not found.")
        return 1

    print_banner()
    print_section_header("GLOSSARY EXTRACTOR", "📚")

    input_path = os.path.abspath(args.input_path)
    if not os.path.exists(input_path):
        print_error(f"Path not found: {input_path}")
        return 1

    print_info(f"Scanning: {input_path}")

    extractor = GlossaryExtractor()
    terms = extractor.extract_from_directory(input_path, min_occurrence=args.min_count)

    if not terms:
        print_warning("No terms found.")
        return 0

    print_success(f"Found {len(terms)} potential terms.")

    output_file = args.output
    if not output_file:
        output_file = os.path.join(os.getcwd(), "glossary_extracted.json")

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(terms, f, ensure_ascii=False, indent=2)
        print_key_value("Saved to", output_file, "💾")
    except Exception as e:
        print_error(f"Error saving file: {e}")
        return 1

    return 0


# ============================================================================
# Interactive Mode — Modern TUI
# ============================================================================

def clear_screen():
    """Clear the terminal screen."""
    if RICH_AVAILABLE:
        console.clear()
    else:
        os.system('cls' if os.name == 'nt' else 'clear')


def select_engine() -> str:
    """Interactive engine selection with descriptions."""
    options = []
    icons = []
    for code, name, icon, desc in ENGINES:
        if RICH_AVAILABLE:
            options.append(f"{name}  [{BRAND_DIM}]{desc}[/]")
        else:
            options.append(f"{name} — {desc}")
        icons.append(icon)

    choice = print_menu("Select Translation Engine", options, show_back=True, icons=icons)
    if choice == 0:
        return ""
    return ENGINES[choice - 1][0]


def select_language() -> str:
    """Interactive language selection."""
    options = []
    icons = []
    for code, name, icon in LANGUAGES:
        options.append(f"{name} ({code})")
        icons.append(icon)
    options.append("Other (enter manually)")
    icons.append("⌨")

    choice = print_menu("Select Target Language", options, show_back=True, icons=icons)
    if choice == 0:
        return ""
    if choice <= len(LANGUAGES):
        return LANGUAGES[choice - 1][0]
    return get_user_input("Language code", "tr")


def interactive_mode() -> dict:
    """Run interactive setup wizard with Rich UI."""
    config = {
        'input_path': '',
        'target_lang': 'tr',
        'source_lang': 'auto',
        'engine': 'google',
        'mode': 'auto',
        'proxy': False,
        'verbose': False
    }

    clear_screen()
    print_banner()

    # Main Menu
    while True:
        choice = print_menu(
            "MAIN MENU",
            [
                "Full Translation (Game EXE/Project)",
                "Translate Existing TL Folder",
                "Settings",
                "Help",
                "Exit"
            ],
            show_back=False,
            icons=["🎮", "📁", "⚙", "❓", "👋"],
        )

        if choice == 1:  # Full Translation
            print_section_header("STEP 1 — File/Folder Selection", "📂")
            print_info("Enter the game EXE or project folder path.")
            console.print()

            path = get_user_input("Path")
            if not path:
                print_warning("Path cannot be empty")
                continue
            if not os.path.exists(path):
                print_error(f"File/folder not found: {path}")
                continue
            config['input_path'] = os.path.abspath(path)

            # Target language
            print_section_header("STEP 2 — Target Language", "🌍")
            lang = select_language()
            if not lang:
                continue
            config['target_lang'] = lang

            # Engine selection
            print_section_header("STEP 3 — Translation Engine", "⚡")
            engine = select_engine()
            if not engine:
                continue
            config['engine'] = engine

            # Mode selection
            print_section_header("STEP 4 — Operation Mode", "🔧")
            mode_choice = print_menu(
                "Select mode",
                [
                    "Auto (Recommended)",
                    "Full (UnRen + Translation)",
                    "Translate Only"
                ],
                show_back=True,
                icons=["🤖", "📦", "📝"],
            )
            if mode_choice == 0:
                continue
            config['mode'] = ['auto', 'full', 'translate'][mode_choice - 1]

            # Summary & Confirm
            clear_screen()
            print_banner()

            build_summary_panel({
                "Path": config['input_path'],
                "Target Language": config['target_lang'],
                "Source Language": config['source_lang'],
                "Engine": config['engine'],
                "Mode": config['mode'],
                "Proxy": "On" if config['proxy'] else "Off",
            }, title="📋 Translation Summary")

            confirm = get_user_input("Start translation? (y/n)", "y")
            if confirm.lower() in ('y', 'yes'):
                return config

        elif choice == 2:  # Translate TL Folder
            print_section_header("TRANSLATE EXISTING TL FOLDER", "📁")
            print_info("Enter the path to your game's tl folder")
            if sys.platform == "win32":
                print_info("Example: C:\\Games\\MyGame\\game\\tl\\turkish")
            else:
                print_info("Example: /home/user/Games/MyGame/game/tl/turkish")
            console.print()

            path = get_user_input("TL Folder Path")
            if not path:
                print_warning("Path cannot be empty")
                continue
            if not os.path.exists(path):
                print_error(f"Folder not found: {path}")
                continue

            config['input_path'] = os.path.abspath(path)
            config['mode'] = 'translate'

            # Target language
            print_section_header("Target Language", "🌍")
            lang = select_language()
            if not lang:
                continue
            config['target_lang'] = lang

            # Engine selection
            print_section_header("Translation Engine", "⚡")
            engine = select_engine()
            if not engine:
                continue
            config['engine'] = engine

            # Summary & Confirm
            clear_screen()
            print_banner()

            build_summary_panel({
                "TL Folder": config['input_path'],
                "Target Language": config['target_lang'],
                "Source Language": config['source_lang'],
                "Engine": config['engine'],
                "Mode": "translate (TL folder)",
            }, title="📋 Translation Summary")

            confirm = get_user_input("Start translation? (y/n)", "y")
            if confirm.lower() in ('y', 'yes'):
                return config

        elif choice == 3:  # Settings
            while True:
                proxy_status = f"[{BRAND_SUCCESS}]On[/]" if config['proxy'] else f"[{BRAND_ERROR}]Off[/]"
                verbose_status = f"[{BRAND_SUCCESS}]On[/]" if config['verbose'] else f"[{BRAND_ERROR}]Off[/]"

                if RICH_AVAILABLE:
                    options = [
                        f"Source Language  [{BRAND_SECONDARY}]{config['source_lang']}[/]",
                        f"Translation Engine  [{BRAND_SECONDARY}]{config['engine']}[/]",
                        f"Proxy  {proxy_status}",
                        f"Verbose Logging  {verbose_status}",
                    ]
                else:
                    options = [
                        f"Source Language: {config['source_lang']}",
                        f"Translation Engine: {config['engine']}",
                        f"Proxy: {'On' if config['proxy'] else 'Off'}",
                        f"Verbose Logging: {'On' if config['verbose'] else 'Off'}",
                    ]

                settings_choice = print_menu(
                    "⚙  SETTINGS", options,
                    icons=["🌐", "⚡", "🔀", "📝"],
                )

                if settings_choice == 0:
                    break
                elif settings_choice == 1:
                    config['source_lang'] = get_user_input("Source language code", config['source_lang'])
                elif settings_choice == 2:
                    engine = select_engine()
                    if engine:
                        config['engine'] = engine
                elif settings_choice == 3:
                    config['proxy'] = not config['proxy']
                    status = "enabled" if config['proxy'] else "disabled"
                    print_info(f"Proxy {status}")
                elif settings_choice == 4:
                    config['verbose'] = not config['verbose']
                    status = "enabled" if config['verbose'] else "disabled"
                    print_info(f"Verbose logging {status}")

        elif choice == 4:  # Help
            clear_screen()
            print_banner()

            if RICH_AVAILABLE:
                help_text = (
                    f"[bold {BRAND_PRIMARY}]RenLocalizer[/] automatically translates "
                    f"Ren'Py visual novel games.\n\n"
                    f"[bold {BRAND_ACCENT}]TRANSLATION MODES[/]\n\n"
                    f"  [bold]1. Full Translation[/] [dim](Game EXE/Project)[/]\n"
                    f"     For games with .exe or project folders\n"
                    f"     On Windows: Can run UnRen automatically\n"
                    f"     On Mac/Linux: Use with pre-extracted files\n\n"
                    f"  [bold]2. Translate Existing TL Folder[/]\n"
                    f"     For already generated tl/<lang> folders\n"
                    f"     Useful when you have .rpy translation files\n"
                    f"     Works on all platforms\n\n"
                    f"[bold {BRAND_ACCENT}]COMMAND LINE USAGE[/]\n\n"
                    f"  [dim]$[/] python run_cli.py <path> --target-lang tr --mode auto\n"
                    f"  [dim]$[/] python run_cli.py translate <path> -t fr -e gemini\n"
                    f"  [dim]$[/] python run_cli.py health-check <path>\n"
                    f"  [dim]$[/] python run_cli.py font-check <path> --lang vi\n"
                    f"  [dim]$[/] python run_cli.py fuzzy <old_tl> <new_tl> --apply\n\n"
                    f"[dim]For more info: docs/CLI_USAGE.md[/]"
                )
                panel = Panel(
                    help_text,
                    title=f"[bold {BRAND_PRIMARY}]❓ Help[/]",
                    border_style=BRAND_DIM,
                    padding=(1, 2),
                )
                console.print(panel)
            else:
                print("""
  HELP
  ─────────────────────────────────────────

  RenLocalizer CLI automatically translates
  Ren'Py visual novel games.

  TRANSLATION MODES:

  1. Full Translation (Game EXE/Project)
     - For games with .exe or project folders
     - On Windows: Can run UnRen automatically
     - On Mac/Linux: Use with pre-extracted files

  2. Translate Existing TL Folder
     - For already generated tl/<lang> folders
     - Useful when you have .rpy translation files
     - Works on all platforms

  COMMAND LINE USAGE:
  python run_cli.py <path> --target-lang tr --mode auto

  For more info: docs/CLI_USAGE.md
  ─────────────────────────────────────────
                """)

            if RICH_AVAILABLE:
                console.input(f"\n  [{BRAND_DIM}]Press Enter to continue...[/]")
            else:
                input("\n  Press Enter to continue...")

        elif choice == 5:  # Exit
            if RICH_AVAILABLE:
                console.print(f"\n  [{BRAND_DIM}]Goodbye! 👋[/]\n")
            else:
                print("\n  Goodbye!\n")
            sys.exit(0)

    return config


# ============================================================================
# Main Entry Point
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description=f"RenLocalizer V{VERSION} CLI — Ren'Py Game Translation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # TRANSLATE command (default)
    translate_parser = subparsers.add_parser('translate', help='Translate a game or project')
    translate_parser.add_argument("input_path", nargs='?', default=None,
                        help="Path to game executable, project directory, or translation file")
    translate_parser.add_argument("--config", help="Path to JSON configuration file")
    translate_parser.add_argument("--target-lang", "-t", default="tr", help="Target language code (default: tr)")
    translate_parser.add_argument("--source-lang", "-s", default="auto", help="Source language code (default: auto)")
    translate_parser.add_argument("--engine", "-e", default="google", choices=["google", "deepl", "openai", "gemini", "deepseek", "local_llm", "libretranslate", "yandex", "pseudo"], help="Translation engine")
    translate_parser.add_argument("--mode", choices=["auto", "full", "translate"], default="auto",
                        help="Operation mode: 'auto' (detect), 'full' (UnRen+Trans), 'translate' (Trans only)")
    translate_parser.add_argument("--proxy", action="store_true", help="Enable proxy")
    translate_parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    translate_parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive menu mode")
    translate_parser.add_argument("--deep-scan", "-d", action="store_true", help="Enable deep scanning (AST/RPYC analysis)")

    # HEALTH-CHECK command
    health_parser = subparsers.add_parser('health-check', help='Run static analysis on project')
    health_parser.add_argument("input_path", help="Path to game directory or .rpy file")
    health_parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    health_parser.add_argument("--include-tl", action="store_true", help="Also check tl/ folder")

    # FONT-CHECK command
    font_parser = subparsers.add_parser('font-check', help='Check font compatibility for a language')
    font_parser.add_argument("input_path", help="Path to game directory")
    font_parser.add_argument("--lang", "-l", default="tr", help="Target language code (default: tr)")
    font_parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")

    # PSEUDO command (quick pseudo-localization)
    pseudo_parser = subparsers.add_parser('pseudo', help='Generate pseudo-localized text for UI testing')
    pseudo_parser.add_argument("input_path", help="Path to game directory or tl folder")
    pseudo_parser.add_argument("--mode", choices=["expand", "accent", "both"], default="both",
                               help="Pseudo mode: expand ([!!! !!!]), accent (àccénts), or both")
    pseudo_parser.add_argument("--output", "-o", help="Output directory (default: tl/pseudo)")

    # FUZZY command (smart update)
    fuzzy_parser = subparsers.add_parser('fuzzy', help='Recover translations using fuzzy matching')
    fuzzy_parser.add_argument("old_tl", help="Path to old translation files")
    fuzzy_parser.add_argument("new_tl", help="Path to new translation files")
    fuzzy_parser.add_argument("--threshold", type=float, default=0.9, help="Auto-apply threshold (default: 0.9)")
    fuzzy_parser.add_argument("--apply", action="store_true", help="Apply suggestions automatically")
    fuzzy_parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")

    # EXTRACT-GLOSSARY command
    glossary_parser = subparsers.add_parser('extract-glossary', help='Extract potential glossary terms from project')
    glossary_parser.add_argument("input_path", help="Path to game directory")
    glossary_parser.add_argument("--min-count", type=int, default=3, help="Minimum occurrence for common terms")
    glossary_parser.add_argument("--output", "-o", help="Output JSON file (default: glossary_extracted.json)")

    # Legacy support
    parser.add_argument("legacy_input_path", nargs='?', default=None, metavar='input_path',
                        help="Path to game executable, project directory, or translation file")
    parser.add_argument("--config", help="Path to JSON configuration file to override settings")
    parser.add_argument("--target-lang", "-t", default="tr", help="Target language code (default: tr)")
    parser.add_argument("--source-lang", "-s", default="auto", help="Source language code (default: auto)")
    parser.add_argument("--engine", "-e", default="google", choices=["google", "deepl", "openai", "gemini", "deepseek", "local_llm", "libretranslate", "yandex", "pseudo"], help="Translation engine")
    parser.add_argument("--mode", choices=["auto", "full", "translate"], default="auto",
                        help="Operation mode: 'auto' (detect), 'full' (UnRen+Trans), 'translate' (Trans only)")
    parser.add_argument("--proxy", action="store_true", help="Enable proxy")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive menu mode")
    parser.add_argument("--deep-scan", action="store_true", help="Enable deep scanning")
    parser.add_argument("--rpyc", action="store_true", help="Enable RPYC reader (experimental)")

    args = parser.parse_args()

    # Normalize: If using legacy mode (no subcommand), copy legacy_input_path to input_path
    if args.command is None and hasattr(args, 'legacy_input_path'):
        args.input_path = args.legacy_input_path

    # Handle subcommands
    if args.command == 'translate':
        if args.input_path is None:
            interactive_config = interactive_mode()
            args.input_path = interactive_config['input_path']
            args.target_lang = interactive_config['target_lang']
            args.source_lang = interactive_config['source_lang']
            args.engine = interactive_config['engine']
            args.mode = interactive_config['mode']
            args.proxy = interactive_config['proxy']
            args.verbose = interactive_config['verbose']
    elif args.command == 'health-check':
        return run_health_check_command(args)
    elif args.command == 'font-check':
        return run_font_check_command(args)
    elif args.command == 'pseudo':
        return run_pseudo_command(args)
    elif args.command == 'fuzzy':
        return run_fuzzy_command(args)
    elif args.command == 'extract-glossary':
        return run_extract_glossary_command(args)
    elif args.command is None:
        if args.input_path is None or args.interactive:
            interactive_config = interactive_mode()
            args.input_path = interactive_config['input_path']
            args.target_lang = interactive_config['target_lang']
            args.source_lang = interactive_config['source_lang']
            args.engine = interactive_config['engine']
            args.mode = interactive_config['mode']
            args.proxy = interactive_config['proxy']
            args.verbose = interactive_config['verbose']

    # Create config manager
    config_manager = ConfigManager()

    # Apply CLI args to config
    if args.config:
        overrides = load_config_override(args.config)
        if 'translation_settings' in overrides:
            for k, v in overrides['translation_settings'].items():
                if hasattr(config_manager.translation_settings, k):
                    setattr(config_manager.translation_settings, k, v)
        if 'app_settings' in overrides:
            for k, v in overrides['app_settings'].items():
                if hasattr(config_manager.app_settings, k):
                    setattr(config_manager.app_settings, k, v)

    config_manager.translation_settings.target_language = config_manager.normalize_renpy_language_code(args.target_lang)
    config_manager.translation_settings.source_language = args.source_lang
    config_manager.translation_settings.enable_proxy = args.proxy
    config_manager.proxy_settings.enabled = args.proxy

    # Setup Logging
    setup_logging(args.verbose)

    # Setup QCoreApplication
    app = QCoreApplication(sys.argv)
    app.setApplicationName("RenLocalizerCLI")
    app.setApplicationVersion(VERSION)

    # Initialize Managers
    proxy_manager = ProxyManager()
    proxy_manager.configure_from_settings(config_manager.proxy_settings)
    translation_manager = TranslationManager(proxy_manager=proxy_manager, config_manager=config_manager)

    # =========================================================================
    # SETUP TRANSLATION ENGINES
    # =========================================================================
    try:
        from src.core.ai_translator import OpenAITranslator, GeminiTranslator, LocalLLMTranslator, DeepSeekTranslator
        from src.core.translator import GoogleTranslator, DeepLTranslator

        selected_engine_code = args.engine.lower()
        ts = config_manager.translation_settings

        if selected_engine_code == 'deepl':
            translation_manager.add_translator(
                TranslationEngine.DEEPL,
                DeepLTranslator(
                    api_key=config_manager.api_keys.deepl_api_key,
                    proxy_manager=proxy_manager,
                    config_manager=config_manager
                )
            )
        elif selected_engine_code == 'openai':
            openai_key = config_manager.get_api_key("openai")
            if not openai_key:
                print_error("OpenAI API key not found in config.")
                return 1
            translation_manager.add_translator(
                TranslationEngine.OPENAI,
                OpenAITranslator(
                    api_key=openai_key,
                    model=getattr(ts, 'openai_model', 'gpt-3.5-turbo'),
                    base_url=getattr(ts, 'openai_base_url', None),
                    config_manager=config_manager,
                    proxy_manager=proxy_manager
                )
            )
        elif selected_engine_code == 'gemini':
            gemini_key = config_manager.get_api_key("gemini")
            if not gemini_key:
                print_error("Gemini API key not found in config.")
                return 1

            gemini_translator = GeminiTranslator(
                api_key=gemini_key,
                model=getattr(ts, 'gemini_model', 'gemini-pro'),
                safety_level=getattr(ts, 'gemini_safety_settings', None),
                config_manager=config_manager,
                proxy_manager=proxy_manager
            )
            # Add fallback
            fallback = GoogleTranslator(proxy_manager=proxy_manager, config_manager=config_manager)
            gemini_translator.set_fallback_translator(fallback)
            translation_manager.add_translator(TranslationEngine.GEMINI, gemini_translator)

        elif selected_engine_code == 'deepseek':
            deepseek_key = config_manager.get_api_key("deepseek")
            if not deepseek_key:
                print_error("DeepSeek API key not found in config.")
                return 1

            deepseek_translator = DeepSeekTranslator(
                api_key=deepseek_key,
                model=getattr(ts, 'deepseek_model', 'deepseek-chat'),
                base_url=getattr(ts, 'deepseek_base_url', None),
                config_manager=config_manager,
                proxy_manager=proxy_manager,
                temperature=getattr(ts, 'ai_temperature', 0.3),
                timeout=getattr(ts, 'ai_timeout', 120),
                max_tokens=getattr(ts, 'ai_max_tokens', 4096),
            )
            # Add fallback
            fallback = GoogleTranslator(proxy_manager=proxy_manager, config_manager=config_manager)
            deepseek_translator.set_fallback_translator(fallback)
            translation_manager.add_translator(TranslationEngine.DEEPSEEK, deepseek_translator)

        elif selected_engine_code == 'local_llm':
            translation_manager.add_translator(
                TranslationEngine.LOCAL_LLM,
                LocalLLMTranslator(
                    model=getattr(ts, 'local_llm_model', 'llama3.2'),
                    base_url=getattr(ts, 'local_llm_url', 'http://localhost:11434/v1'),
                    config_manager=config_manager,
                    proxy_manager=proxy_manager
                )
            )

        elif selected_engine_code == 'libretranslate':
            from src.core.translator import LibreTranslateTranslator
            translation_manager.add_translator(
                TranslationEngine.LIBRETRANSLATE,
                LibreTranslateTranslator(
                    base_url=getattr(ts, 'libretranslate_url', 'http://localhost:5000'),
                    api_key=getattr(ts, 'libretranslate_api_key', ''),
                    config_manager=config_manager
                )
            )

        elif selected_engine_code == 'yandex':
            from src.core.translator import YandexTranslator
            yandex_translator = YandexTranslator(
                proxy_manager=proxy_manager,
                config_manager=config_manager
            )
            google_fallback = GoogleTranslator(
                proxy_manager=proxy_manager,
                config_manager=config_manager
            )
            yandex_translator.set_fallback_translator(google_fallback)
            translation_manager.add_translator(TranslationEngine.YANDEX, yandex_translator)

    except Exception as e:
        print_warning(f"Error setting up translation engine: {e}")

    pipeline = TranslationPipeline(config_manager, translation_manager)

    # Show startup info
    print_banner()
    print_section_header("Translation Session", "🚀")

    # Determine Mode
    input_path = os.path.abspath(args.input_path)
    if not os.path.exists(input_path):
        print_error(f"Input path does not exist: {input_path}")
        return 1

    is_windows = sys.platform == "win32"
    mode = args.mode
    is_exe_file = os.path.isfile(input_path) and input_path.lower().endswith(".exe")
    is_directory = os.path.isdir(input_path)
    is_renpy_project = is_directory and (
        os.path.isdir(os.path.join(input_path, 'game')) or
        os.path.basename(input_path).lower() == 'game'
    )

    if mode == "auto":
        if is_exe_file:
            mode = "full"
        elif is_renpy_project:
            mode = "full"
        else:
            mode = "translate"

    if mode == "full" and is_directory and not is_renpy_project:
        if not os.path.isdir(os.path.join(input_path, 'game')):
            print_warning(f"Directory '{input_path}' doesn't have a 'game' subfolder.")
            print_info("Attempting to use it as project root anyway...")

    if is_exe_file and mode == "translate":
        if is_windows:
            print_info("EXE file provided with 'translate' mode. Switching to 'full' mode.")
            mode = "full"
        else:
            if not is_windows and is_exe_file:
                print_info("EXE file detected. Attempting extraction via Unrpa (cross-platform).")
                mode = "full"

    # Display session info
    build_summary_panel({
        "Input": os.path.basename(input_path),
        "Mode": mode,
        "Target": args.target_lang.upper(),
        "Engine": args.engine.upper(),
        "Version": f"v{VERSION}",
    }, title="🚀 Session Info")

    # Create CLI Handler
    handler = CliHandler(pipeline, verbose=args.verbose)

    # Configure Pipeline
    try:
        engine_enum = TranslationEngine(args.engine.lower())
    except ValueError:
        engine_enum = TranslationEngine.GOOGLE
        print_warning(f"Unknown engine '{args.engine}', falling back to Google.")

    # Setup pipeline based on mode
    if mode == "full":
        pipeline.configure(
            game_exe_path=input_path,
            target_language=args.target_lang,
            source_language=args.source_lang,
            engine=engine_enum,
            auto_unren=True,
            use_proxy=args.proxy,
            include_deep_scan=getattr(args, 'deep_scan', False),
            include_rpyc=getattr(args, 'rpyc', False)
        )
        QTimer.singleShot(0, pipeline.run)

    elif mode == "translate":
        def run_translation_wrapper():
            pipeline.include_deep_scan = getattr(args, 'deep_scan', False)
            pipeline.include_rpyc = getattr(args, 'rpyc', False)
            pipeline.use_proxy = args.proxy
            try:
                result = pipeline.translate_existing_tl(
                    tl_root_path=input_path,
                    target_language=args.target_lang,
                    source_language=args.source_lang,
                    engine=engine_enum,
                    use_proxy=args.proxy
                )
                handler.on_finished(result)
            except Exception as e:
                import traceback
                print_error(f"Error during translation: {e}")
                traceback.print_exc()
                QCoreApplication.quit()

        QTimer.singleShot(0, run_translation_wrapper)

    # Setup signal handling for graceful exit (Ctrl+C)
    signal.signal(signal.SIGINT, lambda *args: QCoreApplication.quit())

    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
