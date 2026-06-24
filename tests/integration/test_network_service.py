from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

import mpxccp.models as models
from mpxccp.domain.constants import CHECK, CROSS
from mpxccp.domain.enums import MeasureUnit
from mpxccp.repositories.session import create_engine_for_path, init_database, session_scope
from mpxccp.services.basic_info_service import BasicInfoService
from mpxccp.services.network_service import NetworkService
from mpxccp.services.product_service import ProductService
from mpxccp.services.quant_service import QuantService


def _engine(tmp_path: Path):
    engine = create_engine_for_path(tmp_path / "network.sqlite3")
    init_database(engine)
    return engine


def _project_id(engine, flow_no: str = "NET-001") -> int:
    result = BasicInfoService(engine).save_basic_info(
        flow_no=flow_no,
        system_name=f"Network Test System {flow_no}",
        client_name="Client",
        assessment_org="Assessment Org",
    )
    assert result.success
    assert result.project_id is not None
    return result.project_id


def _first_subsystem(engine, project_id: int, name: str = "Portal"):
    basic = BasicInfoService(engine)
    basic.sync_subsystems(project_id, [name])
    service = NetworkService(engine)
    service.sync_from_basic_subsystems(project_id)
    return service.list_subsystems(project_id)[0]


def test_network_sync_adds_new_subsystem_without_clearing_existing_channels(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    basic = BasicInfoService(engine)
    service = NetworkService(engine)

    basic.sync_subsystems(project_id, ["Portal"])
    service.sync_from_basic_subsystems(project_id)
    first = service.list_subsystems(project_id)[0]
    service.create_channel(first.id, "Internet Access")
    basic.sync_subsystems(project_id, ["Portal", "Admin"])

    service.sync_from_basic_subsystems(project_id)

    assert service.channel_count(first.id) == 1
    assert [item.name for item in service.list_subsystems(project_id)] == ["Portal", "Admin"]


def test_create_network_channel_creates_four_details(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = NetworkService(engine)
    subsystem = _first_subsystem(engine, project_id)

    channel = service.create_channel(subsystem.id, "Internet Access")
    details = service.load_details(channel.id)

    assert channel.project_id == project_id
    assert channel.network_subsystem_id == subsystem.id
    assert len(details.all_detail_ids()) == 4
    assert details.auth.network_channel_id == channel.id
    assert details.integrity.network_channel_id == channel.id
    assert details.confidentiality.network_channel_id == channel.id
    assert details.boundary.network_channel_id == channel.id


def test_save_network_channel_detail_persists_units_quant_products_and_boundary_rule(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = NetworkService(engine)
    subsystem = _first_subsystem(engine, project_id)
    channel = service.create_channel(subsystem.id, "Internet Access")

    result = service.save_channel_detail(
        channel.id,
        {
            "channel": {
                "name": "Portal HTTPS",
                "source": "Internet",
                "target": "Portal",
                "protocol": "HTTPS",
                "network_environment": "Internet",
                "client_type": "Browser",
                "server_type": "Gateway",
                "interview_record": "Interviewed network owner",
            },
            "units": {
                "auth": {
                    "auth_methods": "TLS certificate",
                    "algorithm": "SM2",
                    "certificate_algorithm": "SM2",
                    "certificate_source": "CA",
                    "certificate_start_date": "2026-01-01",
                    "certificate_end_date": "2027-01-01",
                    "risk_level": "Medium",
                    "risk_analysis": "Certificate lifecycle needs tracking",
                    "remediation": "Maintain renewal record",
                    "quant": {"d": CHECK, "a": CHECK, "k": CHECK, "ra": 1, "rk": 1},
                    "products": [
                        {
                            "name": "TLS Gateway",
                            "vendor": "Vendor A",
                            "certificate_no": "CERT-NET-1",
                            "level": "Level 2",
                            "usage": "auth",
                        }
                    ],
                },
                "integrity": {
                    "integrity_method": "TLS MAC",
                    "quant": {"d": CHECK, "a": CHECK, "k": CROSS, "ra": 1, "rk": 1.2},
                },
                "confidentiality": {
                    "encryption_method": "TLS",
                    "quant": {"d": CHECK, "a": CHECK, "k": CHECK, "ra": 1, "rk": 1},
                },
                "boundary": {
                    "boundary_device": "Firewall",
                    "boundary_product_level": "Level 2",
                    "integrity_method": "ACL signature",
                    "quant": {"d": CHECK, "a": CHECK, "k": CHECK, "ra": 1, "rk": 1},
                    "products": [{"name": "Should not be saved"}],
                },
            },
        },
        silent=True,
    )

    reloaded = service.load_details(channel.id)
    auth_quant = QuantService(engine, project_id=project_id).load(
        MeasureUnit.NETWORK_AUTH.value,
        reloaded.auth.id,
    )
    integrity_quant = QuantService(engine, project_id=project_id).load(
        MeasureUnit.NETWORK_INTEGRITY.value,
        reloaded.integrity.id,
    )
    auth_products = ProductService(engine).load_products(
        project_id,
        MeasureUnit.NETWORK_AUTH.value,
        channel.id,
    )
    boundary_products = ProductService(engine).load_products(
        project_id,
        MeasureUnit.NETWORK_BOUNDARY_INTEGRITY.value,
        channel.id,
    )

    assert result.success is True
    assert reloaded.channel.name == "Portal HTTPS"
    assert reloaded.channel.network_environment == "Internet"
    assert reloaded.channel.client_type == "Browser"
    assert reloaded.channel.server_type == "Gateway"
    assert reloaded.auth.auth_methods == "TLS certificate"
    assert reloaded.auth.extra_data["certificate_start_date"] == "2026-01-01"
    assert reloaded.auth.risk_level == "Medium"
    assert auth_quant.score == 1.0
    assert (integrity_quant.d, integrity_quant.a, integrity_quant.k, integrity_quant.rk) == (
        CHECK,
        CHECK,
        CROSS,
        1.2,
    )
    assert [item.product_name for item in auth_products] == ["TLS Gateway"]
    assert reloaded.boundary.products == []
    assert boundary_products == []


def test_network_boundary_quant_and_evidence_use_boundary_detail(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = NetworkService(engine)
    subsystem = _first_subsystem(engine, project_id)
    channel = service.create_channel(subsystem.id, "Internet Access")
    details = service.load_details(channel.id)

    rule_ref = service.evidence_ref_for_boundary(details.boundary.id)

    assert rule_ref.unit_type == MeasureUnit.NETWORK_BOUNDARY_INTEGRITY.value
    assert rule_ref.related_id == details.boundary.id


def test_delete_network_channel_removes_quant_evidence_and_products_for_its_details_only(
    tmp_path,
):
    engine = _engine(tmp_path)
    project_id = _project_id(engine, "NET-DEL-1")
    other_project_id = _project_id(engine, "NET-DEL-2")
    service = NetworkService(engine)
    target_subsystem = _first_subsystem(engine, project_id, "Portal")
    other_subsystem = _first_subsystem(engine, other_project_id, "Portal")
    target = service.create_channel(target_subsystem.id, "Target Channel")
    other = service.create_channel(other_subsystem.id, "Other Channel")
    target_details = service.load_details(target.id)
    other_details = service.load_details(other.id)

    QuantService(engine, project_id=project_id).save(
        MeasureUnit.NETWORK_AUTH.value,
        target_details.auth.id,
        d=CHECK,
        a=CHECK,
        k=CHECK,
        ra=1,
        rk=1,
    )
    QuantService(engine, project_id=other_project_id).save(
        MeasureUnit.NETWORK_AUTH.value,
        other_details.auth.id,
        d=CHECK,
        a=CHECK,
        k=CHECK,
        ra=1,
        rk=1,
    )
    ProductService(engine).save_products(
        project_id,
        MeasureUnit.NETWORK_AUTH.value,
        target.id,
        [{"name": "Delete Me"}],
    )
    ProductService(engine).save_products(
        other_project_id,
        MeasureUnit.NETWORK_AUTH.value,
        other.id,
        [{"name": "Keep Me"}],
    )
    with session_scope(engine) as session:
        session.add(
            models.EvidenceImage(
                project_id=project_id,
                unit_type=MeasureUnit.NETWORK_AUTH.value,
                related_id=target_details.auth.id,
                file_name="1. network-auth.png",
                original_name="source.png",
                caption="",
                checksum="abc",
            )
        )

    result = service.delete_channel(target.id)

    assert result.success is True
    assert QuantService(engine, project_id=project_id).exists_for_related(
        target_details.auth.id,
        unit_type=MeasureUnit.NETWORK_AUTH.value,
    ) is False
    assert QuantService(engine, project_id=other_project_id).exists_for_related(
        other_details.auth.id,
        unit_type=MeasureUnit.NETWORK_AUTH.value,
    ) is True
    assert ProductService(engine).load_products(
        project_id,
        MeasureUnit.NETWORK_AUTH.value,
        target.id,
    ) == []
    assert [
        item.product_name
        for item in ProductService(engine).load_products(
            other_project_id,
            MeasureUnit.NETWORK_AUTH.value,
            other.id,
        )
    ] == ["Keep Me"]
    with session_scope(engine) as session:
        assert session.get(models.NetworkChannel, target.id) is None
        assert session.get(models.NetworkChannel, other.id) is not None
        assert session.scalar(
            select(models.EvidenceImage).where(
                models.EvidenceImage.project_id == project_id,
                models.EvidenceImage.related_id == target_details.auth.id,
            )
        ) is None


def test_delete_network_channel_preserves_other_detail_product_when_channel_id_collides(
    tmp_path,
):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = NetworkService(engine)
    subsystem = _first_subsystem(engine, project_id)
    other = service.create_channel(subsystem.id, "Other Channel")

    with session_scope(engine) as session:
        other_auth = session.scalar(
            select(models.NetworkAuthDetail).where(
                models.NetworkAuthDetail.network_channel_id == other.id
            )
        )
        other_auth.id = 100
    with session_scope(engine) as session:
        session.add(
            models.NetworkChannel(
                id=100,
                project_id=project_id,
                network_subsystem_id=subsystem.id,
                name="Target Channel",
                sort_order=99,
            )
        )
        session.flush()
        session.add_all(
            [
                models.NetworkAuthDetail(
                    project_id=project_id,
                    network_channel_id=100,
                    sort_order=0,
                ),
                models.NetworkIntegrityDetail(
                    project_id=project_id,
                    network_channel_id=100,
                    sort_order=1,
                ),
                models.NetworkConfidentialityDetail(
                    project_id=project_id,
                    network_channel_id=100,
                    sort_order=2,
                ),
                models.NetworkBoundaryIntegrityDetail(
                    project_id=project_id,
                    network_channel_id=100,
                    sort_order=3,
                ),
            ]
        )
    ProductService(engine).save_products(
        project_id,
        MeasureUnit.NETWORK_AUTH.value,
        100,
        [{"name": "Other Detail Legacy Product"}],
    )

    result = service.delete_channel(100)

    assert result.success is True
    assert "ambiguous_network_channel_product:auth" in result.warnings
    assert [
        item.product_name
        for item in ProductService(engine).load_products(
            project_id,
            MeasureUnit.NETWORK_AUTH.value,
            100,
        )
    ] == ["Other Detail Legacy Product"]
    with session_scope(engine) as session:
        assert session.get(models.NetworkChannel, 100) is None
        assert session.get(models.NetworkChannel, other.id) is not None
        assert session.get(models.NetworkAuthDetail, 100) is not None
