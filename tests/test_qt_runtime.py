from pathlib import Path

from src.utils.qt_runtime import (
    QtGraphicsBootstrapResult,
    build_qt_safe_relaunch_env,
    configure_qt_graphics_environment,
    configure_windows_qt_graphics_environment,
    select_qt_platform_plugin,
    select_qt_render_mode,
    select_windows_qt_render_mode,
    should_attempt_qt_safe_relaunch,
)


def test_select_windows_qt_render_mode_uses_software_for_hidpi():
    assert select_windows_qt_render_mode(150) == "software"


def test_select_windows_qt_render_mode_uses_opengl_for_standard_scale():
    assert select_windows_qt_render_mode(100) == "opengl"


def test_select_qt_render_mode_keeps_linux_native_by_default():
    assert select_qt_render_mode("linux", 200) == "native"


def test_select_qt_platform_plugin_prefers_xcb_first_for_frozen_mixed_linux_sessions():
    env = {"DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-0"}
    assert select_qt_platform_plugin(env, "linux", frozen=True) == "xcb;wayland"


def test_configure_windows_qt_graphics_environment_applies_software_mode():
    env: dict[str, str] = {}
    result = configure_windows_qt_graphics_environment(
        env=env,
        platform_name="win32",
        scale_percent=150,
    )

    assert result.mode == "software"
    assert env["QSG_RHI_BACKEND"] == "opengl"
    assert env["QT_OPENGL"] == "software"
    assert result.graphics_api == "opengl"


def test_configure_windows_qt_graphics_environment_respects_native_override():
    env = {"RENLOCALIZER_QT_RENDER_MODE": "native"}
    result = configure_windows_qt_graphics_environment(
        env=env,
        platform_name="win32",
        scale_percent=175,
    )

    assert result.mode == "native"
    assert result.applied == {}
    assert "QSG_RHI_BACKEND" not in env


def test_configure_windows_qt_graphics_environment_respects_existing_qt_env():
    env = {"QSG_RHI_BACKEND": "vulkan"}
    result = configure_windows_qt_graphics_environment(
        env=env,
        platform_name="win32",
        scale_percent=150,
    )

    assert result.mode == "native"
    assert result.reason == "qt graphics env already overridden"
    assert env["QSG_RHI_BACKEND"] == "vulkan"


def test_windows_spec_bundles_software_opengl_dll():
    spec_text = Path("RenLocalizer.spec").read_text(encoding="utf-8")
    assert "opengl32sw.dll" in spec_text


def test_spec_bundles_png_icon_for_non_windows_qml_surfaces():
    spec_text = Path("RenLocalizer.spec").read_text(encoding="utf-8")
    assert "(os.path.join(project_dir, 'icon.png'), '.')" in spec_text


def test_run_launcher_shows_loading_splash():
    run_text = Path("run.py").read_text(encoding="utf-8")
    assert "QSplashScreen" in run_text
    assert "Loading RenLocalizer" in run_text


def test_linux_apprun_generates_runtime_fontconfig_without_in_place_patch():
    apprun_text = Path("build/linux/AppRun").read_text(encoding="utf-8")
    assert "mktemp -d" in apprun_text
    assert "FONTCONFIG_FILE" in apprun_text
    assert "sed -i" not in apprun_text


def test_macos_bundle_script_updates_plist_with_plistlib_instead_of_sed():
    script_text = Path("build/macos/create_app_bundle.sh").read_text(encoding="utf-8")
    assert "plistlib" in script_text
    assert "sed -i.bak" not in script_text


def test_macos_bundle_script_does_not_write_png_as_invalid_icns_fallback():
    script_text = Path("build/macos/create_app_bundle.sh").read_text(encoding="utf-8")
    assert 'cp "$ICONSET_DIR/icon_256x256.png" "$APP_PATH/Contents/Resources/icon.icns"' not in script_text


def test_configure_qt_graphics_environment_prefers_xcb_wayland_on_frozen_linux():
    env = {"DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-0"}
    result = configure_qt_graphics_environment(
        env=env,
        platform_name="linux",
        scale_percent=200,
        frozen=True,
    )

    assert result.mode == "native"
    assert result.platform_plugin == "xcb;wayland"
    assert env["QT_QPA_PLATFORM"] == "xcb;wayland"
    assert result.graphics_api is None


