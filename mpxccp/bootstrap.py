from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QFont, QFontDatabase, QIcon
from PySide6.QtWidgets import QApplication, QComboBox

from mpxccp.config.paths import resource_path
from mpxccp.config.settings import APP_NAME, APP_ORGANIZATION
from mpxccp.ui.main_window import MAIN_WINDOW_TITLE, MainWindow

logger = logging.getLogger(__name__)

_WINDOWS_CJK_FONT_FILES = (
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\simsun.ttc"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
)
_PREFERRED_FONT_FAMILIES = (
    "Microsoft YaHei UI",
    "Microsoft YaHei",
    "SimSun",
    "SimHei",
    "Arial",
)


class ComboBoxWheelFilter(QObject):
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if (
            isinstance(watched, QComboBox)
            and event.type() == QEvent.Type.Wheel
            and not watched.view().isVisible()
        ):
            event.ignore()
            return True
        return super().eventFilter(watched, event)


def install_combo_box_wheel_protection(app: QApplication | None = None) -> ComboBoxWheelFilter:
    app = app or QApplication.instance()
    if app is None:
        raise RuntimeError("QApplication must exist before installing combo-box wheel protection")

    existing = app.property("mpxccp_combo_box_wheel_filter")
    if isinstance(existing, ComboBoxWheelFilter):
        return existing

    wheel_filter = ComboBoxWheelFilter(app)
    app.installEventFilter(wheel_filter)
    app.setProperty("mpxccp_combo_box_wheel_filter", wheel_filter)
    return wheel_filter


def _resource_file(*parts: str):
    return resource_path("mpxccp", "resources", *parts)


def load_application_icon(app: QApplication) -> None:
    icon_path = _resource_file("icons", "app.png")
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))


def configure_application_font(app: QApplication) -> str:
    for font_file in _WINDOWS_CJK_FONT_FILES:
        if font_file.is_file():
            QFontDatabase.addApplicationFont(str(font_file))

    available_families = set(QFontDatabase.families())
    for family in _PREFERRED_FONT_FAMILIES:
        if family in available_families:
            app.setFont(QFont(family, 9))
            return family

    return app.font().family()


def load_application_style(app: QApplication) -> None:
    style_path = _resource_file("styles", "app.qss")
    try:
        app.setStyleSheet(style_path.read_text(encoding="utf-8"))
    except OSError as exc:
        logger.warning("failed to load application style from %s: %s", style_path, exc)


def run_app(argv: list[str] | None = None) -> int:
    app = QApplication.instance()
    if app is None:
        app = QApplication(list(sys.argv if argv is None else argv))

    app.setOrganizationName(APP_ORGANIZATION)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(MAIN_WINDOW_TITLE)
    configure_application_font(app)
    install_combo_box_wheel_protection(app)
    load_application_icon(app)
    load_application_style(app)

    window = MainWindow()
    window.show()
    return app.exec()
