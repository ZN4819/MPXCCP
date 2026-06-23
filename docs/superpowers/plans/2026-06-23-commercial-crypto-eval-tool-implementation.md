# 商用密码应用安全性评估实施工具 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于 `开发需求文档.md` 和 `开发设计方案.md`，从当前仅有文档的目录中实施一套 Windows 本地 PySide6 桌面工具，覆盖项目管理、四类技术域、评分、证据、Excel 导入导出、知识库、兼容治理和安装运行。

**Architecture:** 采用 Python + PySide6 + SQLite + SQLAlchemy + openpyxl + Pillow 的本地分层架构。UI 层只处理交互和显示，应用服务层处理业务用例，领域层集中评分/量化/关联规则，仓储层管理事务和持久化，适配器层处理 Excel、证据文件、资源路径和打包。

**Tech Stack:** Python 3.11+, PySide6, SQLAlchemy 2.x, Alembic-compatible migration runner or internal migration table, openpyxl, Pillow, pytest, pytest-qt, PyInstaller, ruff.

---

## Execution Model

当前 `F:\Codex\MPXCCP` 不是 Git 仓库。实施时第一步先初始化工程和 Git；如果执行环境已经初始化 Git，则跳过初始化但保留窄范围提交。

推荐采用子 agent 分批并行：

| Wave | 任务 | 并行性 | 说明 |
| --- | --- | --- | --- |
| 0 | Task 1-3 | 串行 | 工程骨架、领域规则、数据库基础必须先完成 |
| 1 | Task 4-7 | 可并行 | 项目基础、共享服务、UI 壳、通用控件可由不同子 agent 开发 |
| 2 | Task 8-11 | 可并行 | 物理、设备、网络、应用四个技术域边界清晰，适合四个子 agent |
| 3 | Task 12-15 | 部分并行 | 评分、Excel 导入、Excel 导出、问题清单/知识库可并行，导出打分表依赖评分接口稳定 |
| 4 | Task 16-18 | 串行为主 | 数据治理、安装打包、总体验收需要整合全部模块 |

子 agent 交付规则：

- 每个子 agent 只改自己任务列出的文件范围。
- 每个子 agent 先写或更新测试，再实现，再运行任务内验证命令。
- 每个子 agent 在交付说明中列出：改动文件、运行命令、通过/失败结果、剩余风险。
- 主 agent 在每个 Wave 后做一次集成审查，确认跨模块接口未漂移。

## Target File Structure

```text
F:\Codex\MPXCCP\
  pyproject.toml
  README.md
  AGENTS.md
  mpxccp\
    __init__.py
    main.py
    bootstrap.py
    config\
      __init__.py
      settings.py
      paths.py
      logging.py
    domain\
      __init__.py
      enums.py
      constants.py
      quant_rules.py
      scoring_rules.py
      association_rules.py
      issue_templates.py
    models\
      __init__.py
      base.py
      project.py
      basic_info.py
      technical_physical.py
      technical_device.py
      technical_network.py
      technical_application.py
      shared.py
      scoring.py
      knowledge.py
    repositories\
      __init__.py
      session.py
      project_repo.py
      basic_info_repo.py
      physical_repo.py
      device_repo.py
      network_repo.py
      application_repo.py
      shared_repo.py
      scoring_repo.py
      knowledge_repo.py
    services\
      __init__.py
      result.py
      project_service.py
      basic_info_service.py
      detail_save_service.py
      quant_service.py
      risk_service.py
      product_service.py
      evidence_service.py
      scoring_service.py
      import_service.py
      export_service.py
      knowledge_service.py
      integrity_service.py
      migration_service.py
    integration\
      __init__.py
      excel\
        __init__.py
        schema.py
        import_reader.py
        export_writer.py
        score_workbook.py
        issue_workbook.py
        workbook_styles.py
      evidence\
        __init__.py
        file_store.py
        thumbnails.py
      packaging\
        __init__.py
        resource_check.py
    ui\
      __init__.py
      main_window.py
      pages\
        __init__.py
        basic_info_page.py
        physical_page.py
        device_page.py
        network_page.py
        application_page.py
        scoring_page.py
      widgets\
        __init__.py
        autosave_manager.py
        date_input.py
        quant_widget.py
        risk_widget.py
        product_list_widget.py
        evidence_dialog.py
        image_upload_widget.py
        knowledge_picker.py
      styles\
        app.qss
    resources\
      icons\
      templates\
  tests\
    conftest.py
    fixtures\
      sample_data.py
      workbook_builders.py
    unit\
    integration\
    ui\
```

## Task 1: 工程初始化与开发工具链

**Agent:** Foundation Agent  
**Depends on:** 无  
**Parallel:** 否  

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `AGENTS.md`
- Create: `mpxccp/__init__.py`
- Create: `mpxccp/main.py`
- Create: `mpxccp/bootstrap.py`
- Create: `tests/conftest.py`
- Create: `.gitignore`

- [x] **Step 1: 初始化 Git 仓库**

Run:

```powershell
git status -sb
```

Expected if not initialized:

```text
fatal: not a git repository (or any of the parent directories): .git
```

If this exact failure appears, run:

```powershell
git init
```

Expected:

```text
Initialized empty Git repository
```

- [x] **Step 2: 创建 Python 包骨架**

Create the package directories listed in Target File Structure. Ensure `mpxccp/main.py` exposes an importable CLI entry:

```python
from __future__ import annotations

from mpxccp.bootstrap import run_app


def main() -> int:
    return run_app()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [x] **Step 3: 写入 `pyproject.toml`**

Use this baseline:

```toml
[project]
name = "mpxccp"
version = "0.1.0"
description = "商用密码应用安全性评估实施工具"
requires-python = ">=3.11"
dependencies = [
  "PySide6>=6.7",
  "SQLAlchemy>=2.0",
  "openpyxl>=3.1",
  "Pillow>=10.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "pytest-qt>=4.4",
  "ruff>=0.5",
  "pyinstaller>=6.0",
]

[project.scripts]
mpxccp = "mpxccp.main:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
qt_api = "pyside6"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

- [x] **Step 4: 写入启动桩**

`mpxccp/bootstrap.py` starts without creating the full UI yet:

```python
from __future__ import annotations


def run_app() -> int:
    return 0
```

- [x] **Step 5: 写入基础测试**

Create `tests/unit/test_bootstrap.py`:

```python
from mpxccp.bootstrap import run_app


def test_run_app_returns_zero_for_bootstrap_stub():
    assert run_app() == 0
```

- [x] **Step 6: 运行验证**

Run:

```powershell
python -m pytest tests/unit/test_bootstrap.py -q
```

Expected:

```text
1 passed
```

- [x] **Step 7: 提交**

Run:

```powershell
git add pyproject.toml README.md AGENTS.md .gitignore mpxccp tests
git commit -m "chore: initialize desktop tool project"
```

Expected:

```text
[main ...] chore: initialize desktop tool project
```

## Task 2: 领域枚举、量化规则、评分规则和关联矩阵

**Agent:** Domain Rules Agent  
**Depends on:** Task 1  
**Parallel:** Wave 0 串行核心任务  

