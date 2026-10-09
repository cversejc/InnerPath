# report.simple AI 协议第一阶段设计

> 基线：`辰鉴 report.simple 工作流重构与代码修改任务书 v1.0`
> 工作区：`C:\Users\21815\Desktop\my_work\chen_jian\sign_up\InnerPath`
> 分支：`codex/simple-ai-protocol`
> 说明：本文件记录第一阶段（后端协议基座）的实现与验收结果。AI 协议只做灰度开发，默认仍走 `legacy_manual`，线上行为不变。

## 一、已对齐的 12 项决策

| 编号 | 决策 | 结论 |
| --- | --- | --- |
| 1 | AI Simple 是否继续使用 `report.simple` | 继续使用同一 key，通过冻结定义中的 `simple_protocol` 分流；历史案件无标记 = `legacy_manual` |
| 2 | AI 协议何时成为新申请默认 | 前三个阶段只开发与灰度，不默认切换；全链路验证后再放开 |
| 3 | AI 首次生成启动时点 | **咨询师接单或管理员分配之后**，案件创建时只准备执行记录，不调用模型 |
| 4 | 是否新增执行/修订/审核三张表并复用 `SkillRun` | 同意；`SimpleReportVersion` 保持冻结只做历史读取 |
| 5 | 节点内容形态 | 统一 `content + structured_content + source_revision_refs`；S1–S4 结构化优先，S5 全文优先，S6 只存质量与交付数据 |
| 6 | Simple 专用 Skill | 复用现有 Skills 与运行时，按节点做最小适配；S1 排盘原始结果只读 |
| 7 | 状态映射与重试 | `auto_retry_limit = 2`，AI 生成中 `GENERATING`，成功 `IN_REVIEW`，失败 `FAILED`，并有明确人工重试入口 |
| 8 | 管理员权限 | 管理员可查看、改派、重开；终审默认由负责人完成，代审需独立审计标识 |
| 9 | S6 质量门禁 | 只有程序化硬规则与依赖效验可硬阻断；AI Validator 的 `BLOCK` 不单独放行或阻断 |
| 10 | 上游重开后的下游处理 | 保守策略：所有实际引用旧确认修订的下游确认稿标记为待复核 |
| 11 | 正式交付模型 | 先独立 Simple 交付快照，并继续生成 legacy `Report`，不修改标准 `ReportVersion` 非空约束 |
| 12 | 灰度与测试 | 前三阶段只开发与灰度；旧测试保留为 legacy 套件，真实 LLM 联调单独专项测试 |

## 二、第一阶段范围

第一阶段只做“协议与版本管理基座”，完成：

1. 新旧 Simple 执行协议分流。
2. 新版 AI 辅助流程定义的发布与案件冻结。
3. Simple 内部执行状态、不可变修订、审核决策三张新表。
4. 服务端版本分配、幂等、并发锁与过期结果拒绝。
5. 节点重开与上游失效标记基础。
6. 新增迁移、回滚评估和第一阶段测试。

第一阶段不做：S1–S5 的 Prompt/输出 Schema 业务实现、S6 完整质量检查、正式交付结构、前端审阅工作台、真实模型联调。

## 三、协议分流与版本冻结

### 3.1 协议标识

沿用 `report.simple` key，在冻结的 `WorkflowVersion.definition_json` 中写入：

```json
{
  "simple_protocol": "ai_assisted",
  "protocol_version": 1,
  "steps": []
}
```

读取规则：

- `definition_json.simple_protocol == "ai_assisted"` → 新版 AI 协议。
- 其他值或缺失 → `legacy_manual`。
- 非法值 → 直接报错，不静默回退。

案件创建时再把这个协议复制到 `ReportCase.application_snapshot.simple_protocol`，并始终以快照为准判断该案件如何执行。运行时不按最新代码定义推断历史案件。

### 3.2 版本发布

`ensure_simple_workflow_version()` 需要变成协议感知：

1. 接收 `protocol` 参数（`legacy_manual` 或 `ai_assisted`）。
2. 在 `latest_published_version` 基础上按 `definition_json.simple_protocol` 过滤。
3. 只有“同协议且定义内容相同”才复用旧版本；否则发布新的递增版本。
4. 旧定义保持字节级稳定，避免为已冻结版本制造无关的新 legacy 版本。

AI 协议灰度期间，案件仅在显式选择或开关打开时才绑定 `ai_assisted` 版本；默认仍走 legacy，直到前端与端到端验证完成。

### 3.3 启动时点

