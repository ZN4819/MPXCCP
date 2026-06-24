from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QComboBox, QTabWidget

from mpxccp.domain.enums import MeasureUnit
from mpxccp.repositories.session import create_engine_for_path, init_database
from mpxccp.services.application_service import ApplicationService
from mpxccp.services.basic_info_service import BasicInfoService
from mpxccp.services.network_service import NetworkService
from mpxccp.ui.main_window import MainWindow
from mpxccp.ui.pages.application_page import ApplicationPage
from mpxccp.ui.widgets import EvidenceDialog, ProductListWidget, QuantWidget, RiskWidget


def _engine(tmp_path: Path):
    engine = create_engine_for_path(tmp_path / "application-page.sqlite3")
    init_database(engine)
    return engine


def _project_id(engine) -> int:
    result = BasicInfoService(engine).save_basic_info(
        flow_no="APP-UI-001",
        system_name="Application Page System",
        client_name="Client",
        assessment_org="Assessment Org",
    )
    assert result.success
    assert result.project_id is not None
    BasicInfoService(engine).sync_subsystems(result.project_id, ["Business", "Management"])
    return result.project_id


def _network_channel(engine, project_id: int):
    network = NetworkService(engine)
    network.sync_from_basic_subsystems(project_id)
    subsystem = network.list_subsystems(project_id)[0]
    return network.create_channel(subsystem.id, "HTTPS")


