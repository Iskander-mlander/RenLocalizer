# -*- coding: utf-8 -*-
"""
RenLocalizer Launcher
Cross-platform launcher for Windows and Unix systems
Now powered by Qt Quick (QML)
"""

import os
import sys
import warnings
import asyncio
import logging
import multiprocessing
import subprocess
import tempfile
import shutil
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING
from src.utils.logger import setup_logger
from src.utils.qt_runtime import (
    QtGraphicsBootstrapResult,
    build_qt_safe_relaunch_env,
    configure_qt_graphics_environment,
    should_attempt_qt_safe_relaunch,
)

if TYPE_CHECKING:
    from PyQt6.QtQml import QQmlApplicationEngine
    from PyQt6.QtWidgets import QApplication

# ============================================================
# SAFETY: Increase recursion limit for deep Ren'Py ASTs
# ============================================================
sys.setrecursionlimit(5000)

# Default version fallback
VERSION = "2.8.5"

try:
    from src.version import VERSION as _v
    VERSION = _v
except ImportError:
    # Fallback: if src is not in path (some IDEs/environments)
    import sys
    sys.path.append(os.path.dirname(__file__))
    try:
        from src.version import VERSION as _v
        VERSION = _v
    except ImportError:
        pass  # Keep default value

# ============================================================
# CRITICAL: Disable Qt system theme detection BEFORE any Qt imports
# This ensures the app uses its own theme regardless of Windows settings
# ============================================================
os.environ["QT_QPA_PLATFORM_THEME"] = ""  # Disable system theme
os.environ["QT_STYLE_OVERRIDE"] = ""  # Disable style override

os.environ["QT_QUICK_CONTROLS_STYLE"] = "Material"
# Keep startup fast: QML applies the saved app theme later via settingsBackend.
os.environ["QT_QUICK_CONTROLS_MATERIAL_THEME"] = "Dark"
os.environ["QT_QUICK_CONTROLS_MATERIAL_ACCENT"] = "Purple"

# Keep macOS layer-backed windows enabled even during direct binary relaunches.
if sys.platform == "darwin" and not os.environ.get("QT_MAC_WANTS_LAYER"):
    os.environ["QT_MAC_WANTS_LAYER"] = "1"

# ============================================================
# CRITICAL: High DPI support — MUST be set before any Qt imports
# Fixes blank/invisible window at 125%, 150%, 200% display scaling
# ============================================================
if sys.platform == "win32" and os.environ.get("RENLOCALIZER_FORCE_DPI_API", "0") == "1":
    try:
        import ctypes
        # Per-Monitor DPI Aware V2 — let Qt6 handle scaling natively
        # Without this, Windows DPI virtualization conflicts with Qt's own scaling
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            # Fallback for older Windows (8.0 and below)
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# ============================================================
# CRITICAL: Set AppUserModelId for Windows taskbar icon
# This MUST be done early, before any Qt/GUI initialization
# ============================================================
if sys.platform == "win32":
    try:
        import ctypes
        # Set explicitly for taskbar icon to appear immediately
        # Changed ID slightly to force Windows Icon Cache refresh
        myappid = "LordOfTurk.RenLocalizer.V2.QML"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass  # Silent fail is acceptable on non-Windows or old Windows versions

warnings.filterwarnings("ignore", category=SyntaxWarning, message=r".*invalid escape sequence.*")

# Ensure stdout/stderr use UTF-8 where possible
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# ============================================================
# GLOBAL EXCEPTION HANDLER
# ============================================================
def _resolve_crash_report_path() -> Path:
    """Return a writable crash report path, preferring the managed data dir."""
    candidates: list[Path] = []

    try:
        from src.utils.path_manager import ensure_data_directories, get_data_path

        data_path = get_data_path()
        ensure_data_directories(data_path)
        candidates.append(data_path / "logs" / "crash_report.log")
    except Exception:
        pass

    work_dir = globals().get("WORK_DIR")
    if isinstance(work_dir, Path):
        candidates.append(work_dir / "crash_report.log")

    candidates.append(Path.cwd() / "crash_report.log")
    candidates.append(Path(tempfile.gettempdir()) / "RenLocalizer-crash_report.log")

    seen: set[str] = set()
    for candidate in candidates:
        try:
            resolved_candidate = candidate.resolve()
        except Exception:
            resolved_candidate = candidate
        candidate_key = str(resolved_candidate)
        if candidate_key in seen:
            continue
        seen.add(candidate_key)
        try:
            resolved_candidate.parent.mkdir(parents=True, exist_ok=True)
            return resolved_candidate
        except Exception:
            continue

    return Path(tempfile.gettempdir()) / "RenLocalizer-crash_report.log"