- 案件创建：只冻结协议、建立 `StepTask`，S1 仍为 `READY`，但不因为创建而启动 AI。
- 咨询师接单：写入负责人、为该案件当前节点入队 `workflow.step.ready`。
- 管理员分配：写入负责人、为当前未完成节点入队 `workflow.step.ready`。
- `workflow.step.ready` 消费时，若是 AI 协议且负责人已存在，才创建 `SkillRun` 并调用模型。
- 已完成/已交付/已取消案件不重复触发。

## 四、数据模型与迁移

### 4.1 新增三张表

**`simple_step_executions`**：每个案件的每个业务节点一行。

```text
id
report_case_id
step_task_id
step_key
execution_status        READY | GENERATING | IN_REVIEW | REVISING | FAILED | COMPLETED
dependency_status       CURRENT | STALE
activation_no
current_revision_id
confirmed_revision_id
active_skill_run_id
input_snapshot
input_fingerprint
stale_reason
created_at
updated_at
```

**`simple_step_revisions`**：不可变内容修订。

```text
id
execution_id
revision_no
revision_type           INITIAL | AI_REVISION | REGENERATE | MANUAL_EDIT
parent_revision_id
content
structured_content
source_revision_refs
skill_run_id
created_by
idempotency_key
created_at
```

**`simple_review_decisions`**：不可变人工审核记录。

```text
id
execution_id
target_revision_id
decision                APPROVE | REQUEST_REVISION | REGENERATE | MANUAL_EDIT | REOPEN
feedback_text
reviewer_id
review_mode             OWNER | ADMIN | DELEGATED
operator_id             实际执行审核的账号
on_behalf_of_user_id    被代理的负责人
idempotency_key
created_at
```

代审规则：`review_mode = OWNER` 时 `on_behalf_of_user_id` 必须为空，`reviewer_id` 为负责人本人；管理员或代审时 `on_behalf_of_user_id` 必须显式给出，`operator_id` 记录真实操作账号，`reviewer_id` 与二者分离，保证审计链可追溯。该约束由迁移中的 `ck_simple_review_decision_delegation_identity` 与服务层双重校验。

### 4.2 关键约束

- `(report_case_id, step_key)` 唯一：一个业务节点只有一个执行实例。
- `(execution_id, revision_no)` 唯一：修订序号由服务端分配。
- `(execution_id, idempotency_key)` 唯一：重复请求返回同一结果。
- `current_revision_id`、`confirmed_revision_id` 不加外键，由服务层保证与执行实例同属一条链，避免与修订表形成循环外键。
- 修订记录与审核记录在 ORM 事件和 PostgreSQL 触发器两层禁止更新、删除。
- `source_revision_refs` 记录实际引用的上游确认修订 ID，不随后续上游变化而改写。

### 4.3 迁移与回滚

- 迁移：`backend/alembic/versions/026_simple_ai_protocol.py`，`down_revision = "025_merge_simple_review"`。
- 只新增表、索引、约束与不可变触发器，不改动旧表列与旧 `SimpleReportVersion` 数据。
- 回滚只删除新增表与触发器，不影响 legacy 案件与旧版本读取。

验证结果：

- SQLite：以 `025_merge_simple_review` 为基线执行 `upgrade head` 与 `downgrade 025_merge_simple_review`，三张新表、索引、唯一约束与检查约束均可正确创建与回收。
- PostgreSQL 15（本地容器实例，独立临时库）：`026` 升降级通过；`trg_simple_step_revisions_immutable`、`trg_simple_review_decisions_immutable` 与函数 `prevent_simple_ai_record_mutation()` 均正确创建；对修订表与审核表的 `UPDATE`/`DELETE` 全部被触发器以 `simple_ai_record_immutable` 拒绝（4/4 拦截），`simple_step_executions` 仍可正常更新；回滚后表、触发器与函数全部清理干净。
- 注意：本仓库早期迁移（`001` 起）直接使用 PostgreSQL `JSONB`，SQLite 全链路 `upgrade head` 本就不受支持；上述 SQLite 验证是在 `025` 基线上单独校验 `026` 的升降级。

## 五、工作流状态转换表

### 5.1 `StepTask` 与执行状态映射

| Simple 执行状态 | `StepTask.status` | 说明 |
| --- | --- | --- |
| `READY` | `READY` | 已激活，等待负责人触发 |
| `GENERATING` | `EXECUTING` | 首次生成运行中 |
| `REVISING` | `EXECUTING` | 反馈修订或整体重生成运行中 |
| `IN_REVIEW` | `IN_REVIEW` | 已有修订，等待咨询师审核 |
| `FAILED` | `READY` | 运行失败，保留错误信息等待重试 |
| `COMPLETED` | `COMPLETED` | 已确认修订并完成节点 |

