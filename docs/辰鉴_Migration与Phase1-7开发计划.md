# 辰鉴 Migration 与 Phase 1–7 开发计划

> 依据：[现有代码与目标架构差距分析](现有代码与目标架构差距分析.md) 和《辰鉴 AI 内容生产工作流与 Skills 架构设计 v1.0》第 64、65、71–79 节。  
> 当前 Alembic Head：`009`。本文件是实施计划；没有执行数据库迁移或应用代码改造。

## 1. 实施原则

- 使用 Expand → Cutover → Contract：先增加兼容结构，再按入口切流，最后在确认无读写依赖后另行评估旧结构退役。
- Alembic `001`–`009` 保持不变；目标结构从新迁移开始。迁移按依赖拆分，发布的 WorkflowVersion、SkillVersion 和 ReportVersion 以追加方式演进。
- 目标文档的 14 张表是报告生产工作流的核心表，不是 InnerPath 整个数据库最终只能有 14 张表。账户、认证、审计、日历和仍在使用的服务申请表继续存在；兼容期表数会增加。
- 不默认回填所有旧报告的 Finding、Fragment 或 QA 数据。旧报告继续通过 `reports` 提供读取兼容；新流水线产生的交付进入 `report_versions`。
- 兼容期不对同一业务操作双写两套工作流状态。新旧请求按创建时间/入口明确归属一套流程；旧流程中的活跃任务先完成或按显式规则迁移。
- 当前文档建议报告 Case 记录来源于 `service_requests` 或 `report_tasks`。目标表定义没有来源 FK；实施前应确定来源关联方案。优先考虑在 `report_cases` 增加两个具体、可空的来源列及互斥约束，不引入多态 `origin_type/id`。如坚持目标字段冻结，则将来源放入 `application_snapshot` 并接受没有数据库 FK 的取舍。

## 2. Alembic Migration 计划

迁移文件名仅为建议，最终 revision ID 由 Alembic 生成。每批先在空库和从 `009` 升级的副本上验证，再部署到共享环境。

| 建议迁移 | 所属阶段 | 新增表 | 重点约束与说明 |
|---|---:|---|---|
| `010_report_workflow_foundation` | 1 | `report_cases`、`workflow_versions`、`workflow_instances`、`step_tasks`、`workflow_outbox` | Workflow key/version 唯一；Step key 在 Instance 内唯一；Outbox 有待投递/重试索引。`report_cases.workflow_instance_id` 与 `workflow_instances.report_case_id` 存在循环关联，先建 Case 和 Instance 表，再以 `ALTER TABLE` 增加 Case 到当前 Instance 的 FK。若保留旧入口来源 FK，在本迁移中一起增加并用 CHECK 限制最多一个来源。 |
| `011_skill_runtime` | 2 | `ai_skill_versions`、`skill_runs` | Skill key/version 唯一；SkillRun 的幂等键唯一；Run 固定引用一个 SkillVersion。 |
| `012_case_semantic_assets` | 3 | `case_evidence_items`、`finding_revisions`、`content_fragment_revisions` | Case、StepTask、SkillRun 外键；Case/Key/Revision 唯一；用部分唯一索引保证每个 Finding/Fragment 仅一个 current revision。NarrativePlan 尚未创建，Fragment 的 NarrativePlan 关联列/FK 在 `013` 建立。 |
| `013_narrative_plans` | 5 | `narrative_plans` | Case/Version 唯一；current plan 的唯一约束；引用已存在的 Case 和 SkillRun，并补上 Fragment 到 NarrativePlan 的 FK。 |
| `014_qa_and_report_versions` | 6 | `qa_issues`、`report_versions` | QA Issue 支持来源、严重级别和处理状态索引；ReportVersion 的 Case/version 唯一，并引用 WorkflowVersion 和 NarrativePlan。 |
| `015_skill_examples` | 7 | `skill_examples` | Skill/Example key/version 唯一；状态、目标 Fragment 和适用标签索引；只保存经脱敏和审核的发布候选/版本。 |

以上合计正好覆盖目标的 14 张工作流表。Phase 4 以 API 和工作台为主，不需要单独新增表；Capability 初期由 Step 的 `required_capability` 与现有角色/分配规则映射，不另建角色副本表。

### Migration 细节