**Files:**
- Create: `mpxccp/domain/enums.py`
- Create: `mpxccp/domain/constants.py`
- Create: `mpxccp/domain/quant_rules.py`
- Create: `mpxccp/domain/scoring_rules.py`
- Create: `mpxccp/domain/association_rules.py`
- Create: `mpxccp/domain/issue_templates.py`
- Test: `tests/unit/test_quant_rules.py`
- Test: `tests/unit/test_scoring_rules.py`
- Test: `tests/unit/test_association_rules.py`

- [x] **Step 1: 定义枚举**

`enums.py` must include stable string enums for `SecurityLayer`、`MeasureUnit`、`RiskLevel`、`RiskMode`、`QuantValue`、`ComplianceStatus`、`ProductLevel`、`ImportMode`、`KnowledgeType`、`KnowledgeModule`。Use Chinese display strings from `开发需求文档.md`.

- [x] **Step 2: 写量化规则测试**

Create tests that lock the documented behavior:

```python
from mpxccp.domain.quant_rules import apply_quant_auto_rule, calculate_object_score


def test_d_cross_disables_a_k_as_slash():
    result = apply_quant_auto_rule(d="×", a="", k="", ra=None, rk=None)
    assert result.d == "×"
    assert result.a == "/"
    assert result.k == "/"
    assert result.a_enabled is False
    assert result.k_enabled is False


def test_first_level_product_forces_a_pass_k_fail_and_rk_1_2():
    result = apply_quant_auto_rule(product_level="一级")
    assert (result.d, result.a, result.k, result.ra, result.rk) == ("√", "√", "×", 1.0, 1.2)


def test_object_score_uses_ra_when_a_fails_k_passes():
    assert calculate_object_score(d="√", a="×", k="√", ra=0.5, rk=1.0) == 0.25
```

- [x] **Step 3: 实现量化规则**

Implement pure functions:

- `apply_quant_auto_rule(...) -> QuantRuleResult`
- `normalize_quant_values(...) -> QuantValues`
- `calculate_object_score(d, a, k, ra, rk) -> float | None`
- `is_effective_d(d) -> bool`

Rules must match FR-032, SCORE-005, SCORE-016, SCORE-017.

- [x] **Step 4: 写评分规则测试**

Create tests for 41 indicators, fixed non-applicable indicators, and total score:

```python
from mpxccp.domain.scoring_rules import (
    FIXED_NOT_APPLICABLE_INDICATORS,
    build_default_indicators,
    calculate_weighted_layer_score,
)


def test_default_indicators_cover_1_to_41():
    indicators = build_default_indicators()
    assert [item.no for item in indicators] == list(range(1, 42))


def test_fixed_not_applicable_indicators():
    assert FIXED_NOT_APPLICABLE_INDICATORS == {8, 12, 17}


def test_layer_score_ignores_not_applicable_items():
    score = calculate_weighted_layer_score([(1.0, 1.0), (None, 1.0), (0.5, 2.0)])
    assert score == 2.0 / 3.0
```

- [x] **Step 5: 实现评分规则**

Implement:

- `build_default_indicators()`
- `map_indicator_to_units(indicator_no)`
- `calculate_weighted_layer_score(items)`
- `calculate_total_score(technical_score, management_score)`
- `classify_compliance(unit_score)`

- [x] **Step 6: 写关联矩阵测试**

Cover all PARENT matrices:

```python
from mpxccp.domain.association_rules import get_association_rule


def test_physical_auth_quant_and_evidence_use_detail_reference():
    rule = get_association_rule("物理访问身份鉴别")
    assert rule.quant_reference == "detail"
    assert rule.evidence_reference == "detail"
    assert "outer_object" in rule.product_compatible_references


def test_network_boundary_has_no_current_product_write_entry():
    rule = get_association_rule("网络边界访问控制完整性")
    assert rule.product_write_reference is None
```

- [x] **Step 7: 实现关联矩阵和问题清单模板常量**

`association_rules.py` must encode PARENT-001 through PARENT-008.  
`issue_templates.py` must encode EXP-016 and EXP-017 templates with named placeholders.

- [x] **Step 8: 运行验证**

Run:

```powershell
python -m pytest tests/unit/test_quant_rules.py tests/unit/test_scoring_rules.py tests/unit/test_association_rules.py -q
```

Expected:

```text
all tests passed
```

- [x] **Step 9: 提交**

```powershell
git add mpxccp/domain tests/unit/test_quant_rules.py tests/unit/test_scoring_rules.py tests/unit/test_association_rules.py
git commit -m "feat: add domain rules for quant scoring and associations"
```

## Task 3: 数据库模型、会话、迁移和 Repository 基础

**Agent:** Persistence Agent  
**Depends on:** Task 1, Task 2  
**Parallel:** Wave 0 串行核心任务  

**Files:**
- Create: `mpxccp/config/paths.py`
- Create: `mpxccp/config/settings.py`
- Create: `mpxccp/config/logging.py`
- Create: `mpxccp/models/base.py`
- Create: `mpxccp/models/project.py`
- Create: `mpxccp/models/basic_info.py`
- Create: `mpxccp/models/technical_physical.py`
- Create: `mpxccp/models/technical_device.py`
- Create: `mpxccp/models/technical_network.py`
- Create: `mpxccp/models/technical_application.py`
- Create: `mpxccp/models/shared.py`
- Create: `mpxccp/models/scoring.py`
- Create: `mpxccp/models/knowledge.py`
- Create: `mpxccp/repositories/session.py`
- Create: `mpxccp/services/migration_service.py`
- Test: `tests/integration/test_database_schema.py`

- [ ] **Step 1: 定义本地路径规则**

`paths.py` must resolve:

- Development data path under project `.local_data/mpxccp.sqlite3`.
- Installed data path under current user's writable app data directory.
- Evidence root read from settings table, not hardcoded.
- Resource path that works in source mode and PyInstaller mode.

- [ ] **Step 2: 写 schema 测试**

Create:

```python
from sqlalchemy import inspect

from mpxccp.repositories.session import create_engine_for_path, init_database


def test_database_schema_creates_core_tables(tmp_path):
    db_path = tmp_path / "tool.sqlite3"
    engine = create_engine_for_path(db_path)
    init_database(engine)
    names = set(inspect(engine).get_table_names())
    assert "projects" in names
    assert "deleted_projects" in names
    assert "quantitative_assessments" in names
    assert "crypto_products" in names
    assert "evidence_images" in names
    assert "scoring_indicators" in names
```

- [ ] **Step 3: 实现 ORM 模型**

Tables must cover:

- Project and recycle bin.
- Basic info, system info, crypto application info, subsystems.
- Physical, device, network, application outer objects and detail records.
- Quantitative assessment, crypto product, evidence image.
- Knowledge entries.
- Scoring indicators, management scores, score summary, score details.
- App settings and data version.

Use integer primary keys, `project_id` foreign keys, `sort_order`, `created_at`, `updated_at`, and indexes on `(project_id, unit_type, related_id)` for shared records.

- [ ] **Step 4: 实现会话和初始化**

`session.py` must expose:

- `create_engine_for_path(path)`
- `session_scope(engine)`
- `readonly_session_scope(engine)`
- `init_database(engine)`

`session_scope` commits on success, rolls back on exception, and closes always.

- [ ] **Step 5: 实现迁移服务**

`migration_service.py` must:

- Ensure default indicators exist.
- Ensure knowledge type/module defaults are compatible.
- Run enum cleanup idempotently.
- Record executed migration name/version in `data_versions`.

- [ ] **Step 6: 运行验证**

