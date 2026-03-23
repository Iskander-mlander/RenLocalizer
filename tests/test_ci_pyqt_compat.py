from pathlib import Path

import yaml


def test_requirements_use_pyqt6_compatibility_range() -> None:
    requirements = Path("requirements.txt").read_text(encoding="utf-8")

    assert "PyQt6>=6.6,<6.11" in requirements
    assert "constraints-release.txt" in requirements


def test_release_constraints_pin_packaged_builds() -> None:
    constraints = Path("constraints-release.txt").read_text(encoding="utf-8")

    assert "PyQt6==6.10.1" in constraints
    assert "PyQt6-Qt6==6.10.1" in constraints
    assert "PyQt6-sip==13.10.3" in constraints


def test_dev_requirements_include_test_tools() -> None:
    dev_requirements = Path("requirements-dev.txt").read_text(encoding="utf-8")

    assert "pytest>=8.0,<9.0" in dev_requirements
    assert "tox>=4.0,<5.0" in dev_requirements


def test_release_workflow_uses_release_constraints() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/release.yml").read_text(encoding="utf-8"))

    for job_name in ("build-windows", "build-linux", "build-macos"):
        install_steps = [s for s in workflow["jobs"][job_name]["steps"] if "Install" in s.get("name", "")]
        joined = "\n".join(step.get("run", "") for step in install_steps)
        assert "constraints-release.txt -r requirements.txt" in joined


def test_tests_workflow_has_python_and_pyqt_matrices() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/tests.yml").read_text(encoding="utf-8"))

    core_matrix = workflow["jobs"]["core-regression"]["strategy"]["matrix"]
    compat_matrix = workflow["jobs"]["linux-pyqt-compat"]["strategy"]["matrix"]

    assert core_matrix["python-version"] == ["3.10", "3.11", "3.12"]
    assert [entry["pyqt6-version"] for entry in compat_matrix["include"]] == ["6.6.1", "6.7.1", "6.8.1", "6.9.1", "6.10.1"]

    for job_name in ("core-regression", "linux-pyqt-compat"):
        install_steps = [s for s in workflow["jobs"][job_name]["steps"] if s.get("name") == "Install Python dependencies"]
        assert len(install_steps) == 1
        assert "pip install -r requirements-dev.txt" in install_steps[0]["run"]

    compat_install = [s for s in workflow["jobs"]["linux-pyqt-compat"]["steps"] if s.get("name") == "Install Python dependencies"][0]["run"]
    assert "pip uninstall -y PyQt6 PyQt6-Qt6 PyQt6-sip || true" in compat_install
    assert 'PyQt6-Qt6${{ matrix.pyqt6_qt6_spec }}' in compat_install
    assert 'PyQt6-sip${{ matrix.pyqt6_sip_spec }}' in compat_install


def test_tests_workflow_runs_qt_smoke_test_from_source() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/tests.yml").read_text(encoding="utf-8"))

    for job_name in ("core-regression", "linux-pyqt-compat"):
        smoke_steps = [s for s in workflow["jobs"][job_name]["steps"] if s.get("name") == "Smoke test source Qt startup"]
        assert len(smoke_steps) == 1
        assert 'RENLOCALIZER_QT_SMOKE_TEST="1"' in smoke_steps[0]["run"]
        assert '"xvfb-run", "-a", "python", "run.py"' in smoke_steps[0]["run"]


def test_tox_matrix_covers_release_and_pyqt_compat() -> None:
    tox_path = Path("tox.ini")
    if not tox_path.exists():
        return

    tox_ini = tox_path.read_text(encoding="utf-8")

    assert "envlist = py{310,311,312}-release, py311-pyqt{66,67,68,69,610}" in tox_ini
    assert "release: -cconstraints-release.txt" in tox_ini
    assert "PyQt6==6.6.1" in tox_ini
    assert "PyQt6==6.10.1" in tox_ini
    assert "tests/test_ci_pyqt_compat.py -q" in tox_ini


def test_settings_page_exposes_extended_batch_range_and_cap_note() -> None:
    qml = Path("src/gui/qml/pages/SettingsPage.qml").read_text(encoding="utf-8")

    assert "to: settingsBackend.getBatchSizeMax()" in qml
    assert "stepSize: 100" in qml
    assert 'batch_size_engine_cap_note' in qml
    assert 'batch_size_effective_note' in qml
    assert 'to: settingsBackend.getAIBatchSizeMax()' in qml
    assert 'ai_batch_limit_note' in qml
    assert 'ai_batch_large_warning' in qml


def test_all_locales_include_batch_cap_messages() -> None:
    required = {
        "batch_size_engine_cap_note",
        "batch_size_effective_note",
        "log_batch_size_engine_cap_applied",
        "ai_batch_limit_note",
        "ai_batch_large_warning",
        "log_ai_batch_large_notice",
    }

    for path in Path("locales").glob("*.json"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        missing = required.difference(data)
        assert not missing, f"{path.name} missing: {sorted(missing)}"