def test_configure_qt_graphics_environment_honors_internal_platform_hint_without_marking_user_override():
    env = {
        "DISPLAY": ":0",
        "WAYLAND_DISPLAY": "wayland-0",
        "RENLOCALIZER_QT_PLATFORM_HINT": "xcb;wayland",
    }
    result = configure_qt_graphics_environment(
        env=env,
        platform_name="linux",
        scale_percent=100,
        frozen=True,
    )

    assert result.platform_plugin == "xcb;wayland"
    assert result.reason == "automatic safe graphics bootstrap"


def test_configure_qt_graphics_environment_supports_linux_software_fallback():
    env = {"RENLOCALIZER_QT_RENDER_MODE": "software"}
    result = configure_qt_graphics_environment(
        env=env,
        platform_name="linux",
        scale_percent=100,
    )

    assert result.mode == "software"
    assert result.graphics_api == "software"
    assert env["QT_QUICK_BACKEND"] == "software"


def test_configure_qt_graphics_environment_respects_existing_qpa_platform_but_still_applies_render_mode():
    env = {
        "QT_QPA_PLATFORM": "xcb",
        "RENLOCALIZER_QT_RENDER_MODE": "software",
    }
    result = configure_qt_graphics_environment(
        env=env,
        platform_name="linux",
        scale_percent=100,
    )

    assert result.platform_plugin == "xcb"
    assert result.graphics_api == "software"
    assert env["QT_QPA_PLATFORM"] == "xcb"
    assert env["QT_QUICK_BACKEND"] == "software"


def test_configure_windows_qt_graphics_environment_is_noop_on_linux():
    env: dict[str, str] = {}
    result = configure_windows_qt_graphics_environment(
        env=env,
        platform_name="linux",
        scale_percent=200,
    )

    assert result.mode == "native"
    assert result.applied == {}
    assert env == {}


def test_configure_windows_qt_graphics_environment_is_noop_on_macos():
    env: dict[str, str] = {}
    result = configure_windows_qt_graphics_environment(
        env=env,
        platform_name="darwin",
        scale_percent=200,
    )

    assert result.mode == "native"
    assert result.applied == {}
    assert env == {}


def test_should_attempt_qt_safe_relaunch_for_default_linux_startup():
    assert should_attempt_qt_safe_relaunch(env={}, platform_name="linux") is True


def test_should_not_attempt_qt_safe_relaunch_when_user_forced_platform_or_render_mode():
    assert should_attempt_qt_safe_relaunch(
        env={"RENLOCALIZER_QT_RENDER_MODE": "software"},
        platform_name="linux",
    ) is False
    assert should_attempt_qt_safe_relaunch(
        env={"QT_QPA_PLATFORM": "xcb"},
        platform_name="linux",
    ) is False


def test_should_still_attempt_qt_safe_relaunch_when_only_internal_platform_hint_exists():
    assert should_attempt_qt_safe_relaunch(
        env={"RENLOCALIZER_QT_PLATFORM_HINT": "xcb;wayland"},
        platform_name="linux",
    ) is True


def test_should_still_attempt_qt_safe_relaunch_when_platform_plugin_was_auto_applied():
    bootstrap = QtGraphicsBootstrapResult(
        mode="native",
        scale_percent=100,
        applied={"QT_QPA_PLATFORM": "xcb;wayland"},
        reason="automatic safe graphics bootstrap",
        graphics_api=None,
        platform_plugin="xcb;wayland",
    )
    assert should_attempt_qt_safe_relaunch(
        env={"QT_QPA_PLATFORM": "xcb;wayland"},
        platform_name="linux",
        bootstrap=bootstrap,
    ) is True


def test_build_qt_safe_relaunch_env_for_linux_prefers_xcb_and_software():
    env = {
        "DISPLAY": ":0",
        "WAYLAND_DISPLAY": "wayland-0",
        "RENLOCALIZER_QT_PLATFORM_HINT": "xcb;wayland",
        "QSG_RHI_BACKEND": "opengl",
    }
    safe_env = build_qt_safe_relaunch_env(env=env, platform_name="linux")

    assert safe_env["RENLOCALIZER_QT_RECOVERY_ATTEMPT"] == "1"
    assert safe_env["RENLOCALIZER_QT_RENDER_MODE"] == "software"
    assert safe_env["QT_QPA_PLATFORM"] == "xcb"
    assert "QSG_RHI_BACKEND" not in safe_env
    assert "RENLOCALIZER_QT_PLATFORM_HINT" not in safe_env
