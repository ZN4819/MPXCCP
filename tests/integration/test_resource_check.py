from mpxccp.integration.packaging.resource_check import required_resources, validate_resources


def test_required_resources_are_declared():
    resources = required_resources()

    assert "styles/app.qss" in resources
    assert "icons/app.png" in resources


def test_validate_resources_returns_missing_relative_paths(tmp_path):
    missing = validate_resources(tmp_path)

    assert missing == ["styles/app.qss", "icons/app.png"]


def test_validate_resources_accepts_present_files(tmp_path):
    for relative_path in required_resources():
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"present")

    assert validate_resources(tmp_path) == []
