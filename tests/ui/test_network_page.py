from __future__ import annotations

from pathlib import Path

from mpxccp.domain.enums import MeasureUnit
from mpxccp.repositories.session import create_engine_for_path, init_database
from mpxccp.services.basic_info_service import BasicInfoService
from mpxccp.services.network_service import NetworkService
from mpxccp.ui.main_window import MainWindow
from mpxccp.ui.pages.network_page import NetworkPage
from mpxccp.ui.widgets import DateInput, EvidenceDialog, ProductListWidget, QuantWidget, RiskWidget


def _engine(tmp_path: Path):
    engine = create_engine_for_path(tmp_path / "network-page.sqlite3")
    init_database(engine)
    return engine


def _project_id(engine) -> int:
    result = BasicInfoService(engine).save_basic_info(
        flow_no="NET-UI-001",
        system_name="Network Page System",
        client_name="Client",
        assessment_org="Assessment Org",
    )
    assert result.success
    assert result.project_id is not None
    BasicInfoService(engine).sync_subsystems(result.project_id, ["Portal", "Admin"])
    return result.project_id


def test_network_page_uses_subsystem_channel_layout_and_common_widgets(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    page = NetworkPage(NetworkService(engine))
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.sync_from_basic_subsystems()
    page.add_channel("Internet Access")

    assert page.subsystem_list().objectName() == "subsystemNavigator"
    assert page.channel_list().objectName() == "channelNavigator"
    assert page.subsystem_names() == ["Portal", "Admin"]
    assert page.channel_names() == ["Internet Access"]
    assert len(page.findChildren(QuantWidget)) == 4
    assert len(page.findChildren(ProductListWidget)) == 3
    assert len(page.findChildren(RiskWidget)) == 4
    assert len(page.findChildren(DateInput)) == 2
    assert len(page.evidence_buttons()) == 4


def test_network_page_saves_current_channel_before_switching_channels(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = NetworkService(engine)
    page = NetworkPage(service)
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.sync_from_basic_subsystems()
    first = page.add_channel("Internet Access")
    second = page.add_channel("Admin Access")
    page.select_channel(first.id)
    page.channel_field("name").setText("Portal HTTPS")
    page.select_channel(second.id)

    assert service.load_details(first.id).channel.name == "Portal HTTPS"
    assert page.selected_channel_id() == second.id
    assert page.channel_names() == ["Portal HTTPS", "Admin Access"]


def test_network_page_sync_saves_current_channel_before_refresh(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = NetworkService(engine)
    page = NetworkPage(service)
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.sync_from_basic_subsystems()
    channel = page.add_channel("Internet Access")
    page.channel_field("name").setText("Portal HTTPS")
    BasicInfoService(engine).sync_subsystems(project_id, ["Portal", "Admin", "Ops"])

    page.sync_from_basic_subsystems()

    assert service.load_details(channel.id).channel.name == "Portal HTTPS"
    assert "Portal HTTPS" in page.channel_names()


def test_network_page_saves_current_channel_before_switching_subsystems(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = NetworkService(engine)
    page = NetworkPage(service)
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.sync_from_basic_subsystems()
    first = page.add_channel("Internet Access")
    second_subsystem_id = page._subsystems[1].id
    page.channel_field("name").setText("Portal HTTPS")

    page.select_subsystem(second_subsystem_id)

    assert service.load_details(first.id).channel.name == "Portal HTTPS"
    assert page.selected_subsystem_id() == second_subsystem_id


def test_network_page_boundary_has_no_product_list_but_keeps_quant_and_evidence(
    qtbot,
    tmp_path,
):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = NetworkService(engine)
    page = NetworkPage(service)
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.sync_from_basic_subsystems()
    channel = page.add_channel("Internet Access")
    boundary_detail = service.load_details(channel.id).boundary

    assert page.product_widget("boundary") is None
    assert isinstance(page.quant_widget("boundary"), QuantWidget)

    page.evidence_buttons()[-1].click()

    assert isinstance(page.current_evidence_dialog(), EvidenceDialog)
    assert page.current_evidence_dialog().parent() is page
    assert page.current_evidence_context() == {
        "project_id": project_id,
        "unit_type": MeasureUnit.NETWORK_BOUNDARY_INTEGRITY.value,
        "related_id": boundary_detail.id,
        "object_name": "Internet Access",
    }


def test_main_window_wires_network_page_service_and_project_context(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    window = MainWindow(network_service=NetworkService(engine))
    qtbot.addWidget(window)

    window.set_project_context(
        project_id=project_id,
        system_name="Network Page System",
        flow_no="NET",
    )
    network_page = window.network_page()
    network_page.sync_from_basic_subsystems()
    created = network_page.add_channel("Internet Access")

    assert network_page.project_id() == project_id
    assert created.project_id == project_id
    assert network_page.channel_names() == ["Internet Access"]
