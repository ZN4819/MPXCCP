from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine

from mpxccp.domain.constants import CHECK, CROSS, SLASH
from mpxccp.services.application_service import ApplicationService
from mpxccp.services.basic_info_service import BasicInfoService
from mpxccp.services.device_service import DeviceService
from mpxccp.services.network_service import NetworkService
from mpxccp.services.physical_service import PhysicalService
from mpxccp.services.scoring_service import ScoringService


@dataclass(frozen=True)
class SampleProjectRefs:
    project_id: int
    subsystems: tuple[str, str]
    physical_object_id: int
    device_object_id: int
    network_channel_id: int
    application_user_id: int
    access_control_id: int
    important_data_id: int
    business_action_id: int
    certified_product_name: str
    uncertified_product_name: str


class SampleDataBuilder:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.last_refs: SampleProjectRefs | None = None

    def create_full_project(self) -> int:
        project_id = self._create_basic_info()
        physical_object_id = self._create_physical(project_id)
        device_object_id = self._create_device(project_id)
        network_channel_id = self._create_network(project_id)
        application_refs = self._create_application(project_id, network_channel_id)
        self._create_management_scores(project_id)
        self.last_refs = SampleProjectRefs(
            project_id=project_id,
            subsystems=("业务系统", "管理端"),
            physical_object_id=physical_object_id,
            device_object_id=device_object_id,
            network_channel_id=network_channel_id,
            application_user_id=application_refs["user_id"],
            access_control_id=application_refs["access_control_id"],
            important_data_id=application_refs["important_data_id"],
            business_action_id=application_refs["business_action_id"],
            certified_product_name="端到端门禁密码模块",
            uncertified_product_name="端到端门禁记录模块",
        )
        return project_id

    def _create_basic_info(self) -> int:
        result = BasicInfoService(self.engine).save_full_basic_info(
            flow_no="E2E-001",
            system_name="端到端验收系统",
            client_name="委托方",
            assessment_org="测评机构",
            contact_name="项目联系人",
            contact_phone="13800000000",
            assessor_name="评估人员",
            assessor_phone="13900000000",
            interview_time="2026-06-26",
            system_info={
                "business_description": "支撑端到端验收的业务系统",
                "security_level": "三级",
                "deployment_mode": "本地部署",
            },
            crypto_application_info={
                "application_scope": "身份鉴别、数据保护、不可否认",
                "algorithm_description": "SM2、SM3、SM4",
                "key_management_description": "集中密钥管理",
                "product_description": "使用多类商用密码产品",
                "review_method": "专家评审",
                "review_org": "方案评审机构",
                "review_date": "2026-06-20",
            },
            subsystems=("业务系统", "管理端"),
        )
        if not result.success or result.project_id is None:
            raise AssertionError(f"failed to create sample project: {result}")
        return result.project_id

    def _create_physical(self, project_id: int) -> int:
        service = PhysicalService(self.engine)
        obj = service.create_object(project_id, "主机房")
        result = service.save_detail(
            obj.id,
            {
                "object": {
                    "name": "主机房",
                    "location": "一层东侧",
                    "access_control_system": "门禁系统 V1",
                    "video_system": "视频系统 V2",
                    "interview_record": "已访谈机房值守人员",
                },
                "units": {
                    "auth": {
                        "auth_methods": "指纹,门禁卡",
                        "crypto_usage": "已使用",
                        "algorithm": "SM4",
                        "compliance_status": "符合",
                        "product_compliance": "符合",
                        "risk_level": "低风险",
                        "risk_analysis": "身份鉴别风险可控",
                        "remediation": "持续维护值守登记",
                        "quant": {"d": CHECK, "a": CHECK, "k": CHECK, "ra": 1, "rk": 1},
                        "products": [
                            {
                                "name": "端到端门禁密码模块",
                                "vendor": "厂商A",
                                "certificate_no": "CERT-E2E-PHY-001",
                                "level": "二级",
                                "usage": "身份鉴别",
                            }
                        ],
                    },
                    "access_integrity": {
                        "implementation": "门禁记录具备完整性校验",
                        "algorithm": "SM3",
                        "risk_level": "中风险",
                        "risk_analysis": "门禁记录留存周期需加强",
                        "remediation": "完善记录留存和抽查",
                        "quant": {"d": CHECK, "a": CROSS, "k": CHECK, "ra": 1, "rk": 1},
                        "products": [
                            {
                                "name": "端到端门禁记录模块",
                                "vendor": "厂商B",
                                "certificate_no": "",
                                "level": "二级",
                                "usage": "门禁记录完整性",
                            }
                        ],
                    },
                    "video_integrity": {
                        "implementation": "视频记录完整性保护未覆盖全部摄像头",
                        "algorithm": "SM3",
                        "risk_level": "高风险",
                        "risk_analysis": "视频记录可能被篡改",
                        "remediation": "补充视频完整性校验",
                        "quant": {"d": CROSS, "a": SLASH, "k": SLASH, "ra": 1, "rk": 1},
                    },
                },
            },
        )
        self._assert_success(result.success, "physical")
        return obj.id

    def _create_device(self, project_id: int) -> int:
        service = DeviceService(self.engine)
        device = service.create_object(project_id, "业务服务器")
        result = service.save_detail(
            device.id,
            {
                "object": {
                    "name": "业务服务器",
                    "device_type": "服务器",
                    "location": "数据中心 A 区",
                    "management_address": "10.0.0.8",
                    "interview_record": "已访谈运维人员",
                    "description": "承载核心业务",
                },
                "units": {
                    "auth": {
                        "auth_methods": "口令,USBKey",
                        "login_channel": "本地控制台",
                        "algorithm": "SM3",
                        "risk_level": "低风险",
                        "risk_analysis": "设备登录身份鉴别有效",
                        "remediation": "持续审计登录策略",
                        "quant": {"d": CHECK, "a": CHECK, "k": CHECK, "ra": 1, "rk": 1},
                    },
                    "remote_management": {
                        "remote_protocol": "SSH",
                        "certificate_usage": "使用运维证书",
                        "channel_protection": "专用通道",
                        "quant": {"d": CHECK, "a": CHECK, "k": CROSS, "ra": 1, "rk": 1.2},
                    },
                    "access_integrity": {
                        "access_control_policy": "最小权限",
                        "integrity_method": "SM3 摘要",
                        "quant": {"d": CHECK, "a": CHECK, "k": CHECK, "ra": 1, "rk": 1},
                    },
                    "log_integrity": {
                        "log_source": "安全审计日志",
                        "integrity_method": "SM3 摘要",
                        "quant": {"d": CHECK, "a": CROSS, "k": CHECK, "ra": 1, "rk": 1},
                    },
                    "executable_integrity": {
                        "executable_scope": "核心服务程序",
                        "integrity_method": "签名校验",
                        "quant": {"d": CROSS, "a": SLASH, "k": SLASH, "ra": 1, "rk": 1},
                    },
                },
            },
        )
        self._assert_success(result.success, "device")
        return device.id

    def _create_network(self, project_id: int) -> int:
        service = NetworkService(self.engine)
        service.sync_from_basic_subsystems(project_id)
        subsystem = service.list_subsystems(project_id)[0]
        channel = service.create_channel(subsystem.id, "业务 HTTPS 信道")
        result = service.save_channel_detail(
            channel.id,
            {
                "channel": {
                    "name": "业务 HTTPS 信道",
                    "source": "互联网",
                    "target": "业务系统",
                    "protocol": "HTTPS",
                    "network_environment": "互联网",
                    "client_type": "浏览器",
                    "server_type": "网关",
                    "interview_record": "已访谈网络管理员",
                },
                "units": {
                    "auth": {
                        "auth_methods": "TLS 证书",
                        "algorithm": "SM2",
                        "certificate_usage": "CA 证书",
                        "risk_level": "低风险",
                        "risk_analysis": "通信实体身份鉴别有效",
                        "remediation": "保持证书续期",
                        "quant": {"d": CHECK, "a": CHECK, "k": CHECK, "ra": 1, "rk": 1},
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
                        "boundary_device": "边界防火墙",
                        "boundary_product_level": "二级",
                        "integrity_method": "ACL 签名",
                        "quant": {"d": CHECK, "a": CROSS, "k": CHECK, "ra": 1, "rk": 1},
                    },
                },
            },
        )
        self._assert_success(result.success, "network")
        return channel.id

    def _create_application(self, project_id: int, network_channel_id: int) -> dict[str, int]:
        service = ApplicationService(self.engine)
        service.sync_from_basic_subsystems(project_id)
        subsystem = service.list_subsystems(project_id)[0]
        user = service.create_user(subsystem.id, "系统管理员")
        access_control = service.create_access_control(subsystem.id, "权限矩阵")
        important_data = service.create_important_data(subsystem.id, "交易数据", "业务数据")
        business_action = service.create_business_action(subsystem.id, "订单提交")

        self._assert_success(
            service.save_user_detail(
                user.id,
                {
                    "object": {
                        "name": "系统管理员",
                        "role": "管理员",
                        "login_method": "口令+动态令牌",
                        "interview_record": "已访谈应用管理员",
                    },
                    "units": {
                        "user_auth": {
                            "auth_methods": "口令,动态令牌",
                            "crypto_usage": "已使用",
                            "algorithm": "SM3",
                            "key_management": "集中密钥管理",
                            "risk_level": "低风险",
                            "risk_analysis": "应用用户身份鉴别有效",
                            "remediation": "持续审计账号权限",
                            "quant": {"d": CHECK, "a": CHECK, "k": CHECK, "ra": 1, "rk": 1},
                        }
                    },
                },
            ).success,
            "application user",
        )
        self._assert_success(
            service.save_access_control_detail(
                access_control.id,
                {
                    "object": {
                        "name": "权限矩阵",
                        "scope": "后台管理端",
                        "policy_description": "基于角色授权",
                    },
                    "units": {
                        "access_integrity": {
                            "access_control_policy": "角色权限审批",
                            "integrity_method": "SM3 摘要",
                            "quant": {"d": CHECK, "a": CROSS, "k": CHECK, "ra": 1, "rk": 1},
                        }
                    },
                },
            ).success,
            "application access control",
        )
        self._assert_success(
            service.save_important_data_detail(
                important_data.id,
                {
                    "object": {
                        "name": "交易数据",
                        "data_type": "业务数据",
                        "data_location": "数据库 A",
                        "business_description": "记录订单和支付流水",
                        "interview_record": "已访谈 DBA",
                    },
                    "units": {
                        "transport_confidentiality": {
                            "network_channel_id": network_channel_id,
                            "encryption_method": "TLS",
                            "quant": {"d": CHECK, "a": CHECK, "k": CHECK, "ra": 1, "rk": 1},
                        },
                        "storage_confidentiality": {
                            "storage_location": "数据库 A",
                            "encryption_method": "TDE",
                            "quant": {"d": CHECK, "a": CHECK, "k": CROSS, "ra": 1, "rk": 1.2},
                        },
                        "transport_integrity": {
                            "network_channel_id": network_channel_id,
                            "integrity_method": "TLS MAC",
                            "quant": {"d": CHECK, "a": CHECK, "k": CHECK, "ra": 1, "rk": 1},
                        },
                        "storage_integrity": {
                            "storage_location": "数据库 A",
                            "integrity_method": "SM3 摘要",
                            "quant": {"d": CROSS, "a": SLASH, "k": SLASH, "ra": 1, "rk": 1},
                        },
                    },
                },
            ).success,
            "application important data",
        )
        self._assert_success(
            service.save_business_action_detail(
                business_action.id,
                {
                    "object": {
                        "name": "订单提交",
                        "description": "客户提交订单的关键业务行为",
                    },
                    "units": {
                        "non_repudiation": {
                            "signature_method": "SM2 签名",
                            "timestamp_method": "可信时间戳",
                            "certificate_usage": "签名证书",
                            "quant": {"d": CHECK, "a": CHECK, "k": CHECK, "ra": 1, "rk": 1},
                        }
                    },
                },
            ).success,
            "application business action",
        )
        return {
            "user_id": user.id,
            "access_control_id": access_control.id,
            "important_data_id": important_data.id,
            "business_action_id": business_action.id,
        }

    def _create_management_scores(self, project_id: int) -> None:
        scoring = ScoringService(self.engine)
        for indicator_no, compliance in {
            23: "符合",
            24: "部分符合",
            25: "不符合",
            26: "不适用",
            29: "符合",
            34: "部分符合",
            39: "不符合",
        }.items():
            scoring.save_management_score(project_id, indicator_no, compliance)

    def _assert_success(self, success: bool, area: str) -> None:
        if not success:
            raise AssertionError(f"failed to create sample {area} data")