- **字段类型**：状态、版本、外键、时间和查询键使用独立列；JSONB 只放配置快照、结构化内容、输入/输出快照和扩展元数据。
- **current 唯一约束**：PostgreSQL 部分唯一索引按 Case 与 Finding/Fragment key 限制 `is_current = true`。先检查所有写入路径均在同一事务中关闭旧 Revision、创建新 Revision。
- **发布不可变**：数据库约束保证 key/version 唯一；发布后不可修改由领域服务禁止更新并以测试覆盖。若业务要求绕过应用也强制不可变，再评估数据库 Trigger，不在首批迁移中预设复杂 Trigger。
- **Outbox**：状态与业务事件在同一事务插入；独立 Worker 读取待发送事件，成功后标记发布，失败按退避重试。以 Outbox 行 ID 作为稳定事件 ID；消费者按事件 ID 和目标 Step 的当前状态/激活次数幂等处理。若实现选择额外的去重列或唯一键，应作为 Schema 扩展明确记录。
- **删除策略**：Case、已交付版本、SkillRun、Revision 和审计链优先使用 RESTRICT/软删除或保留策略；不要用级联删除抹除追溯记录。具体 FK 的 `ondelete` 按拥有关系逐表评审。
- **发布数据**：初始 WorkflowVersion 和 SkillVersion 通过有版本控制的 seed/CLI 建立，迁移只负责 Schema。Seed 必须幂等，并记录 definition/specification 的内容版本。
- **回滚策略**：空库或尚未写入业务数据时可回退；有新 Case、Run 或交付版本后不以 downgrade 删除数据作为发布回滚。应用回滚通过关闭入口/回退适配器完成，数据修复用新的前向迁移。

## 3. 数据切换与兼容步骤

### 上线前盘点

1. 在目标环境确认实际 `alembic_version`、表/索引与 `009` 的差异；现有分析只覆盖仓库定义，没有读取部署数据库。
2. 统计 `service_requests` 中报告类申请的各状态、`report_tasks` / `service_request_tasks` 中的活跃任务，以及已交付 `reports` 数量；核对是否有旧任务无法恢复。
3. 决定两条报告入口的目标：咨询师报告申请切到 ReportCase；`POST /reports` 是继续创建 Case 并走专用 Workflow，还是暂留在旧流程。决定前不删除入口。
4. 决定在途请求采用“排空旧流程”还是“迁入新流程”。默认建议先排空旧流程；确需迁入时，提供逐状态映射和可重复执行的 backfill 命令，并保留源 ID。

### Expand / Cutover / Contract

1. **Expand**：依次应用 `010`–`015`，保持旧表和旧 API 可用。第一阶段仅需要 `010`，其余迁移随对应阶段交付。
2. **Seed**：写入并发布初始 Sequential WorkflowVersion；Phase 2 再发布首个 SkillVersion。Seed 重跑不得创建重复版本。
3. **逐入口切换**：在服务端入口适配层将新建报告申请交给 ReportCase；用唯一来源关联或幂等键避免同一请求重复建 Case。一次请求只由一套 Workflow 拥有状态。
4. **历史兼容**：已交付旧报告仍从 `reports` 返回；新报告由 `report_versions` 返回，并由 Reports API 投影成当前前端响应。后续要不要为历史 `reports` 创建 `report_versions`，单独评估来源完整性、审计要求和迁移收益。
5. **Contract**：只有监控确认旧报告生产路径停止写入、旧活跃任务清零、所有客户端读取已切换且保留要求已满足后，才另开退役迁移。`service_requests` 仍服务日历流程时不能删除整表；旧草稿/任务表也可能仍被日历路径使用。

## 4. Phase 1–7 开发计划

### Phase 1：Workflow 与 Version 基座

**目标**：不接 AI，跑通纯人工 Sequential Workflow。

**开发项**：

- 后端建立 ReportCase、WorkflowVersion、WorkflowInstance、StepTask、Outbox 的模型、仓储和领域服务；定义状态转换表与合法事件。
- 支持发布版本固定到 Instance、Step 激活、人工指派、完成门禁、Return/Reopen、`activation_no` 增长和取消/暂停规则。
- 在一个事务中提交业务状态与 Outbox 事件；新增 Outbox Worker/Celery 投递适配及按 Outbox 行 ID 幂等消费。
- 在 `api/v1/` 建立 Case/Workflow HTTP 适配；跨域流程放 `application/`，领域模块不导入 API、application 或 tasks。
- 确认报告申请与自助报告两类来源字段/幂等键和 Case 创建规则；先通过 API 或管理命令驱动，不要求本阶段完成完整工作台 UI。