def test_application_page_uses_subsystem_object_tabs_and_common_widgets(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    page = ApplicationPage(ApplicationService(engine))
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.sync_from_basic_subsystems()
    page.add_user("Admin")
    page.add_access_control("Permission Matrix")
    page.add_important_data("Trade Record", "Business Data")
    page.add_business_action("Order Submit")

    tabs = page.findChild(QTabWidget, "applicationObjectTabs")

    assert page.subsystem_list().objectName() == "applicationSubsystemNavigator"
    assert tabs is not None
    assert page.object_tab_names() == ["应用用户", "访问控制信息", "重要数据", "关键业务行为"]
    assert page.subsystem_names() == ["Business", "Management"]
    assert page.object_names("user") == ["Admin"]
    assert page.object_names("access_control") == ["Permission Matrix"]
    assert page.object_names("important_data") == ["Trade Record"]
    assert page.object_names("business_action") == ["Order Submit"]
    assert len(page.findChildren(QuantWidget)) == 7
    assert len(page.findChildren(ProductListWidget)) == 7
    assert len(page.findChildren(RiskWidget)) == 7
    assert page.risk_widget("user_auth").full_mode is True
    assert page.risk_widget("access_integrity").full_mode is False
    assert page.risk_widget("transport_integrity").full_mode is False


def test_application_page_saves_current_object_before_switching_tabs(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = ApplicationService(engine)
    page = ApplicationPage(service)
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.sync_from_basic_subsystems()
    user = page.add_user("Admin")
    page.object_field("user", "name").setText("System Admin")

    page.select_kind("access_control")

    assert service.load_user_details(user.id).user.name == "System Admin"
    assert page.current_kind() == "access_control"


def test_application_page_sync_saves_current_object_before_refresh(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = ApplicationService(engine)
    page = ApplicationPage(service)
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.sync_from_basic_subsystems()
    user = page.add_user("Admin")
    page.object_field("user", "name").setText("System Admin")
    BasicInfoService(engine).sync_subsystems(project_id, ["Business", "Management", "Ops"])

    page.sync_from_basic_subsystems()

    assert service.load_user_details(user.id).user.name == "System Admin"
    assert "System Admin" in page.object_names("user")


def test_application_page_transport_units_keep_empty_channel_until_user_selects(
    qtbot,
    tmp_path,
):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    channel = _network_channel(engine, project_id)
    service = ApplicationService(engine)
    page = ApplicationPage(ApplicationService(engine), network_service=NetworkService(engine))
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.sync_from_basic_subsystems()
    important_data = page.add_important_data("Trade Record", "Business Data")

    transport_confidentiality = page.unit_field(
        "transport_confidentiality",
        "network_channel_id",
    )
    transport_integrity = page.unit_field("transport_integrity", "network_channel_id")

    assert isinstance(transport_confidentiality, QComboBox)
    assert isinstance(transport_integrity, QComboBox)
    assert transport_confidentiality.findData(channel.id) >= 0
    assert transport_integrity.findData(channel.id) >= 0
    assert transport_confidentiality.currentData() is None
    assert transport_integrity.currentData() is None

    page.save_current_detail(silent=True)

    details = service.load_important_data_details(important_data.id)
    assert details.transport_confidentiality.network_channel_id is None
    assert details.transport_integrity.network_channel_id is None


def test_application_page_refreshes_network_channels_after_page_load(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    page = ApplicationPage(ApplicationService(engine), network_service=NetworkService(engine))
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.sync_from_basic_subsystems()
    page.add_important_data("Trade Record", "Business Data")
    channel = _network_channel(engine, project_id)

    page.refresh_network_channels()

    transport_confidentiality = page.unit_field(
        "transport_confidentiality",
        "network_channel_id",
    )
    transport_integrity = page.unit_field("transport_integrity", "network_channel_id")

    assert isinstance(transport_confidentiality, QComboBox)
    assert isinstance(transport_integrity, QComboBox)
    assert transport_confidentiality.findData(channel.id) >= 0
    assert transport_integrity.findData(channel.id) >= 0
    assert transport_confidentiality.currentData() is None
    assert transport_integrity.currentData() is None


def test_application_page_persists_explicit_network_channel_selection(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    channel = _network_channel(engine, project_id)
    service = ApplicationService(engine)
    page = ApplicationPage(service, network_service=NetworkService(engine))
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.sync_from_basic_subsystems()
    important_data = page.add_important_data("Trade Record", "Business Data")
    transport_confidentiality = page.unit_field(
        "transport_confidentiality",
        "network_channel_id",
    )
    transport_integrity = page.unit_field("transport_integrity", "network_channel_id")

    assert isinstance(transport_confidentiality, QComboBox)
    assert isinstance(transport_integrity, QComboBox)
    transport_confidentiality.setCurrentIndex(transport_confidentiality.findData(channel.id))
    transport_integrity.setCurrentIndex(transport_integrity.findData(channel.id))
    page.save_current_detail(silent=True)

    details = service.load_important_data_details(important_data.id)
    assert details.transport_confidentiality.network_channel_id == channel.id
    assert details.transport_integrity.network_channel_id == channel.id


def test_main_window_marks_scoring_dirty_after_application_detail_save(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    window = MainWindow(application_service=ApplicationService(engine))
    qtbot.addWidget(window)

    window.set_project_context(
        project_id=project_id,
        system_name="Application Page System",
        flow_no="APP",
    )
    application_page = window.application_page()
    application_page.sync_from_basic_subsystems()
    application_page.add_user("Admin")

    assert window.is_scoring_dirty is False

    application_page.save_current_detail(silent=True)

    assert window.is_scoring_dirty is True


def test_application_page_evidence_button_uses_current_detail_context(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = ApplicationService(engine)
    page = ApplicationPage(service)
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.sync_from_basic_subsystems()
    user = page.add_user("Admin")
    auth_detail = service.load_user_details(user.id).auth

    page.evidence_button("user_auth").click()

    assert isinstance(page.current_evidence_dialog(), EvidenceDialog)
    assert page.current_evidence_dialog().parent() is page
    assert page.current_evidence_context() == {
        "project_id": project_id,
        "unit_type": MeasureUnit.APP_USER_AUTH.value,
        "related_id": auth_detail.id,
        "object_name": "Admin",
    }


def test_main_window_wires_application_page_service_and_project_context(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    window = MainWindow(application_service=ApplicationService(engine))
    qtbot.addWidget(window)

    window.set_project_context(
        project_id=project_id,
        system_name="Application Page System",
        flow_no="APP",
    )
    application_page = window.application_page()
    application_page.sync_from_basic_subsystems()
    created = application_page.add_user("Admin")

    assert application_page.project_id() == project_id
    assert created.project_id == project_id
    assert application_page.object_names("user") == ["Admin"]