def _append_crash_report(timestamp: str, error_msg: str) -> Path | None:
    """Write crash details to disk and return the effective report path."""
    crash_report_path = _resolve_crash_report_path()
    try:
        with open(crash_report_path, "a", encoding="utf-8") as f:
            f.write(f"\n{'=' * 60}\n[{timestamp}]\n{error_msg}\n")
        return crash_report_path
    except Exception:
        return None


def _show_native_startup_dialog(title: str, message: str) -> bool:
    """Try to show a native startup error dialog without depending on Qt."""
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
            return True
        except Exception:
            return False

    if sys.platform == "darwin" and shutil.which("osascript"):
        safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
        safe_message = message.replace("\\", "\\\\").replace('"', '\\"')
        script = f'display alert "{safe_title}" message "{safe_message}" as critical'
        try:
            subprocess.run(
                ["osascript", "-e", script],
                check=False,
                timeout=10,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            return False

    if sys.platform.startswith("linux"):
        dialog_commands: list[list[str]] = []
        if shutil.which("zenity"):
            dialog_commands.append(["zenity", "--error", "--title", title, "--text", message])
        if shutil.which("kdialog"):
            dialog_commands.append(["kdialog", "--error", message, "--title", title])

        for command in dialog_commands:
            try:
                subprocess.run(
                    command,
                    check=False,
                    timeout=10,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True
            except Exception:
                continue

    return False


def global_exception_handler(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
) -> None:
    """Catch all unhandled exceptions and show a user-friendly dialog."""
    import traceback
    import datetime
    
    if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    crash_report_path = _append_crash_report(timestamp, error_msg)
    crash_report_note = (
        f"Crash report: {crash_report_path}"
        if crash_report_path is not None
        else "Crash report could not be written to disk."
    )
    dialog_message = f"Bir hata oluştu:\n\n{exc_value}\n\n{crash_report_note}"

    if not _show_native_startup_dialog("RenLocalizer Hatası", dialog_message):
        print(error_msg)
        print(crash_report_note)
    
    # Call original handler
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = global_exception_handler


def show_error_and_wait(title: str, message: str) -> None:
    """Show error message and wait for user input (works without Qt)."""
    print(f"\n{'=' * 60}")
    print(f"ERROR: {title}")
    print("=" * 60)
    print(message)
    print("=" * 60)

    dialog_shown = _show_native_startup_dialog(title, message)

    # Keep console open
    if sys.stdin is not None and sys.stdin.isatty():
        print("\nPress Enter to close...")
        try:
            input()
        except Exception:
            import time

            time.sleep(10)
    elif not dialog_shown:
        import time

        time.sleep(10)


def check_windows_version() -> bool:
    """Check if Windows version is compatible."""
    if sys.platform != "win32":
        return True

    try:
        import platform
        machine = platform.machine()
        # Check for 64-bit
        if machine not in ["AMD64", "x86_64"]:
            show_error_and_wait(
                "Unsupported Architecture",
                f"RenLocalizer requires 64-bit Windows.\nYour system: {machine}"
            )
            return False
        return True
    except Exception as e:
        print(f"Warning: Could not check Windows version: {e}")
        return True


def check_vcruntime() -> bool:
    """Check if Visual C++ Runtime is installed (Windows only)."""
    if sys.platform != "win32":
        return True

    import ctypes
    required_dlls = ["vcruntime140.dll", "msvcp140.dll"]
    missing_dlls = []

    for dll_name in required_dlls:
        try:
            ctypes.WinDLL(dll_name)
        except OSError:
            missing_dlls.append(dll_name)

    if missing_dlls:
        show_error_and_wait(
            "RenLocalizer - Missing Runtime",
            f"RenLocalizer requires Microsoft Visual C++ Redistributable.\n\n"
            f"Missing: {', '.join(missing_dlls)}\n\n"
            "Please install Visual C++ Redistributable 2015-2022 (x64)."
        )
        return False
    return True


def get_base_dir() -> Path:
    """Get the base directory where the executable/script resides (for config/logs)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent

def resolve_asset_path(path: str | Path) -> Path:
    """Resolve an asset path, checking _MEIPASS for PyInstaller bundles."""
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            # OneFile mode: Use temp folder
            base = Path(sys._MEIPASS)
        else:
            # OneDir mode: Use executable directory
            base = Path(sys.executable).parent
    else:
        # Development mode
        base = Path(__file__).parent
        
    return base / path

# Set working directory to where the executable is (for relative config/output paths)
WORK_DIR = get_base_dir()
os.chdir(WORK_DIR)

# Add project root to Python path (for imports)
sys.path.insert(0, str(WORK_DIR))


def setup_qt_environment() -> None:
    """Setup Qt environment variables for frozen exe."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if not meipass:
            return

        meipass_path = Path(meipass)
        
        # Add DLL directories (Python 3.8+)
        if hasattr(os, "add_dll_directory"):
            dll_paths = [
                meipass_path,
                meipass_path / "PyQt6" / "Qt6" / "bin",
            ]
            for dll_path in dll_paths:
                if dll_path.exists():
                    try:
                        os.add_dll_directory(str(dll_path))
                    except:
                        pass

        # Set QT_PLUGIN_PATH
        plugin_paths = [
            meipass_path / "PyQt6" / "Qt6" / "plugins",
            meipass_path / "PyQt6" / "plugins",
        ]
        existing_plugin_paths = [str(p) for p in plugin_paths if p.exists()]
        if existing_plugin_paths:
            os.environ["QT_PLUGIN_PATH"] = os.pathsep.join(existing_plugin_paths)

        # Disable noisy Qt font warnings
        os.environ["QT_LOGGING_RULES"] = "qt.qpa.fonts=false;qt.text.font.db=false;*.debug=false"


def check_unix_system() -> bool:
    if sys.platform == "win32": return True
    return True


SCENEGRAPH_RECOVERY_EXIT_CODE = 213


def _is_qt_smoke_test_enabled() -> bool:
    return os.environ.get("RENLOCALIZER_QT_SMOKE_TEST", "0") == "1"


def _get_qt_smoke_test_delay_ms() -> int:
    raw_value = os.environ.get("RENLOCALIZER_QT_SMOKE_TEST_DELAY_MS", "400")
    try:
        return max(100, int(raw_value))
    except ValueError:
        return 400


def _get_current_launch_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, *sys.argv[1:]]
    return [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]]


