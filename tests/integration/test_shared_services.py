from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, select

import mpxccp.models as models
from mpxccp.domain.constants import CHECK, CROSS, SLASH
from mpxccp.repositories.session import create_engine_for_path, init_database, session_scope
from mpxccp.services.basic_info_service import BasicInfoService
from mpxccp.services.knowledge_service import KnowledgeService
from mpxccp.services.product_service import ProductService
from mpxccp.services.quant_service import QuantService
from mpxccp.services.risk_service import RiskService


def _engine(tmp_path: Path):
    engine = create_engine_for_path(tmp_path / "task5.sqlite3")
    init_database(engine)
    return engine


def _project_id(engine) -> int:
    result = BasicInfoService(engine).save_basic_info(
        flow_no="TASK5-001",
        system_name="Shared Service System",
        client_name="Client",
        assessment_org="Org",
    )
    assert result.success
    assert result.project_id is not None
    return result.project_id


def test_quant_save_is_idempotent_and_counts_effective_d_by_allowed_units(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = QuantService(engine, project_id=project_id)

    first = service.save("物理访问身份鉴别", 101, d=CHECK, a=CHECK, k=CHECK, ra=1, rk=1)
    second = service.save("物理访问身份鉴别", 101, d=CHECK, a=CHECK, k=CHECK, ra=1, rk=1)
    service.save("设备访问控制完整性", 202, d=CHECK, a=CHECK, k=CHECK, ra=1, rk=1)
    service.save("远程管理通道", 203, d=CHECK, a=CHECK, k=CROSS, ra=1, rk=1.2)
    service.save("通信过程数据机密性", 301, d=CROSS, a=SLASH, k=SLASH, ra=1, rk=1)

    assert first.record_id == second.record_id
    assert second.changed is False
    assert second.score == 1.0
    assert service.load("物理访问身份鉴别", 101).record_id == first.record_id
    assert service.count_effective_d(project_id) == 2

    with session_scope(engine) as session:
        count = session.scalar(select(func.count()).select_from(models.QuantitativeAssessment))
    assert count == 4


def test_quant_auto_rule_exposes_enabled_state_and_product_level_priority(tmp_path):
    engine = _engine(tmp_path)
    service = QuantService(engine, project_id=_project_id(engine))

    disabled = service.apply_auto_rule(d=CROSS, a=CHECK, k=CHECK)
    level_one = service.apply_auto_rule(product_level="一级")

    assert disabled.d == CROSS
    assert disabled.a == SLASH
    assert disabled.k == SLASH
    assert disabled.a_enabled is False
    assert disabled.k_enabled is False
    assert level_one.d == CHECK
    assert level_one.a == CHECK
    assert level_one.k == CROSS
    assert level_one.rk == 1.2


def test_risk_service_normalizes_final_level_and_rectification_visibility():
    service = RiskService()

    assert service.final_risk_level("高风险", True, "低风险", "完整模式") == "低风险"
    assert service.final_risk_level("高风险", False, "低风险", "完整模式") == "高风险"
    assert service.final_risk_level("无风险", True, "低风险", "简化模式") == "无风险"
    assert service.should_show_rectification("低风险") is True
    assert service.should_show_rectification("无风险") is False
    assert service.normalize_risk_fields(
        {
            "risk_level": "高风险",
            "mitigation_enabled": "是",
            "mitigated_level": "中风险",
            "rectification": "整改",
        },
        "完整模式",
    )["final_risk_level"] == "中风险"


def test_project_products_deduplicate_by_certificate_and_sync_same_certificate(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = ProductService(engine)

    service.save_products(
        project_id,
        "设备登录身份鉴别",
        1,
        [
            {
                "name": "产品A",
                "vendor": "厂商A",
                "certificate_no": "CERT-1",
                "level": "二级",
                "usage": "身份鉴别",
            }
        ],
    )
    service.save_products(
        project_id,
        "远程管理通道",
        2,
        [
            {
                "name": "产品A新版",
                "vendor": "厂商B",
                "certificate_no": "CERT-1",
                "level": "三级",
                "usage": "远程管理",
            },
            {
                "name": "无证产品",
                "vendor": "厂商C",
                "certificate_no": "",
                "level": "一级",
                "usage": "本地",
            },
        ],
    )

    products = service.list_reusable_project_products(project_id)
    remote_products = service.load_products(project_id, "远程管理通道", 2)
    auth_products = service.load_products(project_id, "设备登录身份鉴别", 1)

    assert [item.certificate_no for item in products] == ["CERT-1", ""]
    assert [item.product_name for item in products] == ["产品A新版", "无证产品"]
    assert remote_products[0].product_name == "产品A新版"
    assert remote_products[0].sort_order == 0
    assert auth_products[0].product_name == "产品A新版"
    assert auth_products[0].vendor == "厂商B"
    assert auth_products[0].usage == "远程管理"


def test_product_save_replaces_only_current_related_products(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = ProductService(engine)

    service.save_products(project_id, "设备登录身份鉴别", 1, [{"name": "旧产品"}])
    service.save_products(project_id, "远程管理通道", 2, [{"name": "保留产品"}])
    service.save_products(project_id, "设备登录身份鉴别", 1, [{"name": "新产品"}])

    assert [
        item.product_name for item in service.load_products(project_id, "设备登录身份鉴别", 1)
    ] == [
        "新产品"
    ]
    assert [item.product_name for item in service.load_products(project_id, "远程管理通道", 2)] == [
        "保留产品"
    ]


def test_knowledge_service_filters_adds_dedupes_and_replaces_entries(tmp_path):
    engine = _engine(tmp_path)
    service = KnowledgeService(engine)

    empty = service.add_entry("风险分析", "物理和环境", " ")
    first = service.add_entry("风险分析", "物理和环境", "风险文本")
    service.add_entry("风险分析", "网络和通信", "网络风险")
    service.add_entry("整改建议", "物理和环境", "整改文本")

    assert empty.success is False
    assert first.success is True
    assert [item.content for item in service.list_entries("风险分析", "物理和环境")] == ["风险文本"]
    assert [
        item.content for item in service.list_entries("风险分析", "物理和环境", show_all=True)
    ] == [
        "风险文本",
        "网络风险",
    ]
    assert [
        item.content
        for item in service.list_entries(
            "风险分析",
            "物理和环境",
            show_all=True,
            text_filter="网络",
        )
    ] == ["网络风险"]

    dedupe = service.dedupe_append(
        [
            {"type": "风险分析", "module": "物理和环境", "content": "风险文本"},
            {"type": "风险分析", "module": "物理和环境", "content": "新增风险"},
        ]
    )
    assert dedupe.payload["added"] == 1

    replace = service.replace_all(
        [{"type": "整改建议", "module": "通用要求", "content": "替换后整改"}]
    )
    assert replace.success
    assert [
        item.content for item in service.list_entries("整改建议", "通用要求", show_all=True)
    ] == [
        "替换后整改"
    ]

def test_knowledge_dedupe_ignores_disabled_duplicate_entries(tmp_path):
    engine = _engine(tmp_path)
    service = KnowledgeService(engine)
    with session_scope(engine) as session:
        session.add(
            models.KnowledgeEntry(
                entry_type="风险分析",
                module="物理和环境",
                content="旧风险",
                is_enabled=False,
            )
        )

    result = service.dedupe_append(
        [{"type": "风险分析", "module": "物理和环境", "content": "旧风险"}]
    )

    assert result.payload["added"] == 1
    assert [item.content for item in service.list_entries("风险分析", "物理和环境")] == ["旧风险"]


def test_knowledge_replace_all_rejects_empty_payload_without_clearing_existing_entries(tmp_path):
    engine = _engine(tmp_path)
    service = KnowledgeService(engine)
    service.add_entry("整改建议", "物理和环境", "已有整改")

    result = service.replace_all([{"type": "整改建议", "module": "物理和环境", "body": "字段错误"}])

    assert result.success is False
    assert result.warnings == ["no_valid_entries"]
    assert [item.content for item in service.list_entries("整改建议", "物理和环境")] == [
        "已有整改"
    ]
