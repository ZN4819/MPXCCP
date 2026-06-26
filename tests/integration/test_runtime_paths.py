from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from mpxccp.config import paths
from mpxccp.config.settings import APP_NAME


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_user_data_path_is_not_install_directory(tmp_path, monkeypatch):
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData"))

    assert hasattr(paths, "resolve_user_data_path")
    path = paths.resolve_user_data_path("mpxccp.sqlite3")

    assert "AppData" in str(path)
    assert APP_NAME in str(path)
    assert path.name == "mpxccp.sqlite3"
    assert _project_root() not in path.parents


def test_packaging_scripts_call_expected_entrypoints():
    scripts_dir = _project_root() / "scripts"
    check_script = (scripts_dir / "check_resources.ps1").read_text(encoding="utf-8")
    build_script = (scripts_dir / "build_windows.ps1").read_text(encoding="utf-8")

    assert "mpxccp.integration.packaging.resource_check" in check_script
    assert "$LASTEXITCODE" in check_script

    assert "-m pytest" in build_script
    assert "check_resources.ps1" in build_script
    assert "-m PyInstaller" in build_script
    assert "--name" in build_script
    assert "MPXCCP" in build_script
    assert "--add-data" in build_script
    assert "mpxccp\\resources" in build_script


def test_packaging_template_directory_is_tracked():
    assert (_project_root() / "mpxccp" / "resources" / "templates" / ".keep").is_file()


def test_check_resources_script_propagates_missing_resource_exit_code(tmp_path):
    powershell = shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required for Windows packaging script verification")

    result = subprocess.run(
        [
            powershell,
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(_project_root() / "scripts" / "check_resources.ps1"),
            str(tmp_path),
        ],
        cwd=_project_root(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "styles/app.qss" in result.stdout