**验证与退出条件**：纯人工流程可创建 Case、固定版本、顺序激活、完成、退回、重开；不合法状态转换被拒绝；携带相同 Outbox 行 ID 的事件重复投递不重复推进；已发布 WorkflowVersion 不可原地编辑。

### Phase 2：Skill Runtime

**目标**：Step 可由固定 SkillVersion 生成结构化结果并完整追踪。

**开发项**：

- 建立 SkillVersion 发布/查询、SkillRun 幂等创建和执行状态服务。
- 实现 SkillExecutor、ContextBuilder、PromptAssembler、ModelGateway、OutputValidator、Guardrail 与 TraceRecorder；模型供应商 HTTP 细节封装在 Gateway。
- 将当前确定性命理计算和现有单步报告生成适配为首个 Skill。保留既有 Prompt 和解析器作为起点，逐步替换直接调用，不重写算法。
- 在 SkillRun 保存固定版本、脱敏策略允许的输入/Context 快照、模型参数、原始/解析输出、耗时和错误；定义敏感内容的访问权限与保留期限。

**验证与退出条件**：指定 Step 执行固定 SkillVersion 得到符合 Contract 的结果；重复请求由幂等键复用/返回既有 Run；可以从 Run 追溯版本和模型 Trace；模型失败状态可恢复，不伪装成成功输出。

### Phase 3：Evidence / Finding / Fragment

**目标**：把输入事实、专业判断和内容片段分开保存，并实现依赖失效传播。

**开发项**：

- 把 Case 输入快照、用户明确提供的情境和确定性计算结果整理为带 source/status 的 Evidence；保留原输入，不由 AI 补造事实。
- 建立 Finding 的类型、角色、置信度、重要度、可报告性、状态、证据引用和 Relation 引用；变更采用 append-only Revision。
- 建立 Analysis/Report Fragment Revision，分别记录 Semantic Revision、Content Revision、Source Snapshot、Owner Step、来源 SkillRun 和 stale 原因。
- 实现 Semantic Edit、Style Edit 与 StalePropagation；依赖图用显式 Finding/Fragment 引用，不以“同一 Case”作为全部下游内容的失效理由。
- 定义人工接受、修改、拒绝、新增 Finding 的领域事件与 Revision 归属。

**验证与退出条件**：更改确实被 Fragment 引用的 Finding 会将下游 Fragment 标为 STALE；只改文风/措辞不传播；拒绝 Finding 不被下游作为已确认语义资产读取；所有 current Revision 唯一。

### Phase 4：Consultant Workbench

**目标**：咨询师在界面内完成 Step 审核，无需编辑底层 JSON。

**开发项**：

- 扩展 `src/features/service-requests/` 或在确认边界后建立报告 Case feature；API 留在对应 feature 的 `api.js`，统一经过 `apiClient`。
- 在 StaffConsole 增加 Case 队列、当前 Step、所需 Capability、Step 状态和分配视图；已有服务申请/日历工作台继续使用原 API。
- 提供 AI Draft、Evidence 查看、Finding 接受/修改/拒绝/新增、Fragment 编辑、保存冲突提示、Complete Step、Return/Reopen 等操作。
- 用现有角色和有效申请分配关系实现 Capability Adapter；服务端每个读写操作均重新校验，前端隐藏按钮不作为授权。
- 逐步复用 Vant 4、共享按钮、设计 Token 和现有组件；敏感输入不额外显示无关咨询师内部 Trace。

**验证与退出条件**：咨询师仅能看到已分配 Case 和当前 Step 所需内容；管理员按目标权限管理；关键操作可键盘访问且有明确加载/冲突/失败状态；可完成至少一条真实端到端的人工审核流程。

### Phase 5：Narrative / Report Authoring

**目标**：报告从 Confirmed Semantic Assets 写作，不再把前序长文整体重读后重新综合。

**开发项**：

- 实现 CaseSemanticModelBuilder，仅从已确认 Finding/Fragment 及所需 Evidence 投影结构化语义模型。
- 通过 Authoring Skill 生成 Narrative Candidate；记录来源 SkillRun、适用章节和覆盖信息。
- 建立 NarrativePlan 版本、候选选择与咨询师确认；改动已确认语义资产时按来源关系使受影响 Plan/Fragment 失效。
- 按 Fragment 写作并保存 ReportFragment Revision；保留“你是谁 / 卡在哪 / 往哪去”的产品章节边界，标题和排序允许内容规划调整。