```powershell
python -m pytest tests/integration/test_database_schema.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 7: 提交**

```powershell
git add mpxccp/config mpxccp/models mpxccp/repositories mpxccp/services/migration_service.py tests/integration/test_database_schema.py
git commit -m "feat: add persistence schema and migration foundation"
```

## Task 4: 项目生命周期、基本信息和子系统同步

**Agent:** Project Lifecycle Agent  
**Depends on:** Task 3  
**Parallel:** Wave 1，与 Task 5、Task 6、Task 7 可并行  

**Files:**
- Create: `mpxccp/repositories/project_repo.py`
- Create: `mpxccp/repositories/basic_info_repo.py`
- Create: `mpxccp/services/result.py`
- Create: `mpxccp/services/project_service.py`
- Create: `mpxccp/services/basic_info_service.py`
- Test: `tests/integration/test_project_lifecycle.py`
- Test: `tests/integration/test_basic_info_service.py`

- [ ] **Step 1: 写项目生命周期测试**

Cover FR-010 through FR-015:

```python
def test_soft_deleted_project_is_hidden_and_recoverable(app_services):
    project = app_services.basic_info.save_basic_info(
        flow_no="LC-001",
        system_name="测试系统",
        silent=True,
    ).project
    app_services.project.soft_delete(project.id)
    assert project.id not in [item.id for item in app_services.project.list_openable()]
    app_services.project.restore([project.id])
    assert project.id in [item.id for item in app_services.project.list_openable()]
```

- [ ] **Step 2: 实现 `ServiceResult`**

Use a small result object with:

- `success: bool`
- `message: str`
- `warnings: list[str]`
- `project_id: int | None`
- `payload: dict[str, object]`

- [ ] **Step 3: 实现 ProjectService**

Methods:

- `new_project_state()`
- `list_openable()`
- `open_project(project_id)`
- `soft_delete(project_id)`
- `restore(project_ids)`
- `hard_delete(project_id)`

Hard delete must follow DEL-003 order and must not delete disk evidence files.

- [ ] **Step 4: 写基本信息测试**

Cover required fields and subsystem ordering:

```python
def test_first_basic_info_save_creates_project_and_subsystems(app_services):
    result = app_services.basic_info.save_full_basic_info(
        flow_no="LC-002",
        system_name="业务系统",
        subsystems=["门户", "管理端"],
        silent=True,
    )
    assert result.success
    assert result.project_id is not None
    assert app_services.basic_info.list_subsystems(result.project_id) == ["门户", "管理端"]
```

- [ ] **Step 5: 实现 BasicInfoService**

Methods:

- `save_basic_info(...)`
- `save_full_basic_info(...)`
- `load_basic_info(project_id)`
- `sync_subsystems(project_id, names)`
- `list_subsystems(project_id)`

Subsystem save must preserve existing IDs for same names, update sort order, and expose network/application sync events without clearing existing module data.

- [ ] **Step 6: 运行验证**

```powershell
python -m pytest tests/integration/test_project_lifecycle.py tests/integration/test_basic_info_service.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 7: 提交**

```powershell
git add mpxccp/repositories/project_repo.py mpxccp/repositories/basic_info_repo.py mpxccp/services/result.py mpxccp/services/project_service.py mpxccp/services/basic_info_service.py tests/integration/test_project_lifecycle.py tests/integration/test_basic_info_service.py
git commit -m "feat: implement project lifecycle and basic info services"
```

## Task 5: 量化、风险、密码产品、证据和知识库共享服务

**Agent:** Shared Services Agent  
**Depends on:** Task 3  
**Parallel:** Wave 1  

**Files:**
- Create: `mpxccp/repositories/shared_repo.py`
- Create: `mpxccp/repositories/knowledge_repo.py`
- Create: `mpxccp/services/quant_service.py`
- Create: `mpxccp/services/risk_service.py`
- Create: `mpxccp/services/product_service.py`
- Create: `mpxccp/services/evidence_service.py`
- Create: `mpxccp/services/knowledge_service.py`
- Create: `mpxccp/integration/evidence/file_store.py`
- Create: `mpxccp/integration/evidence/thumbnails.py`
- Test: `tests/integration/test_shared_services.py`
- Test: `tests/integration/test_evidence_service.py`

- [ ] **Step 1: 写量化服务测试**

```python
def test_quant_save_is_idempotent(app_services, detail_ref):
    first = app_services.quant.save("物理访问身份鉴别", detail_ref.id, d="√", a="√", k="√", ra=1, rk=1)
    second = app_services.quant.save("物理访问身份鉴别", detail_ref.id, d="√", a="√", k="√", ra=1, rk=1)
    assert first.record_id == second.record_id
    assert second.changed is False
```

- [ ] **Step 2: 实现 QuantService**

Methods:

- `load(unit_type, related_id)`
- `save(unit_type, related_id, d, a, k, ra, rk)`
- `apply_auto_rule(...)`
- `count_effective_d(project_id)`

Effective D count must follow SAVE-010 and FR-125 exactly.

- [ ] **Step 3: 实现 RiskService**

Methods:

- `final_risk_level(risk_level, mitigation_enabled, mitigated_level, mode)`
- `should_show_rectification(final_level)`
- `normalize_risk_fields(data, mode)`

- [ ] **Step 4: 写产品服务测试**

```python
def test_project_products_deduplicate_by_certificate(app_services, project):
    app_services.products.save_products(project.id, "设备登录身份鉴别", 1, [
        {"name": "产品A", "vendor": "厂商", "certificate_no": "CERT-1", "level": "二级", "usage": "身份鉴别"},
    ])
    app_services.products.save_products(project.id, "远程管理通道", 2, [
        {"name": "产品A新版", "vendor": "厂商", "certificate_no": "CERT-1", "level": "二级", "usage": "远程管理"},
    ])
    products = app_services.products.list_reusable_project_products(project.id)
    assert [item.certificate_no for item in products] == ["CERT-1"]
```

- [ ] **Step 5: 实现 ProductService**

Methods:

- `load_products(project_id, unit_type, related_id)`
- `save_products(project_id, unit_type, related_id, products)`
- `list_reusable_project_products(project_id)`
- `sync_same_certificate(project_id, source_product)`

Must keep PARENT-007 compatibility.

- [ ] **Step 6: 写证据服务测试**

```python
def test_evidence_import_copies_file_and_records_relative_name(app_services, tmp_path, project):
    source = tmp_path / "source.png"
    source.write_bytes(b"fake image")
    result = app_services.evidence.import_files(
        project_id=project.id,
        system_name="测试系统",
        unit_type="物理访问身份鉴别",
        related_id=101,
        object_name="机房A",
        files=[source],
        suffixes=["现场"],
    )
    assert result.success
    assert result.records[0].file_name.startswith("1. 物理身份鉴别_现场")
```

- [ ] **Step 7: 实现 EvidenceService 和文件适配器**

Must implement EVID-001 through EVID-012:

- Evidence root from settings.
- Sanitized path.
- Module directory mapping.
- File import with suffix.
- Thumbnail best effort.
- Delete with record removal even when disk file is missing.
- Renumber via temporary names.

- [ ] **Step 8: 实现 KnowledgeService**

Methods:

- `list_entries(type, module, show_all=False, text_filter="")`
- `add_entry(type, module, content)`
- `update_entry(id, content, module)`
- `delete_entries(ids)`
- `dedupe_append(entries)`
- `replace_all(entries)`

