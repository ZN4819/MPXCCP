from PySide6.QtWidgets import QApplication


def test_run_app_sets_metadata_and_delegates_to_qt_exec(monkeypatch, qapp):
    from mpxccp import bootstrap

    events: dict[str, bool] = {}

    class FakeMainWindow:
        def __init__(self) -> None:
            events["created"] = True

        def show(self) -> None:
            events["shown"] = True

    monkeypatch.setattr(bootstrap, "MainWindow", FakeMainWindow)
    monkeypatch.setattr(QApplication, "exec", lambda _app: 17)

    assert bootstrap.run_app() == 17
    assert QApplication.organizationName() == "Codex"
    assert QApplication.applicationName() == "MPXCCP"
    assert QApplication.applicationDisplayName() == "商用密码应用安全性评估实施工具"
    assert events == {"created": True, "shown": True}
