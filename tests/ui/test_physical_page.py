from __future__ import annotations

from pathlib import Path

from mpxccp.domain.constants import CHECK, CROSS
from mpxccp.domain.enums import MeasureUnit
from mpxccp.repositories.session import create_engine_for_path, init_database
from mpxccp.services.basic_info_service import BasicInfoService
from mpxccp.services.physical_service import PhysicalService
from mpxccp.services.product_service import ProductService
from mpxccp.services.quant_service import QuantService
from mpxccp.ui.main_window import MainWindow
from mpxccp.ui.pages.physical_page import PhysicalPage
from mpxccp.ui.widgets import EvidenceDialog, ProductListWidget, QuantWidget, RiskWidget


def _engine(tmp_path: Path):
    engine = create_engine_for_path(tmp_path / "physical-page.sqlite3")
    init_database(engine)
    return engine


def _project_id(engine) -> int:
    result = BasicInfoService(engine).save_basic_info(
        flow_no="PHY-UI-001",
        system_name="物理页面系统",
        client_name="委托方",
        assessment_org="测评机构",
    )
    assert result.success
    assert result.project_id is not None
    return result.project_id


def test_physical_page_uses_master_detail_layout_and_common_widgets(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    page = PhysicalPage(PhysicalService(engine))
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.add_object("机房A")

    assert page.object_list().objectName() == "objectNavigator"
    assert page.object_names() == ["机房A"]
    assert len(page.findChildren(QuantWidget)) == 3
    assert len(page.findChildren(ProductListWidget)) == 3
    risk_widgets = page.findChildren(RiskWidget)
    assert len(risk_widgets) == 3
    assert [widget.full_mode for widget in risk_widgets] == [True, False, False]
    assert [button.text() for button in page.evidence_buttons()] == [
        "提交测评证据",
        "提交测评证据",
        "提交测评证据",
    ]


def test_physical_page_saves_current_detail_before_switching_objects(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = PhysicalService(engine)
    page = PhysicalPage(service)
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    first = page.add_object("机房A")
    second = page.add_object("机房B")
    page.select_object(first.id)
    page.object_field("name").setText("主机房")
    page.select_object(second.id)

    assert service.load_details(first.id).object.name == "主机房"
    assert page.selected_object_id() == second.id
    assert page.object_names() == ["主机房", "机房B"]


def test_physical_page_delete_current_object_refreshes_list(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    page = PhysicalPage(PhysicalService(engine))
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    first = page.add_object("机房A")
    page.add_object("机房B")

    page.select_object(first.id)
    page.delete_current_object(confirm=True)

    assert page.object_names() == ["机房B"]
    assert page.selected_object_id() is not None


def test_physical_page_evidence_button_opens_parented_dialog(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    page = PhysicalPage(PhysicalService(engine))
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.add_object("机房A")

    page.evidence_buttons()[0].click()
    dialog = page.current_evidence_dialog()

    assert isinstance(dialog, EvidenceDialog)
    assert dialog.parent() is page
    assert dialog.windowTitle() == "测评证据"


def test_physical_page_evidence_button_keeps_current_detail_context(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = PhysicalService(engine)
    page = PhysicalPage(service)
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    obj = page.add_object("机房A")
    auth_detail = service.load_details(obj.id).auth

    page.evidence_buttons()[0].click()

    assert page.current_evidence_context() == {
        "project_id": project_id,
        "unit_type": MeasureUnit.PHYSICAL_AUTH.value,
        "related_id": auth_detail.id,
        "object_name": "机房A",
    }


def test_physical_page_reload_then_save_preserves_quant_and_products(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = PhysicalService(engine)
    obj = service.create_object(project_id, "机房A")
    details = service.load_details(obj.id)
    QuantService(engine, project_id=project_id).save(
        MeasureUnit.PHYSICAL_AUTH.value,
        details.auth.id,
        d=CHECK,
        a=CHECK,
        k=CROSS,
        ra=1,
        rk=1.2,
    )
    ProductService(engine).save_products(
        project_id,
        MeasureUnit.PHYSICAL_AUTH.value,
        obj.id,
        [{"name": "门禁密码模块", "certificate_no": "CERT-PRESERVE"}],
    )
    page = PhysicalPage(service)
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.save_current_detail(silent=True)

    quant = QuantService(engine, project_id=project_id).load(
        MeasureUnit.PHYSICAL_AUTH.value,
        details.auth.id,
    )
    products = ProductService(engine).load_products(
        project_id,
        MeasureUnit.PHYSICAL_AUTH.value,
        obj.id,
    )

    assert (quant.d, quant.a, quant.k, quant.rk) == (CHECK, CHECK, CROSS, 1.2)
    assert [item.product_name for item in products] == ["门禁密码模块"]


def test_main_window_wires_physical_page_service_and_project_context(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    window = MainWindow(physical_service=PhysicalService(engine))
    qtbot.addWidget(window)

    window.set_project_context(project_id=project_id, system_name="物理页面系统", flow_no="PHY")
    physical_page = window.physical_page()
    created = physical_page.add_object("机房A")

    assert physical_page.project_id() == project_id
    assert created.project_id == project_id
    assert physical_page.object_names() == ["机房A"]


def test_physical_page_delete_confirmation_names_current_object(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    page = PhysicalPage(PhysicalService(engine))
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.add_object("机房A")

    assert "机房A" in page.delete_confirmation_text()
