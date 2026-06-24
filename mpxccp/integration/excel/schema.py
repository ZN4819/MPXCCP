from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SheetNames:
    basic_info: str = "系统基本信息"
    physical: str = "物理和环境安全"
    device: str = "设备和计算安全"
    network: str = "网络和通信安全"
    application: str = "应用和数据安全"


@dataclass(frozen=True)
class ApplicationSections:
    user_auth: str = "【用户身份鉴别】"
    access_integrity: str = "【访问控制信息完整性】"
    important_data: str = "【重要数据安全】"
    non_repudiation: str = "【关键业务行为 - 不可否认性】"


SHEET_NAMES = SheetNames()
APPLICATION_SECTIONS = ApplicationSections()

MAX_WORKBOOK_SIZE_BYTES = 50 * 1024 * 1024
PRODUCT_TEXT_PATTERN = "产品名称(厂商,证书:证书编号,等级:认证等级,用途:用途说明)"
QUANT_COLUMNS = ("d", "a", "k", "ra", "rk")

PHYSICAL_OBJECT_COLUMNS = (
    "name",
    "interview_record",
    "location",
    "access_control_system",
    "video_system",
)
PHYSICAL_AUTH_COLUMNS = (
    "auth_methods",
    "crypto_usage",
    "algorithm",
    "compliance_status",
    "product_compliance",
    "products",
    *QUANT_COLUMNS,
    "guarded",
    "registered",
    "accompanied",
    "realtime_monitoring",
    "risk_level",
    "risk_analysis",
    "mitigation_available",
    "mitigation_note",
    "mitigated_level",
    "remediation",
)
PHYSICAL_INTEGRITY_COLUMNS = (
    "implementation",
    "algorithm",
    "compliance_status",
    "product_compliance",
    "products",
    *QUANT_COLUMNS,
    "risk_level",
    "risk_analysis",
    "remediation",
)
PHYSICAL_COLUMNS = (
    *PHYSICAL_OBJECT_COLUMNS,
    *PHYSICAL_AUTH_COLUMNS,
    *PHYSICAL_INTEGRITY_COLUMNS,
    *PHYSICAL_INTEGRITY_COLUMNS,
)

DEVICE_OBJECT_COLUMNS = ("name", "interview_record")
DEVICE_AUTH_COLUMNS = (
    "auth_methods",
    "crypto_usage",
    "algorithm",
    "compliance_status",
    "product_compliance",
    "products",
    *QUANT_COLUMNS,
    "risk_level",
    "risk_analysis",
    "mitigation_available",
    "mitigation_note",
    "mitigated_level",
    "remediation",
)
DEVICE_REMOTE_COLUMNS = (
    "remote_position",
    "centralized_management",
    "crypto_usage",
    "compliance_status",
    "product_compliance",
    "products",
    *QUANT_COLUMNS,
    "risk_level",
    "risk_analysis",
    "mitigation_available",
    "mitigation_note",
    "mitigated_level",
    "remediation",
    "remote_protocol",
    "certificate_algorithm",
    "certificate_source",
    "certificate_start_date",
    "certificate_end_date",
    "confidentiality_algorithm",
    "integrity_algorithm",
    "other_info",
)
DEVICE_INTEGRITY_COLUMNS = (
    "implementation_status",
    "algorithm",
    "compliance_status",
    "product_compliance",
    "products",
    *QUANT_COLUMNS,
    "risk_level",
    "risk_analysis",
    "remediation",
)
DEVICE_COLUMNS = (
    *DEVICE_OBJECT_COLUMNS,
    *DEVICE_AUTH_COLUMNS,
    *DEVICE_REMOTE_COLUMNS,
    *DEVICE_INTEGRITY_COLUMNS,
    *DEVICE_INTEGRITY_COLUMNS,
    *DEVICE_INTEGRITY_COLUMNS,
)