### 5.2 允许的状态转换

| 操作 | 前置状态 | 后置状态 | 说明 |
| --- | --- | --- | --- |
| 首次生成 | `READY` | `GENERATING` | 必须已有负责人且 `dependency_status = CURRENT` |
| 生成成功 | `GENERATING` | `IN_REVIEW` | 写入新修订，`current_revision_id` 指向该修订 |
| 生成失败 | `GENERATING` / `REVISING` | `FAILED` | 记录 `last_error`，不清除输入快照 |
| 反馈修订 | `IN_REVIEW` | `REVISING` | 记录 `REQUEST_REVISION` 决策与基准修订 |
| 整体重生成 | `IN_REVIEW` | `REVISING` | 记录 `REGENERATE` 决策与基准修订 |
| 人工编辑 | `IN_REVIEW` | `IN_REVIEW` | 直接追加 `MANUAL_EDIT` 修订 |
| 审核通过 | `IN_REVIEW` | `COMPLETED` | 只允许确认当前 `current_revision_id` |
| 失败重试 | `FAILED` | `GENERATING` / `REVISING` | 沿用原基准修订与输入指纹 |
| 重开已完成节点 | `COMPLETED` | `READY` | 递增 `activation_no`，下游标记 `STALE` |

### 5.3 非法操作必须拒绝

- 生成中重复生成或重复审核。
- 未生成内容直接审核通过。
- 非当前负责人审核或编辑。
- 使用过期 `activation_no`、过期修订基准或过期输入指纹提交结果。
- 上游依赖已经失效仍继续推进。
- 使用旧修订覆盖较新的已确认版本。

### 5.4 重开与依赖失效

初期采用保守策略：

1. 重开目标节点后，删除其 `confirmed_revision_id`，生成新的修订基线。
2. 下游 `StepTask` 重置为 `PENDING`，对应执行记录标记 `dependency_status = STALE` 并写入 `stale_reason`。
3. 只标记“实际引用了旧确认修订”的下游；未引用旧版本的节点保持 `CURRENT`。
4. 上游依赖恢复有效前，禁止 S6 交付与该分支继续推进。

### 5.5 自动重试语义

- 定义中每个 AI 节点冻结 `auto_retry_limit = 2`：首次执行失败后最多自动重试两次，合计最多三次运行。
- 自动重试沿用同一 `base_revision_id` 与 `input_fingerprint`，不重复创建人工操作记录。
- 自动重试额度耗尽后执行状态保持 `FAILED`，错误信息留在 `StepTask` 上，等待负责人或管理员人工重试。
- 人工重试不受 `auto_retry_limit` 限制，但每次重试都必须通过负责人、激活号、修订基准与输入指纹校验；替换或改派负责人时，旧负责人的进行中运行会被归档，不能继续写回修订。

## 六、API 契约

