from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

import mpxccp.models as models
from mpxccp.domain.constants import CHECK, CROSS
from mpxccp.domain.enums import MeasureUnit
from mpxccp.repositories.session import create_engine_for_path, init_database, session_scope
from mpxccp.services.application_service import ApplicationService
from mpxccp.services.basic_info_service import BasicInfoService
from mpxccp.services.network_service import NetworkService
from mpxccp.services.product_service import ProductService
from mpxccp.services.quant_service import QuantService


def _engine(tmp_path: Path):
    engine = create_engine_for_path(tmp_path / "application.sqlite3")
    init_database(engine)
    return engine


def _project_id(engine, flow_no: str = "APP-001") -> int:
    result = BasicInfoService(engine).save_basic_info(
        flow_no=flow_no,
        system_name=f"Application Test System {flow_no}",
        client_name="Client",
        assessment_org="Assessment Org",
    )
    assert result.success
    assert result.project_id is not None
    return result.project_id


def _first_subsystem(engine, project_id: int, name: str = "Business"):
    basic = BasicInfoService(engine)
    basic.sync_subsystems(project_id, [name])
    service = ApplicationService(engine)
    service.sync_from_basic_subsystems(project_id)
    return service.list_subsystems(project_id)[0]


def _network_channel(engine, project_id: int):
    basic = BasicInfoService(engine)
    basic.sync_subsystems(project_id, ["Business"])
    network = NetworkService(engine)
    network.sync_from_basic_subsystems(project_id)
    subsystem = network.list_subsystems(project_id)[0]
    return network.create_channel(subsystem.id, "HTTPS")