NETWORK_OBJECT_COLUMNS = ("subsystem_name", "channel_name", "interview_record")
NETWORK_AUTH_COLUMNS = (
    "owning_subsystem",
    "network_environment",
    "client_type",
    "server_type",
    "implementation_status",
    "algorithm",
    "compliance_status",
    "product_compliance",
    "protocol",
    "certificate_algorithm",
    "certificate_source",
    "certificate_start_date",
    "certificate_end_date",
    "certificate_other_info",
    "products",
    *QUANT_COLUMNS,
    "risk_level",
    "risk_analysis",
    "mitigation_available",
    "mitigation_note",
    "mitigated_level",
    "remediation",
)
NETWORK_INTEGRITY_COLUMNS = (
    "implementation_status",
    "algorithm",
    "compliance_status",
    "product_compliance",
    "products",
    *QUANT_COLUMNS,
    "risk_level",
    "risk_analysis",
    "remediation",
)
NETWORK_CONFIDENTIALITY_COLUMNS = (
    "implementation_status",
    "algorithm",
    "compliance_status",
    "product_compliance",
    "products",
    *QUANT_COLUMNS,
    "risk_level",
    "risk_analysis",
    "mitigation_available",
    "mitigation_note",
    "mitigated_level",
    "remediation",
)
NETWORK_COMMON_UNIT_COLUMNS = NETWORK_CONFIDENTIALITY_COLUMNS
NETWORK_BOUNDARY_COLUMNS = (
    "compliance_status",
    "product_compliance",
    "boundary_product_level",
    *QUANT_COLUMNS,
    "risk_level",
    "risk_analysis",
    "remediation",
)
NETWORK_COLUMNS = (
    *NETWORK_OBJECT_COLUMNS,
    *NETWORK_AUTH_COLUMNS,
    *NETWORK_INTEGRITY_COLUMNS,
    *NETWORK_CONFIDENTIALITY_COLUMNS,
    *NETWORK_BOUNDARY_COLUMNS,
)

APPLICATION_USER_COLUMNS = (
    "subsystem_name",
    "name",
    "interview_record",
    "auth_methods",
    "crypto_usage",
    "algorithm",
    "compliance_status",
    "product_compliance",
    "products",
    *QUANT_COLUMNS,
    "key_management",
    "risk_level",
    "risk_analysis",
    "mitigation_available",
    "mitigation_note",
    "mitigated_level",
    "remediation",
)
APPLICATION_ACCESS_COLUMNS = (
    "subsystem_name",
    "name",
    "interview_record",
    "implementation_status",
    "algorithm",
    "compliance_status",
    "product_compliance",
    "products",
    *QUANT_COLUMNS,
    "key_management",
    "risk_level",
    "risk_analysis",
    "remediation",
)
IMPORTANT_DATA_UNIT_COLUMNS = (
    "implementation_status",
    "algorithm",
    "mechanism_description",
    "image_path",
    "compliance_status",
    "product_compliance",
    "products",
    *QUANT_COLUMNS,
    "related_channel",
    "key_management",
    "risk_level",
    "risk_analysis",
    "mitigation_available",
    "mitigation_note",
    "mitigated_level",
    "remediation",
)
IMPORTANT_DATA_TRANSPORT_COLUMNS = IMPORTANT_DATA_UNIT_COLUMNS
IMPORTANT_DATA_STORAGE_COLUMNS = tuple(
    column for column in IMPORTANT_DATA_UNIT_COLUMNS if column != "related_channel"
)
IMPORTANT_DATA_TRANSPORT_INTEGRITY_COLUMNS = tuple(
    column
    for column in IMPORTANT_DATA_TRANSPORT_COLUMNS
    if column not in {"mitigation_available", "mitigation_note", "mitigated_level"}
)
APPLICATION_IMPORTANT_DATA_COLUMNS = (
    "subsystem_name",
    "name",
    "data_type",
    "interview_record",
    *IMPORTANT_DATA_TRANSPORT_COLUMNS,
    *IMPORTANT_DATA_STORAGE_COLUMNS,
    *IMPORTANT_DATA_TRANSPORT_INTEGRITY_COLUMNS,
    *IMPORTANT_DATA_STORAGE_COLUMNS,
)
APPLICATION_BUSINESS_COLUMNS = (
    "subsystem_name",
    "name",
    "interview_record",
    "implementation_status",
    "algorithm",
    "mechanism_description",
    "image_path",
    "compliance_status",
    "product_compliance",
    "products",
    *QUANT_COLUMNS,
    "key_management",
    "risk_level",
    "risk_analysis",
    "mitigation_available",
    "mitigation_note",
    "mitigated_level",
    "remediation",
)
