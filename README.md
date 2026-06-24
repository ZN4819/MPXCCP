# MPXCCP 商用密码应用安全性评估实施工具

本仓库用于开发一套面向 Windows 本地运行的“商用密码应用安全性评估实施工具”。工具面向评估人员、项目负责人、复核人员和工具维护人员，目标是在单机环境中完成被测系统信息采集、四类技术域测评对象维护、量化评估、风险判定、证据图片管理、评分、Excel 导入导出和问题清单生成。

## 当前状态

当前仓库已完成需求、设计、实施计划、Task 1 工程初始化、Task 2 领域规则、Task 3 持久化基础、Task 4 项目生命周期服务、Task 5 共享服务、Task 6 桌面主窗口壳、Task 7 通用 UI 控件、Task 8 物理和环境安全模块、Task 9 设备和计算安全模块、Task 10 网络和通信安全模块和 Task 11 应用和数据安全模块。Task 11 已建立应用子系统同步、四类应用对象仓储/服务/页面，覆盖七类应用测评单元详情创建、保存、量化/证据详情关联、产品外层对象关联、传输单元通信信道选择、同步前保存、删除范围和主窗口接入。

- `开发需求文档.md`：最高优先级需求基线，记录功能、数据结构、交互行为、评分公式、Excel 协议、证据文件协议、保存协议和兼容边界。
- `开发设计方案.md`：开发设计方案，明确推荐技术栈、总体架构、数据模型、模块边界、测试与验收方案。
- `docs/superpowers/plans/2026-06-23-commercial-crypto-eval-tool-implementation.md`：详细开发实施计划，按任务和并行 Wave 拆分工程落地步骤。
- `AGENTS.md`：面向后续开发代理的仓库级工作规则，包含文档优先级、关键业务不变量、UI 设计约束、测试要求和完成标准。
- `docs/阶段记录.md`：按阶段记录实施内容、验证结果、文档同步和远程分支。

## 当前工程入口

- 包入口：`mpxccp/main.py`
- 启动桩：`mpxccp/bootstrap.py`
- 领域规则：`mpxccp/domain/`
- 配置与路径：`mpxccp/config/`
- ORM 模型：`mpxccp/models/`
- 会话边界：`mpxccp/repositories/session.py`
- 迁移服务：`mpxccp/services/migration_service.py`
- 项目生命周期服务：`mpxccp/services/project_service.py`
- 基本信息服务：`mpxccp/services/basic_info_service.py`
- 共享 Repository：`mpxccp/repositories/shared_repo.py`、`mpxccp/repositories/knowledge_repo.py`
- 共享业务服务：`mpxccp/services/quant_service.py`、`mpxccp/services/risk_service.py`、`mpxccp/services/product_service.py`、`mpxccp/services/evidence_service.py`、`mpxccp/services/knowledge_service.py`
- 物理和环境安全：`mpxccp/repositories/physical_repo.py`、`mpxccp/services/physical_service.py`、`mpxccp/ui/pages/physical_page.py`
- 设备和计算安全：`mpxccp/repositories/device_repo.py`、`mpxccp/services/device_service.py`、`mpxccp/ui/pages/device_page.py`
- 网络和通信安全：`mpxccp/repositories/network_repo.py`、`mpxccp/services/network_service.py`、`mpxccp/ui/pages/network_page.py`
- 应用和数据安全：`mpxccp/repositories/application_repo.py`、`mpxccp/services/application_service.py`、`mpxccp/ui/pages/application_page.py`
- 证据适配器：`mpxccp/integration/evidence/file_store.py`、`mpxccp/integration/evidence/thumbnails.py`
- UI 主窗口：`mpxccp/ui/main_window.py`
- 通用 UI 控件：`mpxccp/ui/widgets/`
- UI 资源：`mpxccp/resources/styles/app.qss`、`mpxccp/resources/icons/app.png`
- 资源校验：`mpxccp/integration/packaging/resource_check.py`
- 基础测试：`tests/unit/test_bootstrap.py`
- UI 测试：`tests/ui/test_main_window.py`、`tests/ui/test_physical_page.py`、`tests/ui/test_device_page.py`、`tests/ui/test_network_page.py`、`tests/ui/test_quant_widget.py`、`tests/ui/test_autosave_manager.py`、`tests/ui/test_date_input.py`、`tests/ui/test_risk_widget.py`、`tests/ui/test_product_list_widget.py`、`tests/ui/test_evidence_dialog.py`、`tests/ui/test_widget_exports.py`
- 领域测试：`tests/unit/test_quant_rules.py`、`tests/unit/test_scoring_rules.py`、`tests/unit/test_association_rules.py`
- 数据库测试：`tests/integration/test_database_schema.py`
- 项目与基本信息测试：`tests/integration/test_project_lifecycle.py`、`tests/integration/test_basic_info_service.py`
- 共享服务测试：`tests/integration/test_shared_services.py`、`tests/integration/test_evidence_service.py`
- 物理模块测试：`tests/integration/test_physical_service.py`
- 设备模块测试：`tests/integration/test_device_service.py`
- 网络模块测试：`tests/integration/test_network_service.py`
- 资源校验测试：`tests/integration/test_resource_check.py`
- 工程配置：`pyproject.toml`