- [ ] **Step 9: 运行验证**

```powershell
python -m pytest tests/integration/test_shared_services.py tests/integration/test_evidence_service.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 10: 提交**

```powershell
git add mpxccp/repositories/shared_repo.py mpxccp/repositories/knowledge_repo.py mpxccp/services/quant_service.py mpxccp/services/risk_service.py mpxccp/services/product_service.py mpxccp/services/evidence_service.py mpxccp/services/knowledge_service.py mpxccp/integration/evidence tests/integration/test_shared_services.py tests/integration/test_evidence_service.py
git commit -m "feat: add shared quant product evidence and knowledge services"
```

## Task 6: UI 主窗口、资源、样式和启动行为

**Agent:** UI Shell Agent  
**Depends on:** Task 3  
**Parallel:** Wave 1  

**Files:**
- Modify: `mpxccp/bootstrap.py`
- Create: `mpxccp/ui/main_window.py`
- Create: `mpxccp/ui/styles/app.qss`
- Create: `mpxccp/integration/packaging/resource_check.py`
- Create: `mpxccp/resources/icons/.keep`
- Test: `tests/ui/test_main_window.py`
- Test: `tests/integration/test_resource_check.py`

- [ ] **Step 1: 写主窗口测试**

```python
def test_main_window_has_required_tabs(qtbot):
    from mpxccp.ui.main_window import MainWindow
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.windowTitle() == "商用密码应用安全性评估实施工具"
    assert window.tab_names() == [
        "被测系统基本信息",
        "物理和环境安全",
        "设备和计算安全",
        "网络和通信安全",
        "应用和数据安全",
        "打分",
    ]
```

- [ ] **Step 2: 实现 MainWindow 壳**

MainWindow must include:

- Menu entries from FR-003.
- Toolbar entries from IMPL-010.
- Status bar fields: project name, flow number, effective D count.
- Central tabs with stub page widgets.
- `set_project_context(project_id, system_name, flow_no)`.
- `mark_scoring_dirty()`.

- [ ] **Step 3: 实现启动行为**

`bootstrap.py` must:

- Create a single QApplication.
- Set organization and application names.
- Install combo-box wheel protection.
- Load icon and QSS.
- Return `app.exec()`.

- [ ] **Step 4: 写资源校验测试**

```python
from mpxccp.integration.packaging.resource_check import required_resources, validate_resources


def test_required_resources_are_declared():
    resources = required_resources()
    assert "styles/app.qss" in resources
    assert "icons/app.png" in resources
```

- [ ] **Step 5: 实现资源校验**

`resource_check.py` returns required icons and templates, and `validate_resources(base_path)` returns missing paths without raising.

- [ ] **Step 6: 运行验证**

```powershell
python -m pytest tests/ui/test_main_window.py tests/integration/test_resource_check.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 7: 提交**

```powershell
git add mpxccp/bootstrap.py mpxccp/ui mpxccp/integration/packaging mpxccp/resources tests/ui/test_main_window.py tests/integration/test_resource_check.py
git commit -m "feat: add desktop shell and startup resources"
```

## Task 7: 通用 UI 控件和自动保存管理器

**Agent:** UI Widgets Agent  
**Depends on:** Task 2, Task 5  
**Parallel:** Wave 1  

**Files:**
- Create: `mpxccp/ui/widgets/autosave_manager.py`
- Create: `mpxccp/ui/widgets/date_input.py`
- Create: `mpxccp/ui/widgets/quant_widget.py`
- Create: `mpxccp/ui/widgets/risk_widget.py`
- Create: `mpxccp/ui/widgets/product_list_widget.py`
- Create: `mpxccp/ui/widgets/evidence_dialog.py`
- Create: `mpxccp/ui/widgets/image_upload_widget.py`
- Create: `mpxccp/ui/widgets/knowledge_picker.py`
- Test: `tests/ui/test_quant_widget.py`
- Test: `tests/ui/test_autosave_manager.py`
- Test: `tests/ui/test_date_input.py`

- [ ] **Step 1: 写量化控件测试**

```python
def test_quant_widget_disables_a_k_when_d_is_cross(qtbot):
    from mpxccp.ui.widgets.quant_widget import QuantWidget
    widget = QuantWidget()
    qtbot.addWidget(widget)
    widget.set_d("×")
    assert widget.a_value() == "/"
    assert widget.k_value() == "/"
    assert widget.a_enabled() is False
    assert widget.k_enabled() is False
```

- [ ] **Step 2: 实现 QuantWidget**

Widget must expose:

- `set_values(d, a, k, ra, rk)`
- `values()`
- `set_d(value)`
- `a_enabled()`
- `k_enabled()`
- signal `values_changed`

- [ ] **Step 3: 写自动保存测试**

```python
def test_autosave_manager_debounces_changes(qtbot):
    from PySide6.QtWidgets import QLineEdit
    from mpxccp.ui.widgets.autosave_manager import AutoSaveManager
    editor = QLineEdit()
    qtbot.addWidget(editor)
    called = []
    manager = AutoSaveManager(editor, delay_ms=50)
    manager.save_requested.connect(lambda: called.append(True))
    editor.setText("changed")
    qtbot.wait(80)
    assert called == [True]
```

- [ ] **Step 4: 实现 AutoSaveManager**

Must recursively scan input widgets, skip invalid objects, use single-shot timer, and expose `save_now()`.

- [ ] **Step 5: 实现 DateInput**

Must support:

- Clear.
- Manual text commit.
- Popup calendar.
- Min/max date.
- Readable colors through QSS.

- [ ] **Step 6: 实现 RiskWidget、ProductListWidget、EvidenceDialog、ImageUploadWidget、KnowledgePicker**

Each widget must be thin:

- It gathers UI input.
- It exposes signals.
- It delegates persistence to services injected by parent pages.

- [ ] **Step 7: 运行验证**

```powershell
python -m pytest tests/ui/test_quant_widget.py tests/ui/test_autosave_manager.py tests/ui/test_date_input.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 8: 提交**

```powershell
git add mpxccp/ui/widgets tests/ui/test_quant_widget.py tests/ui/test_autosave_manager.py tests/ui/test_date_input.py
git commit -m "feat: add shared UI widgets and autosave manager"
```

## Task 8: 物理和环境安全模块

**Agent:** Physical Domain Agent  
**Depends on:** Task 4, Task 5, Task 7  
**Parallel:** Wave 2，与 Task 9-11 可并行  

**Files:**
- Create: `mpxccp/repositories/physical_repo.py`
- Create: `mpxccp/services/physical_service.py`
- Create: `mpxccp/ui/pages/physical_page.py`
- Test: `tests/integration/test_physical_service.py`
- Test: `tests/ui/test_physical_page.py`

- [ ] **Step 1: 写物理对象创建测试**

```python
def test_create_physical_object_creates_three_details(app_services, project):
    obj = app_services.physical.create_object(project.id, "机房A")
    details = app_services.physical.load_details(obj.id)
    assert details.auth is not None
    assert details.access_integrity is not None
    assert details.video_integrity is not None