沿用 `/report-cases/{id}/simple` 前缀，旧接口保持兼容。第一阶段接口：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/report-cases/{id}/simple/steps/{step}` | 查询执行状态、当前修订与异常 |
| `POST` | `/report-cases/{id}/simple/steps/{step}/generate` | 启动首次生成（幂等） |
| `POST` | `/report-cases/{id}/simple/steps/{step}/revise` | 基于指定修订提交自然语言反馈 |
| `POST` | `/report-cases/{id}/simple/steps/{step}/regenerate` | 基于指定修订整体重生成 |
| `POST` | `/report-cases/{id}/simple/steps/{step}/manual-edit` | 保存人工修订，生成新版本 |
| `POST` | `/report-cases/{id}/simple/steps/{step}/approve` | 确认当前修订并完成节点 |
| `GET` | `/report-cases/{id}/simple/steps/{step}/revisions` | 查询不可变修订历史 |
| `POST` | `/report-cases/{id}/simple/steps/{step}/reopen` | 重开已完成节点 |
| `GET` | `/report-cases/{id}/simple/quality` | 查询 S6 质量检查结果 |
| `POST` | `/report-cases/{id}/simple/finalize` | 终审与交付 |

统一要求：

- 操作人授权：负责人或管理员；管理员代审需独立审计字段。
- 状态校验：所有写操作校验 `execution_status` 与 `StepTask.status`。
- 基准修订：修订类操作必须携带 `base_revision_id`。
- 并发与幂等：`Idempotency-Key` 或请求体 `idempotency_key`，重复请求返回同一结果。
- 过期拒绝：`activation_no`、`input_fingerprint`、当前负责人、`current_revision_id` 任一不匹配则拒绝写入。
- 旧接口 `POST .../steps/{step}/complete` 仅服务 legacy 协议；AI 协议调用时返回明确错误码，不隐式兼容。

第一阶段兼容与保护：

- AI 协议案件调用 legacy `POST .../simple/steps/{step}/complete` 返回 `409 simple_ai_protocol_required`，legacy 案件调用 AI 专用接口同样被拒绝。
- AI 协议的 legacy 交付路径（`backend/app/application/report_delivery.py` 中的 Simple 分支）统一经 `ensure_legacy_simple_protocol()` 拦截，避免绕过新协议直接走旧交付。
- `POST .../simple/finalize` 已占位但返回 `501 simple_finalize_not_implemented`，第一阶段的终审交付仍由 legacy final gate 负责，第三阶段再接入独立 Simple 交付快照。
- 六个 AI 节点复用现有生产 Skill，不新增 Simple 专用 key：S1 `report.s1_foundation_analysis`、S2 `report.s2_psychology_mapping`、S3 `report.s3_integration`、S4 `report.s4_mechanism_block_action`、S5 `report.fragment_authoring`、S6 `report.final_validator`；S1 排盘原始结果只读。

## 七、文件改动清单

### 已完成（未提交）

| 文件 | 改动性质 |
| --- | --- |
| `backend/alembic/env.py` | 小范围扩展：导入新模型 |
| `backend/alembic/versions/026_simple_ai_protocol.py` | 新增：三张新表、索引、约束与 PostgreSQL 不可变触发器 |
| `backend/app/application/simple_ai_workflow.py` | 新增：执行服务（生成、修订、人工编辑、审核、重开、幂等与过期拒绝） |
| `backend/app/application/report_cases.py` | 小范围扩展：协议感知的版本发布与案件冻结 |
| `backend/app/application/report_delivery.py` | 小范围扩展：legacy Simple 交付路径的协议守卫 |
| `backend/app/application/report_case_info.py` | 小范围扩展：补充信息与追加说明的 legacy 守卫 |
| `backend/app/application/skill_runtime.py` | 小范围扩展：AI 节点运行完成后的 Simple 续跑 |
| `backend/app/domains/workflow/simple_definitions.py` | 小范围扩展：协议常量、AI 定义、协议读取与 legacy 守卫 |
| `backend/app/domains/workflow/service.py` | 小范围扩展：案件创建时写入 `simple_protocol` 快照 |
| `backend/app/domains/delivery/simple_models.py` | 新增：执行、修订、审核三模型与不可变 ORM 事件 |
| `backend/app/domains/delivery/simple_schemas.py` | 新增：执行状态、修订、审核请求/响应契约 |
| `backend/app/domains/skills/bindings.py` | 小范围扩展：按协议冻结所需 Skill 集合，标准流程仍绑七个 |
| `backend/app/domains/service_requests/payloads.py`、`schemas.py` | 小范围扩展：申请 payload 透传并锁定 `simple_protocol` |
| `backend/app/domains/service_requests/staff.py` | 小范围扩展：接单后触发当前节点 ready |
| `backend/app/tasks/workflow_tasks.py` | 小范围扩展：`workflow.step.ready` 的 AI 分支与运行续跑 |
| `backend/app/api/v1/report_cases.py` | 小范围扩展：第一阶段 Simple 接口与 legacy `complete` 保护 |
| `backend/app/api/v1/service_request_admin_routes.py`、`backend/app/api/v1/service_request_api_support.py` | 小范围扩展：管理员分配后触发当前节点 ready |
| `backend/tests/test_simple_report_workflow.py` | 测试夹具扩展：加入新表；legacy 断言保留 |
| `backend/tests/test_simple_ai_protocol.py` | 新增：第一阶段后端测试（8 例） |
| `docs/implementation/simple-ai协议第一阶段设计.md` | 新增：本设计文档 |

旧版 Simple 的执行与交付路径没有删除或改写；上表“小范围扩展”均为在既有分支上增加协议判断，legacy 分支行为保持不变。

## 八、历史兼容方案

1. 旧 `SimpleReportVersion` 表、固定 `v1.0–v6.0`、旧 `complete` 接口与旧交付路径全部保留。
2. 无协议标记的历史案件、进行中案件一律按 `legacy_manual` 执行，不自动迁移。
3. 同一 `report.simple` key 下允许多个已发布版本并存，案件只认冻结版本与快照协议。
4. 新版接口只在 AI 协议案件上开放；旧工作台在新协议灰度期间不受影响。
5. 回滚只删除新增表与触发器，不触碰 legacy 数据。

## 九、第一阶段测试结果

### 9.1 新增测试

`backend/tests/test_simple_ai_protocol.py`（8 例，全部通过）：

1. `test_ai_case_waits_for_acceptance_and_starts_on_ready_event`：案件创建不生成；接单后 `workflow.step.ready` 才创建 `SkillRun`，并覆盖初始执行记录。
2. `test_ai_revision_manual_edit_and_approval_are_immutable`：AI 修订、人工编辑、审核通过与审核决策不可变。
3. `test_generation_idempotency_and_command_conflicts`：幂等启动返回同一运行，生成中重复命令被拒绝。
4. `test_stale_activation_base_owner_and_fingerprint_are_rejected`：过期激活号、过期基准修订、非当前负责人、过期输入指纹全部拒绝。
5. `test_automatic_retry_stops_after_two_retries_then_manual_retry`：自动重试两次后停在 `FAILED`，人工重试仍可用。
6. `test_reassignment_archives_the_previous_owners_run`：改派后旧负责人的进行中运行被归档。
7. `test_legacy_complete_and_unimplemented_finalize_are_guarded`：AI 案件调用 legacy `complete` 返回 `409`，`finalize` 返回 `501`。
8. `test_reopen_invalidates_only_downstream_revisions_that_reference_it`：重开只失效实际引用旧确认稿的下游，未引用节点保持 `CURRENT`。

`backend/tests/test_simple_report_workflow.py` 保留全部 legacy 断言，并扩展夹具以创建三张新表；其中协议发布用例覆盖“旧案件无标记 → `legacy_manual`、AI 案件冻结 `ai_assisted`”。

### 9.2 回归结果

- `py -3.11 -m pytest tests/test_simple_ai_protocol.py -q` → `8 passed`。
- `py -3.11 -m pytest tests -q` → `481 passed, 27 warnings`。
- `py -3.11 -m compileall -q app` → 通过。
- `git diff --check` → 无空白错误（仅 Git 的 LF/CRLF 提示）。
- 迁移升降级：SQLite 与 PostgreSQL 15 均按 4.3 的结论验证通过。

修订不可变的双层保护中，ORM 事件在 SQLite 测试夹具内生效，PostgreSQL 触发器在责任环境另有专项验证；标准流程与 legacy Simple 无回归。

前端第一阶段不做新工作台。旧版 Simple 工作台继续可用；AI 协议默认不启用，前端改造从第二阶段开始。

## 十、技术风险与待确认

1. **Skill 适配粒度**：决策 6 已确认复用六个现有 Skill，不再新增 Simple 专用 key。每个节点的输入裁剪与 Prompt 适配在第二阶段随节点实现一起落地，届时需按节点确认输入契约与输出 Schema。
2. **默认协议开关**：第一阶段默认仍为 legacy；AI 协议何时默认启用，按决策 2 等前三阶段验证后决定，当前没有前端入口，只能由显式 `simple_protocol` 字段创建 AI 案件。
3. **S6 与质量门禁**：第一阶段的 `quality_state` 只提供查询，`BLOCK` 不硬阻断也不自动放行；硬阻断项清单在第三阶段实现前单独确认。
4. **终审与交付**：`finalize` 目前返回 `501`，终审仍走 legacy final gate；独立 Simple 交付快照与旧 `Report` 的并行生成在第三阶段落地。
5. **时柱争议**：第一阶段不引入定盘服务，案件存在时柱争议时只提示服务范围限制；是否阻断创建留到第二阶段确认。
6. **真实模型联调**：第一阶段测试全部使用桩运行，未调用真实 LLM；真实联调按决策 12 单独作为专项测试推进。

## 十一、第一阶段状态与下一步

第一阶段（后端协议基座）已完成：协议分流与版本冻结、三张新表与迁移、执行/修订/审核状态机、幂等与过期拒绝、重开与依赖失效、六个 Skill 绑定、自动重试、legacy 保护、接口与测试全部落地并通过回归。改动仍在工作区未提交，默认不切换线上行为。

下一阶段（业务节点实现）按任务书推进，顺序建议：

1. 逐节点确认 S1–S5 的输入契约、Prompt 与结构化输出 Schema，并把适配规则写入冻结定义。
2. 实现 S6 质量检查规则与 `quality_state` 明细，明确第一阶段只提示、不阻断的边界。
3. 补充前端审阅工作台（节点状态、修订对比、反馈修订、人工编辑、审核与重开）。
4. 在独立开关下做端到端灰度，先内部账号验证，再决定是否默认切换到 `ai_assisted`。