## 推荐技术栈

- Python 3.11+
- PySide6
- SQLite
- SQLAlchemy 2.x
- openpyxl
- Pillow
- pytest
- pytest-qt
- ruff
- PyInstaller

## 目标架构

项目采用本地桌面分层架构：

- UI 层：PySide6 主窗口、业务页、通用控件和交互反馈。
- 应用服务层：项目、详情保存、评分、导入导出、证据、知识库等业务用例。
- 领域层：枚举、评分公式、量化规则、关联矩阵、问题清单模板。
- 仓储层：ORM 模型、Repository、事务边界、迁移。
- 适配器层：Excel、图片缩略图、证据文件、配置、日志、资源路径和打包。

## 核心业务范围

- 项目生命周期管理：新建、打开、保存、软删除、恢复、硬删除支撑。
- 基本信息维护：项目基本信息、系统基本信息、子系统、密码应用情况。
- 四类技术域：物理和环境安全、设备和计算安全、网络和通信安全、应用和数据安全。
- 通用能力：量化评估、风险判定、密码产品、证据图片、知识库。
- 评分：41 项指标、技术域评分、管理域评分、总分计算、评分汇总持久化。
- 导入导出：访谈模板导入、评估数据导出、打分表导入导出、问题清单导出、知识库导入导出。
- 数据治理：本地数据初始化、兼容迁移、项目范围解析、关联完整性检查。
- 安装运行：Windows 本地运行、资源校验、用户目录数据存储。

## 开发原则

- `开发需求文档.md` 是验收基线，不得随意改变其中记录的当前行为。
- 只读加载和写入保存必须分离。
- 评分、Excel、证据、密码产品、知识库等业务逻辑必须服务化。
- 量化评估和证据通常关联测评单元详情；密码产品必须保留历史兼容关联语义。
- Excel sheet 名称、列顺序、合并单元格、颜色、空值表达和产品文本格式都属于验收范围。
- UI 设计、重设计、原型或视觉实现工作必须先按 `AGENTS.md` 使用 Product Design 技能路由。

## 实施入口

后续开发按实施计划推进：

```text
docs/superpowers/plans/2026-06-23-commercial-crypto-eval-tool-implementation.md
```

建议顺序：

1. 工程初始化与开发工具链。已完成。
2. 领域规则。已完成。
3. 数据库基础。已完成。
4. 项目生命周期、基本信息和子系统同步。已完成。
5. 共享服务。已完成。
6. UI 主窗口壳、资源、样式和启动行为。已完成。
7. 通用 UI 控件和自动保存管理器。已完成。
8. 物理和环境安全模块。已完成。
9. 设备和计算安全模块。已完成。
10. 网络和通信安全模块。已完成。
11. 应用和数据安全模块。已完成。
12. 评分、Excel、问题清单和知识库。下一步。
13. 数据治理、安装包和端到端验收。

## 未来验证命令

当前已可运行的最小验证：

```powershell
uv venv --python 3.11 .venv
uv pip install --python .venv\Scripts\python.exe -e ".[dev]"
.venv\Scripts\python.exe -m pytest tests/unit/test_bootstrap.py -q
.venv\Scripts\python.exe -m pytest tests/unit/test_quant_rules.py tests/unit/test_scoring_rules.py tests/unit/test_association_rules.py -q
.venv\Scripts\python.exe -m pytest tests/integration/test_database_schema.py -q
.venv\Scripts\python.exe -m pytest tests/integration/test_project_lifecycle.py tests/integration/test_basic_info_service.py -q
.venv\Scripts\python.exe -m pytest tests/integration/test_shared_services.py tests/integration/test_evidence_service.py -q
.venv\Scripts\python.exe -m pytest tests/ui/test_main_window.py tests/integration/test_resource_check.py tests/unit/test_bootstrap.py -q
.venv\Scripts\python.exe -m pytest tests/integration/test_physical_service.py tests/ui/test_physical_page.py -q
.venv\Scripts\python.exe -m pytest tests/integration/test_device_service.py tests/ui/test_device_page.py -q
.venv\Scripts\python.exe -m pytest tests/integration/test_network_service.py tests/ui/test_network_page.py -q
.venv\Scripts\python.exe -m pytest tests/integration/test_application_service.py tests/ui/test_application_page.py -q
.venv\Scripts\python.exe -m pytest tests/ui/test_quant_widget.py tests/ui/test_autosave_manager.py tests/ui/test_date_input.py tests/ui/test_risk_widget.py tests/ui/test_product_list_widget.py tests/ui/test_evidence_dialog.py tests/ui/test_widget_exports.py -q
```

完整工程逐步实现后，最终回归应至少包含：

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
powershell -ExecutionPolicy Bypass -File scripts/check_resources.ps1
```