def _wire_qml_shutdown_order(
    app: "QApplication",
    engine: "QQmlApplicationEngine",
) -> None:
    """Tear down the QML engine before app-owned backend objects disappear."""
    teardown_scheduled = False

    def _schedule_engine_teardown() -> None:
        nonlocal teardown_scheduled
        if teardown_scheduled:
            return
        teardown_scheduled = True
        engine.deleteLater()

    app.lastWindowClosed.connect(_schedule_engine_teardown)
    app.aboutToQuit.connect(_schedule_engine_teardown)


def _setup_completion_notification_tray(app, backend, app_icon):
    """Install an optional native desktop notification path.

    Uses Qt's system tray support when available and silently falls back to the
    existing in-app completion dialog on platforms/desktops without tray support.
    """
    try:
        from PyQt6.QtWidgets import QSystemTrayIcon
    except Exception:
        return None

    try:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return None

        tray_icon = QSystemTrayIcon(app_icon, app)
        tray_icon.setToolTip("RenLocalizer")
        tray_icon.show()

        def _show_completion_notification(title, message, output_path, diagnostic_path, review_note_count):
            try:
                lines = [message]
                if review_note_count:
                    lines.append(f"Review notes: {review_note_count}")
                if output_path:
                    lines.append(Path(output_path).name)
                tray_icon.showMessage(
                    title,
                    "\n".join(line for line in lines if line),
                    QSystemTrayIcon.MessageIcon.Information,
                    8000,
                )
            except Exception:
                pass

        backend.completionSummary.connect(_show_completion_notification)
        return tray_icon
    except Exception:
        return None