```

- [ ] **Step 2: 实现 PhysicalRepository**

Queries:

- List objects by project and sort order.
- Create object with three detail rows.
- Load object and details.
- Delete object with detail IDs.
- Update object base fields.

- [ ] **Step 3: 实现 PhysicalService**

Methods:

- `create_object(project_id, name)`
- `list_objects(project_id)`
- `load_detail(object_id)`
- `save_detail(object_id, payload, silent)`
- `delete_object(object_id)`

`save_detail` must save object fields, three detail units, products, quant values, risk fields, and emit enough info for UI refresh.

- [ ] **Step 4: 写删除范围测试**

```python
def test_delete_physical_object_removes_quant_for_its_details_only(app_services, two_projects_with_physical):
    target, other = two_projects_with_physical
    app_services.physical.delete_object(target.object_id)
    assert app_services.quant.exists_for_related(target.auth_detail_id) is False
    assert app_services.quant.exists_for_related(other.auth_detail_id) is True
```

- [ ] **Step 5: 实现 PhysicalPage**

UI must:

- Use master-detail layout.
- Add/delete object with confirmation.
- Save current detail before switching.
- Use QuantWidget, RiskWidget, ProductListWidget, evidence buttons.
- Refresh left list name after save.

- [ ] **Step 6: 运行验证**

```powershell
python -m pytest tests/integration/test_physical_service.py tests/ui/test_physical_page.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 7: 提交**

```powershell
git add mpxccp/repositories/physical_repo.py mpxccp/services/physical_service.py mpxccp/ui/pages/physical_page.py tests/integration/test_physical_service.py tests/ui/test_physical_page.py
git commit -m "feat: implement physical security module"
```

## Task 9: 设备和计算安全模块

**Agent:** Device Domain Agent  
**Depends on:** Task 4, Task 5, Task 7  
**Parallel:** Wave 2  

**Files:**
- Create: `mpxccp/repositories/device_repo.py`
- Create: `mpxccp/services/device_service.py`
- Create: `mpxccp/ui/pages/device_page.py`
- Test: `tests/integration/test_device_service.py`
- Test: `tests/ui/test_device_page.py`

- [ ] **Step 1: 写设备对象创建测试**

```python
def test_create_device_object_creates_five_details(app_services, project):
    device = app_services.device.create_object(project.id, "服务器A")
    details = app_services.device.load_details(device.id)
    assert len(details.all_detail_ids()) == 5
```

- [ ] **Step 2: 实现 DeviceRepository**

Must support object list, create with five detail records, load, update, delete.

- [ ] **Step 3: 实现 DeviceService**

Methods:

- `create_object(project_id, name)`
- `save_detail(object_id, payload, silent)`
- `delete_object(object_id)`
- `apply_product_level_quant_rule(unit_name, product_level)`

- [ ] **Step 4: 写设备产品等级联动测试**

```python
def test_first_level_product_sets_k_fail_and_rk_1_2(app_services, project):
    result = app_services.device.apply_product_level_quant_rule("设备访问控制完整性", "一级")
    assert (result.d, result.a, result.k, result.rk) == ("√", "√", "×", 1.2)
```

- [ ] **Step 5: 实现 DevicePage**

UI must include five sections:

- 身份鉴别。
- 远程管理。
- 访问控制完整性。
- 日志完整性。
- 可执行程序完整性。

Remote management date fields must use DateInput.

- [ ] **Step 6: 运行验证**

```powershell
python -m pytest tests/integration/test_device_service.py tests/ui/test_device_page.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 7: 提交**

```powershell
git add mpxccp/repositories/device_repo.py mpxccp/services/device_service.py mpxccp/ui/pages/device_page.py tests/integration/test_device_service.py tests/ui/test_device_page.py
git commit -m "feat: implement device security module"
```

## Task 10: 网络和通信安全模块

**Agent:** Network Domain Agent  
**Depends on:** Task 4, Task 5, Task 7  
**Parallel:** Wave 2  

**Files:**
- Create: `mpxccp/repositories/network_repo.py`
- Create: `mpxccp/services/network_service.py`
- Create: `mpxccp/ui/pages/network_page.py`
- Test: `tests/integration/test_network_service.py`
- Test: `tests/ui/test_network_page.py`

- [ ] **Step 1: 写子系统同步测试**

```python
def test_network_sync_adds_new_subsystem_without_clearing_existing_channels(app_services, project):
    app_services.basic_info.sync_subsystems(project.id, ["门户"])
    app_services.network.sync_from_basic_subsystems(project.id)
    first = app_services.network.list_subsystems(project.id)[0]
    app_services.network.create_channel(first.id, "互联网访问")
    app_services.basic_info.sync_subsystems(project.id, ["门户", "管理端"])
    app_services.network.sync_from_basic_subsystems(project.id)
    assert app_services.network.channel_count(first.id) == 1
```

- [ ] **Step 2: 实现 NetworkRepository**

Must support:

- Sync network subsystems from base subsystems.
- Create channel with four detail records.
- Delete channel with quant/evidence cleanup.
- Load and save four unit details.

- [ ] **Step 3: 实现 NetworkService**

Methods:

- `sync_from_basic_subsystems(project_id)`
- `create_channel(network_subsystem_id, name)`
- `save_channel_detail(channel_id, payload, silent)`
- `delete_channel(channel_id)`

- [ ] **Step 4: 写边界完整性关联测试**

```python
def test_network_boundary_quant_and_evidence_use_boundary_detail(app_services, network_channel):
    details = app_services.network.load_details(network_channel.id)
    rule_ref = app_services.network.evidence_ref_for_boundary(details.boundary.id)
    assert rule_ref.related_id == details.boundary.id
```

- [ ] **Step 5: 实现 NetworkPage**

UI must:

- Show subsystem list and channel list.
- Save current channel detail before switching.
- Include four measurement sections.
- Keep network boundary product list absent while quant/evidence remain available.

- [ ] **Step 6: 运行验证**

```powershell
python -m pytest tests/integration/test_network_service.py tests/ui/test_network_page.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 7: 提交**

```powershell
git add mpxccp/repositories/network_repo.py mpxccp/services/network_service.py mpxccp/ui/pages/network_page.py tests/integration/test_network_service.py tests/ui/test_network_page.py
git commit -m "feat: implement network communication module"
```

## Task 11: 应用和数据安全模块

**Agent:** Application Domain Agent  
**Depends on:** Task 4, Task 5, Task 7  
**Parallel:** Wave 2  

**Files:**
- Create: `mpxccp/repositories/application_repo.py`
- Create: `mpxccp/services/application_service.py`
- Create: `mpxccp/ui/pages/application_page.py`
- Test: `tests/integration/test_application_service.py`
- Test: `tests/ui/test_application_page.py`

- [ ] **Step 1: 写应用子系统同步测试**

```python
def test_application_sync_preserves_existing_objects(app_services, project):
    app_services.basic_info.sync_subsystems(project.id, ["业务端"])
    app_services.application.sync_from_basic_subsystems(project.id)
    subsystem = app_services.application.list_subsystems(project.id)[0]
    app_services.application.create_user(subsystem.id, "管理员")
    app_services.basic_info.sync_subsystems(project.id, ["业务端", "管理端"])
    app_services.application.sync_from_basic_subsystems(project.id)
    assert app_services.application.user_count(subsystem.id) == 1
```

- [ ] **Step 2: 实现 ApplicationRepository**

Must support:

- Sync application subsystems.
- Create/delete users, access controls, important data, business actions.
- Create expected detail rows for each object.
- Load/save object detail payloads.

- [ ] **Step 3: 实现 ApplicationService**

Methods:

