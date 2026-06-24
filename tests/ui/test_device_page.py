from __future__ import annotations

from pathlib import Path

from mpxccp.domain.constants import CHECK, CROSS
from mpxccp.domain.enums import MeasureUnit
from mpxccp.repositories.session import create_engine_for_path, init_database
from mpxccp.services.basic_info_service import BasicInfoService
from mpxccp.services.device_service import DeviceService
from mpxccp.services.product_service import ProductService
from mpxccp.services.quant_service import QuantService
from mpxccp.ui.main_window import MainWindow
from mpxccp.ui.pages.device_page import DevicePage
from mpxccp.ui.widgets import DateInput, EvidenceDialog, ProductListWidget, QuantWidget, RiskWidget


def _engine(tmp_path: Path):
    engine = create_engine_for_path(tmp_path / "device-page.sqlite3")
    init_database(engine)
    return engine


def _project_id(engine) -> int:
    result = BasicInfoService(engine).save_basic_info(
        flow_no="DEV-UI-001",
        system_name="设备页面系统",
        client_name="委托方",
        assessment_org="测评机构",
    )
    assert result.success
    assert result.project_id is not None
    return result.project_id


def test_device_page_uses_master_detail_layout_and_common_widgets(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    page = DevicePage(DeviceService(engine))
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.add_object("服务器A")

    assert page.object_list().objectName() == "objectNavigator"
    assert page.object_names() == ["服务器A"]
    assert len(page.findChildren(QuantWidget)) == 5
    assert len(page.findChildren(ProductListWidget)) == 5
    assert len(page.findChildren(RiskWidget)) == 5
    assert len(page.findChildren(DateInput)) == 2
    assert [button.text() for button in page.evidence_buttons()] == [
        "提交测评证据",
        "提交测评证据",
        "提交测评证据",
        "提交测评证据",
        "提交测评证据",
    ]


def test_device_page_saves_current_detail_before_switching_objects(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = DeviceService(engine)
    page = DevicePage(service)
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    first = page.add_object("服务器A")
    second = page.add_object("服务器B")
    page.select_object(first.id)
    page.object_field("name").setText("业务服务器")
    page.select_object(second.id)

    assert service.load_details(first.id).object.name == "业务服务器"
    assert page.selected_object_id() == second.id
    assert page.object_names() == ["业务服务器", "服务器B"]


def test_device_page_crypto_usage_updates_quant_for_auth_unit(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    page = DevicePage(DeviceService(engine))
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.add_object("服务器A")

    crypto_usage = page.unit_field("auth", "crypto_usage")
    crypto_usage.setCurrentText("未使用")
    quant = page.quant_widget("auth")

    assert (quant.values()["d"], quant.values()["a"], quant.values()["k"]) == (
        CROSS,
        "/",
        "/",
    )
    assert quant.a_enabled() is False
    assert quant.k_enabled() is False


def test_device_page_product_level_updates_quant_for_integrity_unit(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    page = DevicePage(DeviceService(engine))
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.add_object("服务器A")

    product_level = page.unit_field("access_integrity", "product_level")
    product_level.setCurrentText("一级")
    quant = page.quant_widget("access_integrity")

    assert (
        quant.values()["d"],
        quant.values()["a"],
        quant.values()["k"],
        quant.values()["rk"],
    ) == (CHECK, CHECK, CROSS, 1.2)


def test_device_page_product_level_keeps_priority_after_implementation_status_change(
    qtbot,
    tmp_path,
):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    page = DevicePage(DeviceService(engine))
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.add_object("服务器A")

    page.unit_field("access_integrity", "product_level").setCurrentText("一级")
    page.unit_field("access_integrity", "implementation_status").setCurrentText("未实现")
    quant = page.quant_widget("access_integrity")

    assert (
        quant.values()["d"],
        quant.values()["a"],
        quant.values()["k"],
        quant.values()["rk"],
    ) == (CHECK, CHECK, CROSS, 1.2)


def test_device_page_product_list_level_updates_quant(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    page = DevicePage(DeviceService(engine))
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.add_object("服务器A")

    page.product_widget("log_integrity").add_product(
        {"name": "日志完整性密码模块", "level": "一级"}
    )
    quant = page.quant_widget("log_integrity")

    assert (
        quant.values()["d"],
        quant.values()["a"],
        quant.values()["k"],
        quant.values()["rk"],
    ) == (CHECK, CHECK, CROSS, 1.2)


def test_device_page_evidence_button_keeps_current_detail_context(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = DeviceService(engine)
    page = DevicePage(service)
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    device = page.add_object("服务器A")
    auth_detail = service.load_details(device.id).auth

    page.evidence_buttons()[0].click()

    assert isinstance(page.current_evidence_dialog(), EvidenceDialog)
    assert page.current_evidence_dialog().parent() is page
    assert page.current_evidence_context() == {
        "project_id": project_id,
        "unit_type": MeasureUnit.DEVICE_AUTH.value,
        "related_id": auth_detail.id,
        "object_name": "服务器A",
    }


def test_device_page_reload_then_save_preserves_quant_and_products(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = DeviceService(engine)
    device = service.create_object(project_id, "服务器A")
    details = service.load_details(device.id)
    QuantService(engine, project_id=project_id).save(
        MeasureUnit.DEVICE_AUTH.value,
        details.auth.id,
        d=CHECK,
        a=CHECK,
        k=CROSS,
        ra=1,
        rk=1.2,
    )
    ProductService(engine).save_products(
        project_id,
        MeasureUnit.DEVICE_AUTH.value,
        device.id,
        [{"name": "服务器密码模块", "certificate_no": "CERT-DEV-PRESERVE"}],
    )
    page = DevicePage(service)
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.save_current_detail(silent=True)

    quant = QuantService(engine, project_id=project_id).load(
        MeasureUnit.DEVICE_AUTH.value,
        details.auth.id,
    )
    products = ProductService(engine).load_products(
        project_id,
        MeasureUnit.DEVICE_AUTH.value,
        device.id,
    )

    assert (quant.d, quant.a, quant.k, quant.rk) == (CHECK, CHECK, CROSS, 1.2)
    assert [item.product_name for item in products] == ["服务器密码模块"]


def test_main_window_wires_device_page_service_and_project_context(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    window = MainWindow(device_service=DeviceService(engine))
    qtbot.addWidget(window)

    window.set_project_context(project_id=project_id, system_name="设备页面系统", flow_no="DEV")
    device_page = window.device_page()
    created = device_page.add_object("服务器A")

    assert device_page.project_id() == project_id
    assert created.project_id == project_id
    assert device_page.object_names() == ["服务器A"]


def test_device_page_delete_confirmation_names_current_object(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    page = DevicePage(DeviceService(engine))
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.add_object("服务器A")

    assert "服务器A" in page.delete_confirmation_text()