def _attempt_qt_safe_relaunch(
    logger: logging.Logger,
    stage: str,
    detail: str,
    graphics_bootstrap: QtGraphicsBootstrapResult,
) -> int | None:
    if not should_attempt_qt_safe_relaunch(
        env=os.environ,
        platform_name=sys.platform,
        bootstrap=graphics_bootstrap,
    ):
        return None

    safe_env = build_qt_safe_relaunch_env(
        env=os.environ,
        platform_name=sys.platform,
    )
    safe_platform = safe_env.get("QT_QPA_PLATFORM", "native")
    message = (
        f"Qt startup failed during {stage}; relaunching once in safe mode "
        f"(platform={safe_platform}, render={safe_env.get('RENLOCALIZER_QT_RENDER_MODE', 'native')})"
    )
    print(f"[WARN] {message}")
    if detail:
        print(f"[WARN] Failure detail: {detail}")
    logger.warning(message)
    if detail:
        logger.warning("Qt startup failure detail: %s", detail)

    return subprocess.call(
        _get_current_launch_command(),
        cwd=str(WORK_DIR),
        env=safe_env,
    )


def main() -> int:
    print("=" * 60)
    print("RenLocalizer (Qt Quick Edition) Starting...")
    print("=" * 60)

    # Initialize Secure Logger
    logger = setup_logger()
    logger.info(f"RenLocalizer Starting... Version: {VERSION}")

    setup_qt_environment()

    graphics_bootstrap = configure_qt_graphics_environment(
        frozen=bool(getattr(sys, "frozen", False))
    )
    graphics_summary = (
        f"Qt graphics bootstrap: platform={sys.platform}, mode={graphics_bootstrap.mode}, "
        f"api={graphics_bootstrap.graphics_api or 'native'}, "
        f"plugin={graphics_bootstrap.platform_plugin or 'native'}, "
        f"scale={graphics_bootstrap.scale_percent}%, reason={graphics_bootstrap.reason}"
    )
    print(f"[INFO] {graphics_summary}")
    logger.info(graphics_summary)
    if graphics_bootstrap.applied:
        logger.info("Applied Qt graphics env: %s", graphics_bootstrap.applied)
    
    # Check system requirements
    if sys.platform == "win32":
        if not check_windows_version(): return 1
        if not check_vcruntime(): return 1
    else:
        check_unix_system()

    print("\nLoading Qt framework...")

    try:
        # Import Qt
        from PyQt6.QtCore import QTimer, QUrl, Qt
        from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
        from PyQt6.QtQuick import QQuickWindow, QSGRendererInterface
        from PyQt6.QtWidgets import QApplication, QSplashScreen
        from PyQt6.QtQml import QQmlApplicationEngine

        if graphics_bootstrap.graphics_api == "opengl":
            QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.OpenGL)
        elif graphics_bootstrap.graphics_api == "software":
            QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Software)

        # High DPI: Use PassThrough rounding so 150%/200% scales are not
        # rounded to integer multiples, preventing layout overflow and blank windows
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        # Use QApplication for better desktop integration (Icons, Taskbar, etc.)
        app = QApplication(sys.argv)
        app.setApplicationName("RenLocalizer")
        app.setOrganizationName("LordOfTurk")

        # Show a lightweight splash screen immediately so slow startup work
        # does not look like a frozen launch.
        splash_pixmap_path = resolve_asset_path("icon.png")
        if splash_pixmap_path.exists():
            splash_pixmap = QPixmap(str(splash_pixmap_path))
        else:
            splash_pixmap = QPixmap(480, 280)
        if splash_pixmap.isNull():
            splash_pixmap = QPixmap(480, 280)
        if splash_pixmap.isNull() or splash_pixmap.size().isEmpty():
            splash_pixmap.fill(QColor("#121224"))
            painter = QPainter(splash_pixmap)
            try:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                painter.setPen(QColor("#ffffff"))
                title_font = QFont()
                title_font.setPointSize(28)
                title_font.setBold(True)
                painter.setFont(title_font)
                painter.drawText(splash_pixmap.rect(), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, "RenLocalizer")
                painter.setFont(QFont())
                painter.drawText(splash_pixmap.rect().adjusted(0, 60, 0, 0), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, "Loading application...")
            finally:
                painter.end()

        splash = QSplashScreen(splash_pixmap, Qt.WindowType.WindowStaysOnTopHint)
        splash.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)

        splash_phase_text = "Loading RenLocalizer"
        splash_dot_count = 0

        def _update_splash_message(new_phase: str | None = None) -> None:
            nonlocal splash_phase_text, splash_dot_count
            if new_phase is not None:
                splash_phase_text = new_phase
                splash_dot_count = 0
            dots = "." * splash_dot_count
            splash.showMessage(
                f"{splash_phase_text}{dots}",
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                Qt.GlobalColor.white,
            )
            splash_dot_count = (splash_dot_count + 1) % 4

        splash_timer = QTimer()
        splash_timer.timeout.connect(_update_splash_message)
        splash.show()
        app.processEvents()
        splash_timer.start(250)
        _update_splash_message()

        # ── Linux emoji font registration ────────────────────────
        # Bundle carries NotoColorEmoji.ttf in fonts/ directory.
        # Register it via QFontDatabase so Qt can render emoji icons
        # (navigation bar, tools page, toast notifications) on distros
        # that lack a system color emoji font.
        emoji_font_family = ""
        if sys.platform != "win32":
            from PyQt6.QtGui import QFontDatabase
            _font_candidates = [
                resolve_asset_path("fonts") / "NotoColorEmoji.ttf",
                resolve_asset_path("fonts") / "NotoEmoji-Regular.ttf",
                Path("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"),
                Path("/usr/share/fonts/truetype/google-noto/NotoColorEmoji.ttf"),
                Path("/usr/share/fonts/opentype/noto/NotoColorEmoji.ttf"),
                Path("/usr/share/fonts/noto/NotoColorEmoji.ttf"),
                Path("/usr/share/fonts/truetype/noto/NotoEmoji-Regular.ttf"),
            ]
            _registered_fonts: set[Path] = set()
            for _font_path in _font_candidates:
                if not _font_path.exists() or _font_path in _registered_fonts:
                    continue
                fid = QFontDatabase.addApplicationFont(str(_font_path))
                if fid >= 0:
                    _registered_fonts.add(_font_path)
                    if not emoji_font_family:
                        font_families = QFontDatabase.applicationFontFamilies(fid)
                        if font_families:
                            emoji_font_family = font_families[0]
                    logger.debug("Registered emoji font: %s", _font_path.name)
                else:
                    logger.warning("Failed to register emoji font: %s", _font_path)
            if not _registered_fonts:
                logger.info(
                    "No emoji font registered for Qt. Linux source runs may "
                    "show fallback icons until a system emoji font such as "
                    "Noto Color Emoji is installed."
                )

        _update_splash_message("Preparing the application")
        app.processEvents()
        
        # Import Backends (Logic)
        from src.utils.config import ConfigManager
        from src.backend.app_backend import AppBackend
        from src.backend.settings_backend import SettingsBackend
        
        app.setApplicationVersion(VERSION)

        _update_splash_message("Loading user settings")
        app.processEvents()

        # Set application icon
        # Primary: icon.png (Linux/macOS), Fallback: icon.ico (Windows)
        potential_icons = ["icon.png", "icon.ico"]
        app_icon = QIcon()
        
        for icon_name in potential_icons:
            icon_path = resolve_asset_path(icon_name)
            if icon_path.exists():
                print(f"[INFO] Loading icon from: {icon_path}")
                temp_icon = QIcon(str(icon_path))
                if not temp_icon.isNull():
                    app_icon = temp_icon
                    app.setWindowIcon(app_icon)
                    print(f"[INFO] {icon_name} loaded successfully.")
                    break
        
        if app_icon.isNull():
             print("[WARNING] No suitable icon file found or failed to load.")

        # Initialize Logic
        config_manager = ConfigManager()
        backend = AppBackend(
            config_manager,
            emoji_font_family=emoji_font_family,
            parent=app,
        )
        settings_backend = SettingsBackend(
            config_manager,
            proxy_manager=backend.proxy_manager,
            parent=app,
        )
        
        # Link backends for signal propagation (Localization refresh)
        settings_backend.languageChanged.connect(backend.refreshUI)
        settings_backend.themeChanged.connect(backend.refreshUI)

        # Optional native desktop notification path for completion events.
        # Falls back to the existing in-app dialog on desktops without tray support.
        _completion_tray = _setup_completion_notification_tray(app, backend, app_icon)

        # Create QML Engine
        engine = QQmlApplicationEngine(app)
        _wire_qml_shutdown_order(app, engine)

        # Expose Backends to QML
        engine.rootContext().setContextProperty("backend", backend)
        engine.rootContext().setContextProperty("settingsBackend", settings_backend)

        # Error Handling for QML
        def on_object_created(obj, url) -> None:
            if obj is None:
                print(f"[FATAL ERROR] Failed to load QML: {url}")
                app.exit(-1)

        engine.objectCreated.connect(on_object_created)

        # Load MAIN QML
        # Use resolve_asset_path so it works inside PyInstaller bundle
        qml_path = resolve_asset_path("src/gui/qml/main.qml")
        _update_splash_message("Starting the interface")
        app.processEvents()
        print(f"Loading UI: {qml_path}")
        
        if not qml_path.exists():
            print(f"[ERROR] QML file not found: {qml_path}")
            # Do not exit here, let engine.load fail gracefully or handled below
        
        # Important: Add QML root to import paths so imports work in frozen exe
        qml_root = resolve_asset_path("src/gui/qml")
        engine.addImportPath(str(qml_root))

        engine.load(QUrl.fromLocalFile(str(qml_path)))

        if not engine.rootObjects():
            print("[ERROR] No root objects created.")
            splash_timer.stop()
            splash.close()
            safe_exit = _attempt_qt_safe_relaunch(
                logger=logger,
                stage="qml_load",
                detail=f"qml={qml_path}",
                graphics_bootstrap=graphics_bootstrap,
            )
            if safe_exit is not None:
                return safe_exit
            return 1

        # Force icon on the root window (Fix for Windows taskbar)
        if engine.rootObjects():
            root_window = engine.rootObjects()[0]
            recovery_requested = False
            recovery_detail = ""

            if hasattr(root_window, "sceneGraphError"):
                def _handle_scene_graph_error(error: object, message: str) -> None:
                    nonlocal recovery_requested, recovery_detail
                    logger.error("Qt scene graph error (%s): %s", error, message)
                    print(f"[ERROR] Qt scene graph error ({error}): {message}")
                    if should_attempt_qt_safe_relaunch(
                        env=os.environ,
                        platform_name=sys.platform,
                        bootstrap=graphics_bootstrap,
                    ):
                        recovery_requested = True
                        recovery_detail = message
                        QTimer.singleShot(0, lambda: app.exit(SCENEGRAPH_RECOVERY_EXIT_CODE))

                root_window.sceneGraphError.connect(_handle_scene_graph_error)
            
            # Use native PyQt6 setIcon on QQuickWindow directly
            if not app_icon.isNull():
                root_window.setIcon(app_icon)
            
            # Step 1: Show window FIRST so Windows creates a real HWND
            root_window.show()
            app.processEvents()
            splash_timer.stop()
            splash.close()
            
            # Step 2: Apply native Windows icon via ctypes (most reliable for taskbar)
            icon_path = resolve_asset_path("icon.ico")
            if sys.platform == "win32" and icon_path.exists():
                def _apply_native_icon() -> None:
                    """Apply icon via Win32 API after HWND is fully initialized."""
                    try:
                        import ctypes
                        
                        user32 = ctypes.windll.user32
                        WM_SETICON = 0x80
                        ICON_SMALL = 0  # 16x16 — title bar, taskbar
                        ICON_BIG = 1    # 32x32 — Alt+Tab, taskbar hover
                        
                        # Get HWND with proper int cast (winId() returns sip.voidptr)
                        hwnd = int(root_window.winId())
                        if not hwnd:
                            print("[WARNING] HWND is 0, window not yet realized")
                            return
                        
                        icon_str = str(icon_path)
                        # LR_LOADFROMFILE = 0x10, IMAGE_ICON = 1
                        # Explicit sizes: 16x16 for small, 32x32 for big
                        h_icon_small = user32.LoadImageW(
                            None, icon_str, 1, 16, 16, 0x10
                        )
                        h_icon_big = user32.LoadImageW(
                            None, icon_str, 1, 32, 32, 0x10
                        )
                        
                        if h_icon_small:
                            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_icon_small)
                        if h_icon_big:
                            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_icon_big)
                            
                    except Exception as e:
                        print(f"[WARNING] Failed to set native Windows icon: {e}")
                
                # Apply immediately after show
                _apply_native_icon()
                
                # Insurance: reapply with escalating delays in case QML recreates the window handle
                # First retry after 200ms, second after 500ms (covers slow systems & QML layout passes)
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(200, _apply_native_icon)
                QTimer.singleShot(500, _apply_native_icon)
            
            # Re-apply Qt icon after QML finishes initialization (cross-platform)
            if not app_icon.isNull():
                from PyQt6.QtCore import QTimer
                def _reapply_qt_icon() -> None:
                    root_window.setIcon(app_icon)
                    app.setWindowIcon(app_icon)
                QTimer.singleShot(100, _reapply_qt_icon)
            
            # Process events to flush all icon changes
            app.processEvents()

            if _is_qt_smoke_test_enabled():
                smoke_delay_ms = _get_qt_smoke_test_delay_ms()
                logger.info("Qt smoke test enabled; exiting after %sms", smoke_delay_ms)
                print(f"[INFO] Qt smoke test enabled; exiting after {smoke_delay_ms}ms")

                def _smoke_exit():
                    try:
                        graphics_api = root_window.rendererInterface().graphicsApi()
                        graphics_api_name = getattr(graphics_api, "name", str(graphics_api))
                        logger.info("Qt Quick graphics API in use: %s", graphics_api_name)
                        print(f"[INFO] Qt Quick graphics API in use: {graphics_api_name}")
                    except Exception as exc:
                        logger.debug("Could not query Qt Quick graphics API: %s", exc)
                    root_window.close()
                    app.quit()

                QTimer.singleShot(smoke_delay_ms, _smoke_exit)
            else:
                def _query_graphics_api():
                    try:
                        graphics_api = root_window.rendererInterface().graphicsApi()
                        graphics_api_name = getattr(graphics_api, "name", str(graphics_api))
                        logger.info("Qt Quick graphics API in use: %s", graphics_api_name)
                        print(f"[INFO] Qt Quick graphics API in use: {graphics_api_name}")
                    except Exception as exc:
                        logger.debug("Could not query Qt Quick graphics API: %s", exc)

                QTimer.singleShot(0, _query_graphics_api)

        print("[OK] UI loaded successfully. Entering event loop.")
        exit_code = app.exec()
        if exit_code == SCENEGRAPH_RECOVERY_EXIT_CODE and recovery_requested:
            safe_exit = _attempt_qt_safe_relaunch(
                logger=logger,
                stage="scene_graph_error",
                detail=recovery_detail,
                graphics_bootstrap=graphics_bootstrap,
            )
            if safe_exit is not None:
                return safe_exit
        
        # ============================================================
        # CLEANUP: Graceful asyncio shutdown (Windows WinError 10022 fix)
        # ============================================================
        try:
            # Close any open aiohttp sessions before event loop cleanup
            if hasattr(backend, 'translation_manager'):
                backend.translation_manager.close_all_sessions()
        except Exception as cleanup_error:
            logger.debug(f"Asyncio cleanup warning: {cleanup_error}")

        try:
            # Cancel pending asyncio tasks without run_until_complete —
            # Qt event loop is already gone at this point; calling
            # run_until_complete here causes SIGABRT in PyInstaller Linux builds.
            # get_running_loop() raises RuntimeError when no loop is running (expected here).
            # get_event_loop() is deprecated in 3.10+ in this context, so we use
            # the policy directly as a best-effort cleanup.
            try:
                loop = asyncio.get_event_loop_policy().get_event_loop()
                if loop and not loop.is_closed():
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    loop.close()
            except Exception:
                pass
        except Exception as cleanup_error:
            logger.debug(f"Asyncio cleanup warning: {cleanup_error}")
        
        return exit_code

    except Exception as e:
        error_msg = f"Error starting RenLocalizer: {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()

        safe_exit = _attempt_qt_safe_relaunch(
            logger=logger,
            stage="startup_exception",
            detail=error_msg,
            graphics_bootstrap=graphics_bootstrap,
        )
        if safe_exit is not None:
            return safe_exit

        show_error_and_wait(
            "RenLocalizer - Startup Error",
            f"{error_msg}\n\nCheck logs for details."
        )
        return 1


if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