- `sync_from_basic_subsystems(project_id)`
- `create_user(subsystem_id, name)`
- `create_access_control(subsystem_id, name)`
- `create_important_data(subsystem_id, name, data_type)`
- `create_business_action(subsystem_id, name)`
- `save_user_detail(...)`
- `save_access_control_detail(...)`
- `save_important_data_detail(...)`
- `save_business_action_detail(...)`
- `delete_application_object(kind, id)`

- [ ] **Step 4: 写重要数据四详情测试**

```python
def test_create_important_data_creates_four_details(app_services, application_subsystem):
    data = app_services.application.create_important_data(application_subsystem.id, "交易记录", "业务数据")
    details = app_services.application.load_important_data_details(data.id)
    assert details.transport_confidentiality is not None
    assert details.storage_confidentiality is not None
    assert details.transport_integrity is not None
    assert details.storage_integrity is not None
```

- [ ] **Step 5: 实现 ApplicationPage**

UI must:

- Show four object tabs or segmented controls in the detail area.
- Keep object switching controls above detail body.
- Use complete risk mode for user auth, transport confidentiality, storage confidentiality, storage integrity, and non-repudiation.
- Use simplified risk mode for access control integrity and transport integrity.
- Support communication channel selection for transport confidentiality and transport integrity.

- [ ] **Step 6: 运行验证**

```powershell
python -m pytest tests/integration/test_application_service.py tests/ui/test_application_page.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 7: 提交**

```powershell
git add mpxccp/repositories/application_repo.py mpxccp/services/application_service.py mpxccp/ui/pages/application_page.py tests/integration/test_application_service.py tests/ui/test_application_page.py
git commit -m "feat: implement application data security module"
```

## Task 12: 评分引擎、评分页和有效 D 统计

**Agent:** Scoring Agent  
**Depends on:** Task 8, Task 9, Task 10, Task 11  
**Parallel:** Wave 3，与 Task 13-15 部分并行  

**Files:**
- Create: `mpxccp/repositories/scoring_repo.py`
- Create: `mpxccp/services/scoring_service.py`
- Create: `mpxccp/ui/pages/scoring_page.py`
- Test: `tests/integration/test_scoring_service.py`
- Test: `tests/ui/test_scoring_page.py`

- [ ] **Step 1: 写评分初始化测试**

```python
def test_scoring_initializes_41_indicators(app_services):
    app_services.scoring.ensure_indicators()
    indicators = app_services.scoring.list_indicators()
    assert len(indicators) == 41
    assert {8, 12, 17}.issubset({item.no for item in indicators if item.always_not_applicable})
```

- [ ] **Step 2: 实现 ScoringRepository**

Must support:

- Indicator upsert.
- Management score CRUD.
- Project detail traversal queries.
- Score summary upsert.
- Score detail replacement per summary.

- [ ] **Step 3: 写技术域评分测试**

```python
def test_scoring_refresh_creates_missing_empty_quant_record(app_services, project_with_physical_detail):
    detail_id = project_with_physical_detail.auth_detail_id
    assert app_services.quant.load("物理访问身份鉴别", detail_id) is None
    app_services.scoring.refresh_technical_domain(project_with_physical_detail.project_id, "物理和环境安全")
    assert app_services.quant.load("物理访问身份鉴别", detail_id) is not None
```

- [ ] **Step 4: 实现 ScoringService**

Methods:

- `ensure_indicators()`
- `refresh_technical_domain(project_id, layer)`
- `save_management_score(project_id, indicator_no, compliance)`
- `calculate_and_persist_summary(project_id)`
- `load_summary(project_id)`
- `mark_dirty(project_id)`

Must implement SCORE-001 through SCORE-017.

- [ ] **Step 5: 实现 ScoringPage**

UI must include:

- Total score card.
- Compliance count cards.
- Eight layer cards.
- Technical detail read-only tables.
- Management editable tables.
- Dirty recalculation button text exactly `⚠ 分数待更新 - 点击重新计算`.

- [ ] **Step 6: 写 UI 表格测试**

```python
def test_scoring_page_dirty_button_text(qtbot):
    from mpxccp.ui.pages.scoring_page import ScoringPage
    page = ScoringPage()
    qtbot.addWidget(page)
    page.mark_dirty()
    assert page.recalculate_button_text() == "⚠ 分数待更新 - 点击重新计算"
```

- [ ] **Step 7: 运行验证**

```powershell
python -m pytest tests/integration/test_scoring_service.py tests/ui/test_scoring_page.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 8: 提交**

```powershell
git add mpxccp/repositories/scoring_repo.py mpxccp/services/scoring_service.py mpxccp/ui/pages/scoring_page.py tests/integration/test_scoring_service.py tests/ui/test_scoring_page.py
git commit -m "feat: implement scoring engine and scoring page"
```

## Task 13: 访谈模板 Excel 导入

**Agent:** Excel Import Agent  
**Depends on:** Task 4, Task 8, Task 9, Task 10, Task 11  
**Parallel:** Wave 3  

**Files:**
- Create: `mpxccp/integration/excel/schema.py`
- Create: `mpxccp/integration/excel/import_reader.py`
- Create: `mpxccp/services/import_service.py`
- Create: `tests/fixtures/workbook_builders.py`
- Test: `tests/integration/test_excel_import.py`

- [ ] **Step 1: 写导入回滚测试**

```python
def test_import_rolls_back_on_invalid_ra(app_services, workbook_builders, project):
    workbook = workbook_builders.physical_workbook_with_invalid_ra()
    result = app_services.importer.import_interview_template(project.id, workbook, mode="替换")
    assert result.success is False
    assert "Ra" in result.message
    assert app_services.physical.list_objects(project.id) == []
```

- [ ] **Step 2: 实现 Excel schema**

`schema.py` must centralize:

- Sheet names.
- Fixed section names for application sheet.
- Column sequences for physical, device, network, application.
- Product text pattern.
- Quant column order D/A/K/Ra/Rk.

- [ ] **Step 3: 实现 ImportReader**

Must support:

- File type and 50MB size check.
- Workbook loading.
- Cell cleaning.
- Date parsing only `%Y-%m-%d` for strings.
- Product text parsing.
- Quant parsing with contextual errors.

- [ ] **Step 4: 实现 ImportService**

Methods:

- `detect_import_mode(project_id, workbook)`
- `import_interview_template(project_id, source, mode)`
- `import_system_basic_info(...)`
- `import_physical(...)`
- `import_device(...)`
- `import_network(...)`
- `import_application(...)`

Must implement IMPORT-001 through IMPORT-014 and FR-090 through FR-095.

- [ ] **Step 5: 写追加模式测试**

```python
def test_append_mode_imports_only_new_network_and_application_subsystems(app_services, workbook_builders, project):
    app_services.basic_info.sync_subsystems(project.id, ["已有子系统"])
    workbook = workbook_builders.network_application_with_existing_and_new_subsystems()
    result = app_services.importer.import_interview_template(project.id, workbook, mode="追加")
    assert result.success
    assert "追加模式：仅导入网络和应用模块的新子系统数据" in result.warnings
    assert app_services.network.has_subsystem(project.id, "新子系统")
```

- [ ] **Step 6: 运行验证**