def test_application_sync_preserves_existing_objects(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    basic = BasicInfoService(engine)
    service = ApplicationService(engine)

    basic.sync_subsystems(project_id, ["Business"])
    service.sync_from_basic_subsystems(project_id)
    subsystem = service.list_subsystems(project_id)[0]
    service.create_user(subsystem.id, "Admin")
    basic.sync_subsystems(project_id, ["Business", "Management"])

    service.sync_from_basic_subsystems(project_id)

    assert service.user_count(subsystem.id) == 1
    assert [item.name for item in service.list_subsystems(project_id)] == [
        "Business",
        "Management",
    ]


def test_create_application_objects_create_expected_details(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = ApplicationService(engine)
    subsystem = _first_subsystem(engine, project_id)

    user = service.create_user(subsystem.id, "Admin")
    access = service.create_access_control(subsystem.id, "Permission Matrix")
    data = service.create_important_data(subsystem.id, "Trade Record", "Business Data")
    action = service.create_business_action(subsystem.id, "Order Submit")

    user_details = service.load_user_details(user.id)
    access_details = service.load_access_control_details(access.id)
    data_details = service.load_important_data_details(data.id)
    action_details = service.load_business_action_details(action.id)

    assert user_details.auth.application_user_id == user.id
    assert access_details.integrity.access_control_object_id == access.id
    assert len(data_details.all_detail_ids()) == 4
    assert data_details.transport_confidentiality.important_data_id == data.id
    assert data_details.storage_confidentiality.important_data_id == data.id
    assert data_details.transport_integrity.important_data_id == data.id
    assert data_details.storage_integrity.important_data_id == data.id
    assert action_details.non_repudiation.business_action_id == action.id


def test_save_application_user_detail_persists_quant_products_and_extra_fields(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = ApplicationService(engine)
    subsystem = _first_subsystem(engine, project_id)
    user = service.create_user(subsystem.id, "Admin")

    result = service.save_user_detail(
        user.id,
        {
            "object": {
                "name": "System Admin",
                "role": "Administrator",
                "login_method": "Password",
                "interview_record": "Interviewed app owner",
            },
            "units": {
                "user_auth": {
                    "auth_methods": "Password, OTP",
                    "crypto_usage": "Used",
                    "algorithm": "SM3",
                    "key_management": "Central key policy",
                    "risk_level": "Medium",
                    "risk_analysis": "OTP is not enforced everywhere",
                    "remediation": "Enable OTP for all admins",
                    "quant": {"d": CHECK, "a": CHECK, "k": CHECK, "ra": 1, "rk": 1},
                    "products": [
                        {
                            "name": "IAM Crypto Module",
                            "vendor": "Vendor A",
                            "certificate_no": "CERT-APP-1",
                            "level": "Level 2",
                            "usage": "auth",
                        }
                    ],
                }
            },
        },
        silent=True,
    )

    reloaded = service.load_user_details(user.id)
    quant = QuantService(engine, project_id=project_id).load(
        MeasureUnit.APP_USER_AUTH.value,
        reloaded.auth.id,
    )
    products = ProductService(engine).load_products(
        project_id,
        MeasureUnit.APP_USER_AUTH.value,
        user.id,
    )

    assert result.success is True
    assert reloaded.user.name == "System Admin"
    assert reloaded.user.extra_data["login_method"] == "Password"
    assert reloaded.auth.auth_methods == "Password, OTP"
    assert reloaded.auth.extra_data["key_management"] == "Central key policy"
    assert quant.score == 1.0
    assert [item.product_name for item in products] == ["IAM Crypto Module"]


def test_save_important_data_details_persists_four_units_and_channel_refs(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    channel = _network_channel(engine, project_id)
    service = ApplicationService(engine)
    service.sync_from_basic_subsystems(project_id)
    subsystem = service.list_subsystems(project_id)[0]
    data = service.create_important_data(subsystem.id, "Trade Record", "Business Data")

    result = service.save_important_data_detail(
        data.id,
        {
            "object": {
                "name": "Trade Ledger",
                "data_type": "Transaction",
                "data_location": "Database A",
                "business_description": "Stores submitted orders",
                "interview_record": "Interviewed DBA",
            },
            "units": {
                "transport_confidentiality": {
                    "network_channel_id": channel.id,
                    "encryption_method": "TLS",
                    "mechanism_description": "Encrypted during transit",
                    "quant": {"d": CHECK, "a": CHECK, "k": CHECK, "ra": 1, "rk": 1},
                    "products": [{"name": "TLS Gateway"}],
                },
                "storage_confidentiality": {
                    "storage_location": "Database A",
                    "encryption_method": "TDE",
                    "quant": {"d": CHECK, "a": CHECK, "k": CROSS, "ra": 1, "rk": 1.2},
                },
                "transport_integrity": {
                    "network_channel_id": channel.id,
                    "integrity_method": "TLS MAC",
                    "quant": {"d": CHECK, "a": CHECK, "k": CHECK, "ra": 1, "rk": 1},
                },
                "storage_integrity": {
                    "storage_location": "Database A",
                    "integrity_method": "SM3 digest",
                    "quant": {"d": CROSS, "a": "/", "k": "/", "ra": 1, "rk": 1},
                },
            },
        },
        silent=True,
    )

    reloaded = service.load_important_data_details(data.id)
    storage_quant = QuantService(engine, project_id=project_id).load(
        MeasureUnit.DATA_STORAGE_CONFIDENTIALITY.value,
        reloaded.storage_confidentiality.id,
    )
    products = ProductService(engine).load_products(
        project_id,
        MeasureUnit.DATA_TRANSPORT_CONFIDENTIALITY.value,
        data.id,
    )

    assert result.success is True
    assert reloaded.data.name == "Trade Ledger"
    assert reloaded.data.extra_data["data_location"] == "Database A"
    assert reloaded.transport_confidentiality.network_channel_id == channel.id
    assert reloaded.transport_integrity.network_channel_id == channel.id
    assert reloaded.transport_confidentiality.extra_data["mechanism_description"] == (
        "Encrypted during transit"
    )
    assert (storage_quant.d, storage_quant.a, storage_quant.k, storage_quant.rk) == (
        CHECK,
        CHECK,
        CROSS,
        1.2,
    )
    assert [item.product_name for item in products] == ["TLS Gateway"]


def test_delete_application_object_removes_quant_evidence_and_products_for_current_object(
    tmp_path,
):
    engine = _engine(tmp_path)
    project_id = _project_id(engine, "APP-DEL-1")
    other_project_id = _project_id(engine, "APP-DEL-2")
    service = ApplicationService(engine)
    subsystem = _first_subsystem(engine, project_id, "Business")
    other_subsystem = _first_subsystem(engine, other_project_id, "Business")
    target = service.create_user(subsystem.id, "Target")
    other = service.create_user(other_subsystem.id, "Other")
    target_details = service.load_user_details(target.id)
    other_details = service.load_user_details(other.id)

    QuantService(engine, project_id=project_id).save(
        MeasureUnit.APP_USER_AUTH.value,
        target_details.auth.id,
        d=CHECK,
        a=CHECK,
        k=CHECK,
        ra=1,
        rk=1,
    )
    QuantService(engine, project_id=other_project_id).save(
        MeasureUnit.APP_USER_AUTH.value,
        other_details.auth.id,
        d=CHECK,
        a=CHECK,
        k=CHECK,
        ra=1,
        rk=1,
    )
    ProductService(engine).save_products(
        project_id,
        MeasureUnit.APP_USER_AUTH.value,
        target.id,
        [{"name": "Delete Me"}],
    )
    ProductService(engine).save_products(
        other_project_id,
        MeasureUnit.APP_USER_AUTH.value,
        other.id,
        [{"name": "Keep Me"}],
    )
    with session_scope(engine) as session:
        session.add(
            models.EvidenceImage(
                project_id=project_id,
                unit_type=MeasureUnit.APP_USER_AUTH.value,
                related_id=target_details.auth.id,
                file_name="1. app-user-auth.png",
                original_name="source.png",
                caption="",
                checksum="abc",
            )
        )

    result = service.delete_application_object("user", target.id)

    assert result.success is True
    assert QuantService(engine, project_id=project_id).exists_for_related(
        target_details.auth.id,
        unit_type=MeasureUnit.APP_USER_AUTH.value,
    ) is False
    assert QuantService(engine, project_id=other_project_id).exists_for_related(
        other_details.auth.id,
        unit_type=MeasureUnit.APP_USER_AUTH.value,
    ) is True
    assert ProductService(engine).load_products(
        project_id,
        MeasureUnit.APP_USER_AUTH.value,
        target.id,
    ) == []
    assert [
        item.product_name
        for item in ProductService(engine).load_products(
            other_project_id,
            MeasureUnit.APP_USER_AUTH.value,
            other.id,
        )
    ] == ["Keep Me"]
    with session_scope(engine) as session:
        assert session.get(models.ApplicationUser, target.id) is None
        assert session.get(models.ApplicationUser, other.id) is not None
        assert session.scalar(
            select(models.EvidenceImage).where(
                models.EvidenceImage.project_id == project_id,
                models.EvidenceImage.related_id == target_details.auth.id,
            )
        ) is None


def test_delete_application_object_preserves_other_detail_product_when_object_id_collides(
    tmp_path,
):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = ApplicationService(engine)
    subsystem = _first_subsystem(engine, project_id)
    other = service.create_user(subsystem.id, "Other")

    with session_scope(engine) as session:
        other_auth = session.scalar(
            select(models.ApplicationUserAuthDetail).where(
                models.ApplicationUserAuthDetail.application_user_id == other.id
            )
        )
        other_auth.id = 100
    with session_scope(engine) as session:
        session.add(
            models.ApplicationUser(
                id=100,
                project_id=project_id,
                application_subsystem_id=subsystem.id,
                name="Target",
                sort_order=99,
            )
        )
        session.flush()
        session.add(
            models.ApplicationUserAuthDetail(
                project_id=project_id,
                application_user_id=100,
                sort_order=0,
            )
        )
    ProductService(engine).save_products(
        project_id,
        MeasureUnit.APP_USER_AUTH.value,
        100,
        [{"name": "Other Detail Legacy Product"}],
    )

    result = service.delete_application_object("user", 100)

    assert result.success is True
    assert "ambiguous_application_object_product:user_auth" in result.warnings
    assert [
        item.product_name
        for item in ProductService(engine).load_products(
            project_id,
            MeasureUnit.APP_USER_AUTH.value,
            100,
        )
    ] == ["Other Detail Legacy Product"]
    with session_scope(engine) as session:
        assert session.get(models.ApplicationUser, 100) is None
        assert session.get(models.ApplicationUser, other.id) is not None
        assert session.get(models.ApplicationUserAuthDetail, 100) is not None