**验证与退出条件**：报告片段能反查语义来源；咨询师能选定并确认 NarrativePlan；未确认 Finding、STALE 内容和无来源强结论不能进入最终候选。

### Phase 6：Final QA / Delivery

**目标**：程序 QA 和人工最终门禁通过后交付不可变 ReportVersion。

**开发项**：

- 实现 Programmatic QA：必需 Fragment 覆盖、Schema、Source Map、事实一致性基础校验、STALE 检查和禁用表达规则。
- 实现 Validator Skill 与 `qa_issues` 生命周期，支持 BLOCK/MAJOR/MINOR、指派处理、重跑及关闭原因。
- Human Final Gate 检查阻断问题和必需人工确认；BLOCK 时服务层拒绝 Assembly/Delivery。
- ReportAssembler 将 Fragment、语义快照、NarrativePlan、WorkflowVersion 组合成 `report_versions`；交付后禁止更新既有版本，只能新增版本。
- 为旧 `GET /reports`、报告详情和用户中心提供兼容读取投影；建立历史报告与新版本的排序、删除/隐藏和权限规则。
- 报告完成后通过明确接口提供日历下游所需来源，不把 Calendar 状态纳入 ReportVersion。

**验证与退出条件**：存在 BLOCK 时任何交付入口都不能生成版本；通过后每个 Case 的版本号唯一递增；已交付快照不可覆盖；旧历史可读；咨询师与用户访问范围一致。

### Phase 7：Dynamic Few-shot / Evaluation

**目标**：将经审核的专业修改沉淀为可控 Examples，并验证 Skill 变化。

**开发项**：

- 定义 Example Candidate 来源、脱敏检查、咨询师推荐、审核/发布、撤回与版本策略。
- 基于 Skill/Fragment、情境标签和适用性实现确定性检索；记录每个 SkillRun 采用的 Example ID/版本和筛选原因。
- 建立离线 Evaluation 与文件化 Regression Dataset；覆盖 Schema、来源忠实、安全边界、语义一致、文风和行动建议。
- Skill 新版本发布前比较回归结果；不做自动 Skill 发布、线上自动 A/B 或自动从生产结果学习。

**验证与退出条件**：候选 Example 未审核前不会进入检索；已发布 Example 有脱敏与来源信息；新 SkillRun 可复现使用的 Example 集；回归失败会阻止发布流程。

## 5. 每阶段交付检查

仓库约定的验证命令可作为实现阶段的检查项；此计划阶段没有运行这些命令：

- 后端：从 `backend/` 运行 `python -m pytest`；迁移需覆盖从 `009` 升级的 Schema 检查。
- 前端纯逻辑：按涉及模块运行 `node --test`。
- 前端生产构建：运行 `npm run build`。
- 每阶段额外验收：API 契约/权限、迁移前后数据行数、Outbox 重试与幂等、Revision 不可变、STALE 传播、QA 门禁和版本快照。

## 6. 开发前需定下的产品与数据决策

| 决策 | 建议默认值 | 影响阶段 |
|---|---|---:|
| 用户自助 `POST /reports` 是否进入新 Case Workflow | 先保留现有行为；上线前明确是否转为专用自动 Workflow，避免绕过目标门禁仍被误认为已迁移 | 1、2、6 |
| 旧报告类服务申请的在途任务 | 默认排空后切流；无法排空的记录逐条制定状态映射 | 1 |
| 历史 `reports` 是否转成 `report_versions` | 默认不伪造缺失的 Workflow/Narrative 来源，保留旧读模型；若统一版本列表是硬需求，再做可审计的 Legacy Import | 6 |
| `report_cases` 与旧入口来源关联 | 建议新增两个具体可空 FK，分别指向 `service_requests` 和 `report_tasks`，并加互斥约束；这是目标字段表之外的兼容扩展 | 1 |
| SkillRun Prompt/输入保存期限与访问范围 | 记录版本追溯所需内容，同时限制咨询师可见范围并制定敏感数据保留/清理规则 | 2 |
| Example 脱敏与发布责任 | 咨询师提出，授权审核角色确认，默认不自动发布 | 7 |