```powershell
python -m pytest tests/integration/test_excel_import.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 7: 提交**

```powershell
git add mpxccp/integration/excel/schema.py mpxccp/integration/excel/import_reader.py mpxccp/services/import_service.py tests/fixtures/workbook_builders.py tests/integration/test_excel_import.py
git commit -m "feat: implement interview workbook import"
```

## Task 14: 全量数据、所选模块和打分表导出导入

**Agent:** Excel Export Agent  
**Depends on:** Task 12, Task 13  
**Parallel:** Wave 3  

**Files:**
- Create: `mpxccp/integration/excel/workbook_styles.py`
- Create: `mpxccp/integration/excel/export_writer.py`
- Create: `mpxccp/integration/excel/score_workbook.py`
- Create: `mpxccp/services/export_service.py`
- Test: `tests/integration/test_excel_export.py`
- Test: `tests/integration/test_score_workbook.py`

- [ ] **Step 1: 写全部数据导出结构测试**

```python
def test_export_all_data_has_expected_sheets(app_services, sample_project):
    workbook = app_services.exporter.export_all_data(sample_project.id)
    assert workbook.sheetnames == [
        "系统基本信息",
        "物理和环境安全",
        "设备和计算安全",
        "网络和通信安全",
        "应用和数据安全",
    ]
```

- [ ] **Step 2: 实现 WorkbookStyles**

Centralize:

- Title fill `4472C4`.
- Header fill `D9E2F3`.
- Not applicable fill `F2F2F2`.
- Thin borders.
- Microsoft YaHei font.
- Column widths from EXP protocols.

- [ ] **Step 3: 实现 ExportWriter**

Methods:

- `write_system_basic_info(workbook, project_id)`
- `write_physical(workbook, project_id)`
- `write_device(workbook, project_id)`
- `write_network(workbook, project_id)`
- `write_application(workbook, project_id)`

Must implement EXP-001 through EXP-007.

- [ ] **Step 4: 写打分表测试**

```python
def test_score_workbook_has_nine_sheets(app_services, sample_project):
    workbook = app_services.exporter.export_score_workbook(sample_project.id)
    assert workbook.sheetnames == [
        "整体测评",
        "1物理和环境安全",
        "2网络和通信安全",
        "3设备和计算安全",
        "4应用和数据安全",
        "5管理制度",
        "6人员管理",
        "7建设运行",
        "8应急处置",
    ]
```

- [ ] **Step 5: 实现 ScoreWorkbook**

Must implement EXP-008 through EXP-012:

- Recalculate scoring before export.
- Overall assessment sheet.
- Four technical domain sheets.
- Four management domain sheets.
- Import management score row 3, column C onward.

- [ ] **Step 6: 实现 ExportService**

Methods:

- `export_all_data(project_id)`
- `export_selected_modules(project_id, modules)`
- `export_score_workbook(project_id)`
- `import_score_workbook(project_id, source, mode)`

- [ ] **Step 7: 运行验证**

```powershell
python -m pytest tests/integration/test_excel_export.py tests/integration/test_score_workbook.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 8: 提交**

```powershell
git add mpxccp/integration/excel/workbook_styles.py mpxccp/integration/excel/export_writer.py mpxccp/integration/excel/score_workbook.py mpxccp/services/export_service.py tests/integration/test_excel_export.py tests/integration/test_score_workbook.py
git commit -m "feat: implement data and score workbook export"
```

## Task 15: 问题清单、知识库导入导出和描述模板

**Agent:** Issue Knowledge Agent  
**Depends on:** Task 5, Task 8, Task 9, Task 10, Task 11, Task 14  
**Parallel:** Wave 3  

**Files:**
- Create: `mpxccp/integration/excel/issue_workbook.py`
- Modify: `mpxccp/services/export_service.py`
- Modify: `mpxccp/services/knowledge_service.py`
- Test: `tests/unit/test_issue_templates.py`
- Test: `tests/integration/test_issue_workbook.py`
- Test: `tests/integration/test_knowledge_import_export.py`

- [ ] **Step 1: 写问题描述清洗测试**

```python
from mpxccp.domain.issue_templates import clean_other_prefix, join_multi_select


def test_issue_description_cleans_other_prefix_and_multi_select():
    assert clean_other_prefix("其他:短信令牌") == "短信令牌"
    assert join_multi_select("指纹,其他:门禁卡") == "指纹、门禁卡"
```

- [ ] **Step 2: 实现问题模板工具函数**

Functions:

- `clean_other_prefix(value)`
- `join_multi_select(value)`
- `describe_product(products)`
- `append_first_level_product_note(products)`
- `effective_issue_risk(detail_risk_fields)`

- [ ] **Step 3: 写问题清单 workbook 测试**

```python
def test_issue_workbook_has_fixed_title_and_headers(app_services, sample_project):
    workbook = app_services.exporter.export_issue_workbook(sample_project.id)
    sheet = workbook["问题清单"]
    assert sheet["A1"].value.startswith("【三级标准】")
    assert [sheet.cell(2, col).value for col in range(1, 13)] == [
        "测评层面", "测评要求", "问题编号", "系统名称", "被测对象名称", "现状描述",
        "问题说明", "风险分析与缓释机制", "风险等级", "整改建议", "说明", "主要责任部门（建议）",
    ]
```

- [ ] **Step 4: 实现 IssueWorkbook**

Must implement EXP-013 through EXP-017:

- Fixed sheet name and title.
- 12 fixed headers.
- Risk colors.
- Continuous merge only.
- Technical domain handlers for physical, network, device, application.
- No management domain issues.

- [ ] **Step 5: 实现知识库导入导出**

`KnowledgeService` and `ExportService` must implement:

- Knowledge workbook export headers: ID、类型、模块、内容、创建时间、更新时间。
- Replace import.
- Append import with dedupe by type/module/content.

- [ ] **Step 6: 运行验证**

```powershell
python -m pytest tests/unit/test_issue_templates.py tests/integration/test_issue_workbook.py tests/integration/test_knowledge_import_export.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 7: 提交**

```powershell
git add mpxccp/domain/issue_templates.py mpxccp/integration/excel/issue_workbook.py mpxccp/services/export_service.py mpxccp/services/knowledge_service.py tests/unit/test_issue_templates.py tests/integration/test_issue_workbook.py tests/integration/test_knowledge_import_export.py
git commit -m "feat: implement issue list and knowledge workbook flows"
```

## Task 16: 数据治理、兼容迁移和关联完整性检查

**Agent:** Data Governance Agent  
**Depends on:** Task 12, Task 15  
**Parallel:** Wave 4 串行为主  

**Files:**
- Create: `mpxccp/services/integrity_service.py`
- Modify: `mpxccp/services/migration_service.py`
- Test: `tests/integration/test_integrity_service.py`
- Test: `tests/integration/test_migrations.py`

- [ ] **Step 1: 写完整性检查测试**

```python
def test_integrity_report_detects_orphan_quant_without_modifying_data(app_services, project, orphan_quant):
    report = app_services.integrity.check_project(project.id)
    assert any(item.kind == "orphan_quant" for item in report.items)
    assert app_services.quant.record_exists(orphan_quant.id)
```

- [ ] **Step 2: 实现项目范围解析**

`IntegrityService.resolve_project_scope(project_id)` returns:

- Detail references grouped by unit type.
- Quant references.
- Evidence references.
- Product references.
- Compatible outer object references for products.

- [ ] **Step 3: 实现只读完整性报告**

Detect:

- Empty association.
- Unknown unit type.
- Orphan quant/evidence/product references.
- Cross-project references.
- Product references not covered by detail or compatible outer object.

No automatic mutation is allowed.

- [ ] **Step 4: 写迁移幂等测试**

```python
def test_migrations_are_idempotent(app_services):
    app_services.migrations.run_all()
    app_services.migrations.run_all()
    assert app_services.scoring.count_indicators() == 41
