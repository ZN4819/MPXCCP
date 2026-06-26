from mpxccp.integration.packaging import resource_check
from mpxccp.integration.packaging.resource_check import required_resources, validate_resources


def test_required_resources_are_declared():
    resources = required_resources()

    assert "styles/app.qss" in resources
    assert "icons/app.png" in resources
    assert "templates/.keep" in resources


def test_validate_resources_returns_missing_relative_paths(tmp_path):
    missing = validate_resources(tmp_path)

    assert missing == required_resources()


def test_validate_resources_accepts_present_files(tmp_path):
    for relative_path in required_resources():
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"present")

    assert validate_resources(tmp_path) == []


def test_resource_check_main_returns_nonzero_for_missing_resources(tmp_path, capsys):
    exit_code = resource_check.main([str(tmp_path)])

    assert exit_code == 1
    assert "styles/app.qss" in capsys.readouterr().out


def test_resource_check_main_returns_zero_for_present_resources(tmp_path, capsys):
    for relative_path in required_resources():
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"present")

    exit_code = resource_check.main([str(tmp_path)])

    assert exit_code == 0
    assert "resource check passed" in capsys.readouterr().out
