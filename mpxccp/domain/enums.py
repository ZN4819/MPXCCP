from __future__ import annotations

from enum import StrEnum


class SecurityLayer(StrEnum):
    PHYSICAL = "物理和环境安全"
    NETWORK = "网络和通信安全"
    DEVICE = "设备和计算安全"
    APPLICATION = "应用和数据安全"
    MANAGEMENT_SYSTEM = "管理制度"
    PERSONNEL = "人员管理"
    CONSTRUCTION = "建设运行"
    EMERGENCY = "应急处置"


class MeasureUnit(StrEnum):
    PHYSICAL_AUTH = "物理访问身份鉴别"
    PHYSICAL_ACCESS_INTEGRITY = "门禁记录完整性"
    PHYSICAL_VIDEO_INTEGRITY = "视频记录完整性"
    DEVICE_AUTH = "设备登录身份鉴别"
    DEVICE_REMOTE = "远程管理通道"
    DEVICE_ACCESS_INTEGRITY = "设备访问控制完整性"
    DEVICE_LOG_INTEGRITY = "设备日志完整性"
    DEVICE_EXECUTABLE_INTEGRITY = "可执行程序完整性"
    NETWORK_AUTH = "通信实体身份鉴别"
    NETWORK_INTEGRITY = "通信过程数据完整性"
    NETWORK_CONFIDENTIALITY = "通信过程数据机密性"
    NETWORK_BOUNDARY_INTEGRITY = "网络边界访问控制完整性"
    APP_USER_AUTH = "应用用户身份鉴别"
    APP_ACCESS_INTEGRITY = "应用访问控制完整性"
    DATA_TRANSPORT_CONFIDENTIALITY = "重要数据传输机密性"
    DATA_STORAGE_CONFIDENTIALITY = "重要数据存储机密性"
    DATA_TRANSPORT_INTEGRITY = "重要数据传输完整性"
    DATA_STORAGE_INTEGRITY = "重要数据存储完整性"
    BUSINESS_ACTION_NON_REPUDIATION = "关键业务行为不可否认性"


class RiskLevel(StrEnum):
    HIGH = "高风险"
    MEDIUM = "中风险"
    LOW = "低风险"
    NONE = "无风险"
    NOT_APPLICABLE = "不适用"


class RiskMode(StrEnum):
    FULL = "完整模式"
    SIMPLE = "简化模式"


class QuantValue(StrEnum):
    PASS = "√"
    FAIL = "×"
    SLASH = "/"
    EMPTY = ""


class ComplianceStatus(StrEnum):
    COMPLIANT = "符合"
    PARTIAL = "部分符合"
    NON_COMPLIANT = "不符合"
    NOT_APPLICABLE = "不适用"


class ProductLevel(StrEnum):
    FIRST = "一级"
    SECOND = "二级"
    THIRD = "三级"


class ImportMode(StrEnum):
    REPLACE = "替换"
    APPEND = "追加"
    CANCEL = "取消"


class KnowledgeType(StrEnum):
    RISK_ANALYSIS = "风险分析"
    MITIGATION = "风险缓释"
    RECTIFICATION = "整改建议"


class KnowledgeModule(StrEnum):
    COMMON = "通用要求"
    PHYSICAL = "物理和环境"
    NETWORK = "网络和通信"
    DEVICE = "设备和计算"
    APPLICATION = "应用和数据"
    MANAGEMENT = "管理"
    OTHER = "其他"