```

- [ ] **Step 5: 固化迁移服务**

Ensure migrations:

- Add missing indicators.
- Clean old enum display strings safely.
- Preserve business data.
- Log warnings instead of blocking old DB open when a noncritical cleanup fails.

- [ ] **Step 6: 运行验证**

```powershell
python -m pytest tests/integration/test_integrity_service.py tests/integration/test_migrations.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 7: 提交**

```powershell
git add mpxccp/services/integrity_service.py mpxccp/services/migration_service.py tests/integration/test_integrity_service.py tests/integration/test_migrations.py
git commit -m "feat: add data governance and integrity diagnostics"
```

## Task 17: 安装包、资源校验和运行支撑

**Agent:** Packaging Agent  
**Depends on:** Task 6, Task 16  
**Parallel:** Wave 4  

**Files:**
- Create: `scripts/build_windows.ps1`
- Create: `scripts/check_resources.ps1`
- Create: `mpxccp/resources/icons/app.png`
- Create: `mpxccp/resources/templates/.keep`
- Modify: `README.md`
- Test: `tests/integration/test_runtime_paths.py`

- [ ] **Step 1: 写运行路径测试**

```python
from mpxccp.config.paths import resolve_user_data_path


def test_user_data_path_is_not_install_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData"))
    path = resolve_user_data_path("mpxccp.sqlite3")
    assert "AppData" in str(path)
    assert path.name == "mpxccp.sqlite3"
```

- [ ] **Step 2: 实现资源完整性检查脚本**

`scripts/check_resources.ps1` must run the Python resource check and fail if required resources are missing:

```powershell
python -m mpxccp.integration.packaging.resource_check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

- [ ] **Step 3: 实现 Windows build script**

`scripts/build_windows.ps1` must:

- Run tests.
- Run resource check.
- Call PyInstaller with app name.
- Include resources and styles.

- [ ] **Step 4: 更新 README**

README must document:

- Install dependencies.
- Run app.
- Run tests.
- Build installer/executable.
- Local data path.
- Evidence root behavior.

- [ ] **Step 5: 运行验证**

```powershell
python -m pytest tests/integration/test_runtime_paths.py -q
powershell -ExecutionPolicy Bypass -File scripts/check_resources.ps1
```

Expected:

```text
all tests passed
resource check passed
```

- [ ] **Step 6: 提交**

```powershell
git add scripts mpxccp/resources README.md tests/integration/test_runtime_paths.py
git commit -m "chore: add Windows packaging and resource checks"
```

## Task 18: 端到端验收、基线夹具和发布前回归

**Agent:** QA Integration Agent  
**Depends on:** Task 17  
**Parallel:** 否  

**Files:**
- Create: `tests/integration/test_end_to_end_workflow.py`
- Create: `tests/fixtures/sample_data.py`
- Create: `docs/验收清单.md`
- Modify: `README.md`

- [ ] **Step 1: 创建端到端样例数据**

`sample_data.py` must create:

- One project with flow number and system name.
- Two subsystems.
- One object in each technical domain.
- One product with certificate and one product without certificate.
- Quant values that produce at least one 符合、部分符合、不符合、不适用.
- Management scores across all four management layers.

- [ ] **Step 2: 写端到端测试**

```python
def test_core_end_to_end_workflow(app_services, sample_data, tmp_path):
    project_id = sample_data.create_full_project()
    app_services.scoring.calculate_and_persist_summary(project_id)
    score_book = app_services.exporter.export_score_workbook(project_id)
    issue_book = app_services.exporter.export_issue_workbook(project_id)
    all_data = app_services.exporter.export_all_data(project_id)
    assert "整体测评" in score_book.sheetnames
    assert "问题清单" in issue_book.sheetnames
    assert "系统基本信息" in all_data.sheetnames
    app_services.project.soft_delete(project_id)
    app_services.project.restore([project_id])
    assert app_services.project.open_project(project_id).id == project_id
```

- [ ] **Step 3: 写手工验收清单**

`docs/验收清单.md` must include the FR-161 flow:

1. 新建项目并保存基本信息。
2. 添加子系统并同步网络、应用页。
3. 添加四类技术域对象并保存详情。
4. 添加密码产品并从项目内批量导入复用。
5. 提交证据图片、删除证据并检查重新编号。
6. 填写量化评估和管理域评分，刷新评分页。
7. 导入访谈模板，导出全部数据。
8. 导出打分表并再次导入管理域评分。
9. 导出问题清单。
10. 软删除项目并恢复。

- [ ] **Step 4: 运行全量回归**

```powershell
python -m pytest -q
python -m ruff check .
```

Expected:

```text
all tests passed
All checks passed
```

- [ ] **Step 5: 执行手工验收并记录结果**

Run the app:

```powershell
python -m mpxccp.main
```

Record pass/fail notes in `docs/验收清单.md` under each checklist item.

- [ ] **Step 6: 提交**

```powershell
git add tests/integration/test_end_to_end_workflow.py tests/fixtures/sample_data.py docs/验收清单.md README.md
git commit -m "test: add end-to-end acceptance baseline"
```

## Integration Review Checklist

Run after each Wave:

- [ ] `python -m pytest -q` passes or failures are isolated to the current Wave and documented.
- [ ] No UI page writes directly to the database session.
- [ ] Read-only load methods do not commit, rollback, create, or delete data.
- [ ] Quant and evidence use detail references.
- [ ] Product range parsing still accepts compatible outer object references.
- [ ] Scoring refresh is the only read-looking path allowed to create empty quant records.
- [ ] Excel schema constants remain centralized in `mpxccp/integration/excel/schema.py`.
- [ ] Evidence file operations never store absolute paths in `EvidenceImage`.
- [ ] Soft delete does not delete business data.
- [ ] Hard delete does not delete disk evidence files.

## Final Verification Commands

Run at the end of implementation:

```powershell
python -m pytest -q
python -m ruff check .
powershell -ExecutionPolicy Bypass -File scripts/check_resources.ps1
```

Expected:

```text
all tests passed
All checks passed
resource check passed
```

## Spec Coverage Map

| Requirement Area | Plan Tasks |
| --- | --- |
| 应用启动、主窗口、资源、样式 | Task 1, Task 6, Task 17 |
| 项目生命周期、软删除、恢复、硬删除 | Task 4, Task 16 |
| 基本信息、子系统、密码应用情况 | Task 4 |
| 通用详情、自动保存、量化、风险、产品、证据 | Task 5, Task 7 |
| 物理和环境安全 | Task 8 |
| 设备和计算安全 | Task 9 |
| 网络和通信安全 | Task 10 |
| 应用和数据安全 | Task 11 |
| 评分、管理域、有效 D 统计 | Task 12 |
| 访谈模板导入 | Task 13 |
| 全量数据导出、所选模块导出、打分表导入导出 | Task 14 |
| 问题清单、知识库导入导出 | Task 15 |
| 数据迁移、项目范围解析、关联完整性检查 | Task 16 |
| 安装运行和自动化验收 | Task 17, Task 18 |
