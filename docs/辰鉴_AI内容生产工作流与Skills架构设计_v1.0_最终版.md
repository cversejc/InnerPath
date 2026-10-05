# 辰鉴（chenvis）AI 内容生产工作流与 Skills 架构设计 v1.0

> 文档性质：最终架构基线 / Codex 开发输入文档
> 适用范围：人生说明书生产、咨询师协作、AI Skills、Dynamic Few-shot、质量审核、报告交付、下游决策日历
> 当前阶段：业务与技术架构冻结；下一步由 Codex 结合现有 InnerPath 代码进行差距分析、数据迁移设计与开发实施
> 重要说明：本文定义“目标架构与 V1 约束”，**不要求 Codex 机械重写现有代码**。开发前必须先做现状映射，优先复用已经正确存在的模块与数据结构。

---

# 0. 文档目标

本文用于把已经确认的辰鉴 AI 内容生产方案固化成一份可直接交给 Codex 的工程设计基线。

本文重点解决：

- 一份人生说明书从申请到最终交付如何流转；
- AI 与人工分别在哪些节点工作；
- Workflow、Step、Skill、Tool、Prompt 的边界；
- 专业分析如何从“大段 Prompt 链”升级为结构化语义资产；
- Finding、AnalysisFragment、ReportFragment 如何版本化和追溯；
- 如何避免多阶段 AI 推断不断放大；
- 如何在最终写作阶段做到“形散神不散”；
- 如何做 Final QA；
- 如何沉淀咨询师经验，构建 Dynamic Few-shot；
- V1 到底需要哪些数据库实体，哪些概念只作为运行时对象；
- Codex 开发过程中哪些架构原则不得被擅自改变。

本文不处理：

- 现有 InnerPath 代码的具体类名映射；
- 当前数据库 Migration 细节；
- 前端具体组件实现；
- 大模型供应商最终选型；
- 生产容量参数。

这些应在 Codex 完成现状扫描后进入落地设计。

---

# 1. 产品与业务基线

辰鉴的人生说明书不是简单的“命理报告生成器”，而是一套以传统象征系统作为观察框架、结合用户自述、心理学概念与哲学表达，帮助用户理解自身运行模式、重复冲突、潜在资源与成长方向的内容产品。

产品主旨：

> 命理为表，心理为里，哲学为根。重点不是对用户做宿命式定论，而是帮助用户看见自身的运行模式，并将理解转化为现实行动。

最终报告保持三个核心章节：

```text
你是谁
↓
卡在哪
↓
往哪去
```

但内部小标题、重点排序、叙事顺序、表达风格可以针对不同 Case 动态变化。

整个系统必须遵循以下内容边界：

- 命理信息是象征性解释框架，不直接等同医学、精神医学或人格障碍诊断；
- 单一十神、星曜、功能倾向不足以形成强人格结论；
- 强结论需要尽量跨来源、跨系统印证；
- 使用倾向性、条件式语言；
- 大运、流年等只作为阶段主题或触发窗口，不写成必然未来；
- 多来源冲突时保留冲突并交给人工判断，不由 AI 强行统一；
- 用户现实经验优先校正模型；
- 如果用户未自报 MBTI，不允许从命理或其他信息直接推断具体 MBTI 类型；
- AI 不得编造用户没有提供过的具体生活经历；
- 最终报告不得因为“风格适配”而改变案例事实或核心专业判断。

---

# 2. 总体架构定位

辰鉴不是：

```text
用户资料
↓
Prompt 1
↓
Prompt 2
↓
Prompt 3
↓
大模型生成完整报告
```

而应该是：

```text
用户与确定性数据
      ↓
Evidence
      ↓
AI 提出专业判断
      ↓
专家确认
      ↓
Case Semantic Model
      ↓
AI 设计叙事方案
      ↓
专家做少量高价值选择
      ↓
AI 分 Fragment 写作
      ↓
人工内容审核
      ↓
独立 Final QA
      ↓
程序冻结交付
```

架构关键词：

```text
Human-in-the-loop
Semantic-first
Versioned
Traceable
Fragment-based
Evaluation-driven
Dynamic Few-shot
```

---

# 3. 四层内容模型

整个人生说明书生产拆成四层。

```text
① Evidence Layer
Fact / User Input / Tool Result

        ↓

② Semantic Layer
Finding
AnalysisFragment
Relations
Case Semantic Model

        ↓

③ Narrative Layer
Narrative Candidate
NarrativePlan
ReportFragment

        ↓

④ Delivery Layer
Final QA
ReportAssembler
ReportVersion
```

AI 在各层权限不同：

```text
Evidence Layer
AI = READ
禁止伪造 Fact

Semantic Layer
AI = PROPOSE
Human = CONFIRM

Narrative Layer
AI = SELECT / ORGANIZE / TRANSLATE / WRITE
禁止产生新的专业 Finding

Delivery Layer
AI = VALIDATE
禁止静默改写已确认正式内容
```

这是整个系统最重要的权限边界之一。

---

# 4. Workflow / Step / Skill / Tool 的边界

## 4.1 Workflow

Workflow 负责：

> 什么时候做什么、执行顺序、谁负责、完成后进入哪里。

Workflow 不保存 Prompt 细节。

## 4.2 Step

Step 是一个业务节点。

例如：

```text
命理基础分析
心理映射
三重整合
卡点与行动
报告写作
最终 QA
```

一个 Step 可以由：

```text
SYSTEM
HUMAN
```

执行。

AI Assistance 与执行主体正交。

因此支持：

```text
SYSTEM + AI
HUMAN + AI Draft
HUMAN + No AI
SYSTEM + Deterministic Processor
```

## 4.3 Skill

Skill 是：

> 一个可版本化、可评测、可组合的 AI 业务执行规范。

Skill 不是：

- Workflow；
- Step；
- Tool；
- Agent；
- 单纯 Prompt 字符串。

一个 Skill 至少包含：

```text
Identity
Input Contract
Context Policy
Instructions
Knowledge Policy
Example Policy
Processor Policy
Tool Policy
Model Policy
Output Contract
Guardrails
Evaluation Profile
```

## 4.4 Tool / Processor

Tool / Processor 负责确定性能力。

例如：

```text
bazi.calculate_chart
ziwei.calculate_chart
normalize_questionnaire
build_case_semantic_model
render_report
```

原则：

> 能稳定程序化的事情，不让 LLM 猜。

V1 使用代码 Registry，不做 Tool 管理后台，不允许模型任意执行脚本。

---

# 5. Workflow Version 与 Skill Version

## 5.1 Workflow Version

Workflow 发布后不可原地修改。

```text
Draft
↓
Published
↓
Retired
```

ReportCase 创建后绑定一个确定的 `workflow_version_id`。

老 Case 不自动迁移到新 Workflow。

## 5.2 Skill Version

Skill 同样：

```text
Draft
↓
Evaluation
↓
Published
↓
Retired
```

Published SkillVersion 不允许原地修改。

WorkflowVersion 应绑定具体 SkillVersion，而不是只绑定 Skill Key。

这保证历史报告可以复现：

```text
当时用了哪个 Workflow？
当时用了哪个 Skill？
当时模型是什么？
当时 Context 是什么？
当时检索了哪些 Example？
```

---

# 6. 人生说明书完整业务 Workflow

```text
Phase A · 数据准备

S0 基础数据准备
SYSTEM

用户问卷
+ 八字 Tool
+ 紫微 Tool
+ 用户自报心理/MBTI信息
+ 其他结构化信息

        ↓

Phase B · 专业分析

S1 命理基础结构
AI + 命理咨询师

        ↓

S2 命理 → 心理映射
AI + 对应专业审核

        ↓

S3 命理 × 心理 × 哲学整合
AI + 对应专业审核

        ↓

S4 心理机制 / 卡点 / 行动
AI + 心理咨询师

        ↓

Phase C · 内容生产

S5 人生说明书首席作者

5A Narrative Planning
5B Human Editorial Choice
5C Report Fragment Authoring
5D Editorial Review

        ↓

Phase D · 质量闸门

S6 Final QA

Programmatic QA
↓
LLM Semantic QA
↓
Human Final Gate

        ↓

Phase E · 交付

ReportAssembler
↓
Immutable ReportVersion
↓
DELIVERED
```

---

# 7. S0：Evidence Layer

S0 只负责形成可靠输入，不负责人格解释。

来源类型：

```text
USER_PROVIDED
SYSTEM_CALCULATED
EXTERNAL_REFERENCE
```

示例：

```text
用户问卷答案
用户当前困扰
MBTI 自报结果
八字排盘结果
紫微排盘结果
当前时序数据
```

一个 Evidence Item 需要明确：

```text
source_type
source_ref
value
```

AI 不允许把自己的上游推断伪装成 Evidence。

---

# 8. Analysis Space：Fact → Finding → AnalysisFragment

前四步的正式生产结果不是四篇长文档，而是：

```text
Fact / Evidence
      ↓
Finding
      ↓
AnalysisFragment
```

长文本只作为咨询师阅读和表达层存在。

## 8.1 Finding

Finding 是整个系统最重要的最小专业判断单位。

一个 Finding 表达一个尽量原子的判断，例如：

```text
当前阶段可能存在稳定需求与自主需求之间的明显张力。
```

Finding 不应该把五六个结论揉成一整段文章。

推荐逻辑字段：

```json
{
  "finding_key": "psychology.stability_autonomy_tension",
  "claim": "当前阶段可能存在稳定需求与自主需求之间的明显张力",
  "kind": "FINDING",
  "semantic_role": "CONFLICT",
  "confidence": "MEDIUM",
  "importance": "HIGH",
  "reportability": "RECOMMENDED",
  "status": "CONFIRMED",
  "evidence_refs": [],
  "structured_data": {}
}
```

## 8.2 Finding 状态

```text
PROPOSED
CONFIRMED
REJECTED
SUPERSEDED
```

AI 初始产生：

```text
PROPOSED
```

人工认可：

```text
CONFIRMED
```

人工否定：

```text
REJECTED
```

后续被新的 Finding Revision 取代：

```text
SUPERSEDED
```

---

# 9. Finding 元数据

## 9.1 confidence

```text
LOW
MEDIUM
HIGH
```

表示证据支撑强度。

## 9.2 importance

```text
LOW
MEDIUM
HIGH
CRITICAL
```

回答：

> 这个 Finding 在当前 Case 中有多重要？

## 9.3 reportability

```text
INTERNAL_ONLY
OPTIONAL
RECOMMENDED
MUST_INCLUDE
```

回答：

> 这个 Finding 适合多大程度进入最终用户报告？

`importance` 与 `reportability` 必须分开。

例如某个命理技术判断可以：

```text
importance = HIGH
reportability = INTERNAL_ONLY
```

它对专家分析非常重要，但最终用户未必需要看到其专业术语。

## 9.4 semantic_role

V1 建议：

```text
IDENTITY
RESOURCE
SHADOW
COMPLEX
DEFENSE
CONFLICT
PATTERN
BLOCK
NEED
INTEGRATION_DIRECTION
TIMING
ACTION
```

---

# 10. Signal 与正式 Finding

Step 1 中的心理解释不能直接作为正式心理结论。

建议：

```text
kind = SIGNAL
```

例如：

```json
{
  "claim": "可能存在较强的外部评价敏感性",
  "kind": "SIGNAL",
  "confidence": "LOW",
  "requires_cross_validation": true
}
```

Step 2 再结合：

```text
用户问卷
+
其他 Evidence
+
Step 1 Signals
```

形成正式 Finding。

目的：防止推断放大。

```text
Step 1 小推测
↓
Step 2 当事实
↓
Step 3 再推一层
↓
Step 4 写成强结论
```

这种链路必须被架构阻断。

---

# 11. AnalysisFragment

AnalysisFragment 是咨询师实际审核与编辑的专业主题单元。

一个 Fragment 可以聚合多个 Findings。

例如：

```text
analysis.psychology.core_complex
analysis.psychology.relationship_cycle
analysis.integration.self_direction
analysis.action.practice_rhythm
```

AnalysisFragment 不是最终给用户看的文章。

---

# 12. S1：Metaphysics Foundation

推荐稳定 Fragment Key：

```text
analysis.metaphysics.core_structure
analysis.metaphysics.visible_pattern
analysis.metaphysics.hidden_pattern
analysis.metaphysics.internal_tension
analysis.metaphysics.resources
analysis.metaphysics.relationship_structure
analysis.metaphysics.timing
analysis.metaphysics.ziwei_structure
```

职责：

- 整理八字与紫微确定信息；
- 形成命理层专业判断；
- 产生待验证 Psychological Signals；
- 不直接定性人格或心理问题。

---

# 13. S2：Psychology Mapping

推荐 Fragment：

```text
analysis.psychology.persona
analysis.psychology.self_belief
analysis.psychology.shadow
analysis.psychology.core_complex
analysis.psychology.conflict_cycle
analysis.psychology.authority_superego
analysis.psychology.resources
```

这是正式心理 Finding 最重要的产生阶段。

`core_complex` 推荐结构化：

```json
{
  "name": "...",
  "trigger": [],
  "core_emotion": [],
  "automatic_thought": "...",
  "defensive_response": "...",
  "short_term_function": "...",
  "long_term_cost": "...",
  "evidence": [],
  "confidence": "MEDIUM"
}
```

特别强调：

> 心理结构必须描述为“运作模式”，而不是临床诊断。

---

# 14. S3：Integration

S3 不重新做一遍心理分析，而负责整合。

推荐 Fragment：

```text
analysis.integration.central_tension
analysis.integration.archetype
analysis.integration.individuation_stage
analysis.integration.life_timing
analysis.integration.self_direction
analysis.integration.integration_task
```

其中以下通常具有最高重要性：

```text
central_tension
self_direction
integration_task
```

这些内容后续直接参与 Narrative Planning。

`self_direction` 不应表达为“未来完美人格”，而应描述：

```text
当前倾向的 A 端
↕
被排除/不足的 B 端
↓
需要发展的整合能力
```

---

# 15. S4：Mechanism / Block / Action

S4 分三组。

## 15.1 Mechanism

```text
analysis.mechanism.defense
analysis.mechanism.energy
analysis.mechanism.relationship_cycle
analysis.mechanism.cognitive_style
```

## 15.2 Block

最终选择 4～5 个最重要 Block。

```text
analysis.blocks.block_01
analysis.blocks.block_02
analysis.blocks.block_03
analysis.blocks.block_04
analysis.blocks.block_05
analysis.blocks.common_pattern
```

标准结构：

```json
{
  "title_internal": "...",
  "importance": "HIGH",
  "real_world_scenarios": [],
  "mechanism": "...",
  "trigger": [],
  "protective_function": "...",
  "long_term_cost": "...",
  "underlying_need": "...",
  "self_invitation": "...",
  "related_findings": [],
  "evidence": []
}
```

这一阶段先理解模式，不在每个 Block 中提前完整给解决方案。

## 15.3 Action

```text
analysis.action.breakthrough
analysis.action.experiments
analysis.action.practice_rhythm
```

Action 推荐结构：

```json
{
  "name": "...",
  "target_pattern": "block_02",
  "target_capability": "...",
  "method": "...",
  "framework": "CBT",
  "instruction": "...",
  "frequency": "weekly",
  "difficulty": "low",
  "why_it_matches": "...",
  "expected_observation": "..."
}
```

Action 必须能追溯：

```text
Finding
↓
Block / Need
↓
Integration Task
↓
Action
```

不能出现与 Case 无关的泛化建议。

---

# 16. Practice Rhythm 与 Calendar

练习节奏需要结构化：

```json
{
  "daily": [],
  "weekly": [],
  "monthly": [],
  "quarterly": []
}
```

这是人生说明书与后续 Calendar Workflow 的重要接口。

下游链路：

```text
Delivered ReportVersion
↓
用户主动请求
↓
CalendarContextProjection
↓
Calendar Skill
↓
CalendarVersion
```

Calendar 是独立 Workflow，不是人生说明书 Workflow 的最后一个 Step。

---

# 17. MBTI / 荣格八维规则

如果用户自报：

```json
{
  "mbti": {
    "value": "ENFP",
    "source": "USER_PROVIDED"
  }
}
```

如果没有：

```json
{
  "mbti": null,
  "function_tendencies": [
    {
      "function": "Ne",
      "claim": "呈现一定探索倾向",
      "source": "AI_GENERATED",
      "confidence": "LOW"
    }
  ]
}
```

禁止把：

```text
类似 Ne 式探索
```

升级成：

```text
你就是 ENFP
```

---

# 18. Finding-first / Structure-first 生产模式

S1～S4 不采用：

```text
AI 直接写完整分析文
↓
人工从头修改
```

正式模式：

```text
SkillRun
↓
Candidate Semantic Output
+
Provisional Fragment
↓
Human Semantic Review
↓
Confirmed Semantic Output
↓
必要时重新生成 Fragment
↓
Confirmed AnalysisFragment
```

逻辑上 Finding-first，体验上不要求两次 AI 调用。

AI 第一次可同时返回：

```json
{
  "findings": [],
  "fragments": [
    {
      "key": "psychology.core_conflict",
      "finding_refs": [],
      "content": "..."
    }
  ]
}
```

---

# 19. 咨询师语义审核交互

咨询师主要只需要四种操作：

```text
接受
修改
拒绝
新增
```

普通 Finding 不要求逐条点击确认。

完成 Fragment 时可批量确认没有被修改/拒绝的普通 Finding。

以下必须显式处理：

```text
LOW confidence
与 Evidence 冲突
高风险 Finding
Guardrail 标记
```

工作台的核心不是让咨询师维护 JSON，而是展示：

```text
正文
核心判断
依据
置信度
风险
```

---

# 20. Semantic Edit 与 Style Edit

这是后续 STALE 的基础。

如果咨询师只是修改表达：

```text
STYLE_EDIT
content_revision + 1
semantic_revision 不变
```

如果改变真实专业判断：

```text
SEMANTIC_EDIT
semantic_revision + 1
content_revision + 1
```

V1 若无法可靠自动识别，可让咨询师保存较大修改时选择：

```text
主要是表达修改
改变了分析判断
```

之后再逐步增加 AI Diff 辅助判断。

---

# 21. Fragment Revision 与 STALE

Fragment 必须具备：

```text
revision_no
semantic_revision
content_revision
```

下游通过 Source Snapshot 记录当时使用的上游 Revision。

例如：

```json
{
  "findings": [
    {
      "finding_key": "psychology.core_complex",
      "revision_no": 3
    }
  ],
  "fragments": [
    {
      "fragment_key": "analysis.psychology.shadow",
      "semantic_revision": 2
    }
  ]
}
```

如果上游只是：

```text
content_revision 2 → 3
semantic_revision 不变
```

下游不 STALE。

如果：

```text
semantic_revision 2 → 3
```

依赖下游必须：

```text
STALE
```

但不自动覆盖人工成果。

---

# 22. Case Semantic Model

S1～S4 完成后形成：

```text
Case Semantic Model
```

它不是新事实，也不是数据库实体。

它是当前 Case 已确认 Semantic Assets 的运行时 Projection。

逻辑区域：

```text
FACTS
IDENTITY
DYNAMICS
BLOCKS
DIRECTION
ACTIONS
```

示意：

```json
{
  "facts": {},
  "identity": {
    "persona": [],
    "resources": [],
    "hidden_sides": []
  },
  "dynamics": {
    "central_tension": "...",
    "core_complex": "...",
    "defense": "...",
    "repeated_pattern": "..."
  },
  "blocks": [],
  "direction": {
    "current_stage": "...",
    "self_direction": "...",
    "integration_task": "..."
  },
  "actions": []
}
```

由：

```text
CaseSemanticModelBuilder
```

运行时生成，并在 SkillRun 中保存 Context Snapshot 以便复现。

---

# 23. Semantic Relations

V1 逻辑层支持：

```text
SUPPORTED_BY
CONTRADICTS
REFINES
EXPLAINS
MANIFESTS_AS
ADDRESSED_BY
RELATED_TO
```

例如：

```text
Core Complex
    ↓ MANIFESTS_AS
Block 02
    ↓ ADDRESSED_BY
Action 03
```

V1 不需要图数据库。

关系可先保存在 Revision JSONB 中，需要复杂查询后再正规化。

---

# 24. Analysis Space 与 Report Space

这是最终架构的核心区分。

```text
Analysis Space
= 后台专业语义资产

Report Space
= 用户最终阅读内容
```

关系：

```text
Evidence
↓
Finding
↓
AnalysisFragment
↓
Report Authoring
↓
ReportFragment
↓
ReportVersion
```

一个 ReportFragment 可以依赖多个 AnalysisFragment / Finding。

一个 Analysis Finding 也可以被多个 ReportFragment 使用。

---

# 25. S5：Report Authoring

S5 不是 ReportAssembler。

S5 是一个真正的 AI + Human 内容生产 Step。

内部流程：

```text
5A Narrative Planning
        ↓
5B Human Editorial Choice
        ↓
5C Report Fragment Authoring
        ↓
5D Editorial Review
```

Workflow 层仍然可以只表现为一个 S5 Step。

---

# 26. Narrative Planner

输入：

```text
CRITICAL / HIGH Confirmed Findings
Confirmed AnalysisFragments
Candidate Blocks
Self Direction
Integration Task
Actions
用户关注问题
用户现实问卷
Presentation Preference
```

明确不输入：

```text
Rejected Findings
历史 AI Draft
咨询师内部讨论
已被替代旧结论
```

Narrative Planner 不是重新分析用户，而是：

> 在已经确认的 Semantic Model 上决定“讲什么、先讲什么、哪些弱化、哪条线贯穿整本报告”。

---

# 27. Narrative Candidate

AI 一次生成 2～3 个方案。

```json
{
  "theme": "从外部评价走向内部主权",
  "rationale": "...",
  "supporting_findings": [],
  "priority_blocks": [],
  "deemphasized_findings": [],
  "narrative_arc": []
}
```

不要求 AI 给唯一答案。

Candidate 只存在于 SkillRun Output，不独立建表。

---

# 28. Human Editorial Choice

最终咨询师不从零设计报告，只做少量高价值选择：

```text
核心主题
主叙事暗线
4～5 个关键 Block
核心 Self Direction
是否遗漏用户最关心问题
```

原则：

```text
AI 负责发现候选结构
↓
人负责最终选择
↓
AI 负责完成写作
```

---

# 29. NarrativePlan

咨询师确认后形成正式 NarrativePlan。

```json
{
  "version": 1,
  "core_theme": "...",
  "selected_candidate": "candidate_b",
  "priority_blocks": [],
  "must_include_findings": [],
  "self_direction": "finding_xxx",
  "reader_profile": {
    "directness": "medium",
    "warmth": "medium",
    "theory_density": "low",
    "action_density": "high",
    "metaphor_density": "medium"
  },
  "narrative_arc": [],
  "chapter_strategy": {}
}
```

NarrativePlan 独立版本化。

如果只是 NarrativePlan 改变：

```text
ReportFragment → STALE
stale_reason = NARRATIVE_CHANGED
```

Analysis Space 不受影响。

如果 Analysis Semantic 改变：

```text
NarrativePlan → STALE
ReportFragment → STALE
stale_reason = SOURCE_CHANGED
```

---

# 30. ReportFragment

最终报告不一次生成整本，也不一句话一个 Fragment。

推荐粒度：

> 一个完整用户可感知的小节。

示例：

```text
你是谁
├─ 世界看到的你
├─ 你眼中的自己
├─ 被隐藏的自己
├─ 核心张力
├─ 能量运作模式
└─ 关系模式

卡在哪
├─ Block 1
├─ Block 2
├─ Block 3
├─ Block 4
├─ Block 5
├─ 共性模式
└─ 破局点

往哪去
├─ 当前阶段
├─ 阶段地图
└─ 成长实验
```

ReportFragment Output：

```json
{
  "title": "...",
  "content": "...",
  "used_findings": [],
  "used_actions": [],
  "transition_hint": "...",
  "presentation_meta": {}
}
```

---

# 31. Report Authoring Skill 权限

允许：

```text
SELECT
TRANSLATE
ORGANIZE
EXPRESS
CONNECT
```

禁止：

```text
CREATE_NEW_FACT
CREATE_NEW_FINDING
CHANGE_CONFIDENCE
OVERRIDE_HUMAN_CONFIRMATION
```

如果写作阶段发现缺少支撑：

```text
MISSING_SEMANTIC_SUPPORT
```

不得自行补出一个新的心理结论。

---

# 32. Source Map / Provenance

ReportFragment 必须保存当时使用的：

```text
Finding Revision
Analysis Fragment Revision
NarrativePlan Version
```

V1 使用 `source_snapshot JSONB`。

这样最终可以追溯：

```text
用户看到的一段报告
↓
用了哪些 Confirmed Finding
↓
这些 Finding 来自哪些 Evidence
```

这也是 Final QA、重复检测、未来审计的基础。

---

# 33. Dynamic Few-shot

Dynamic Few-shot 必须进入 V1。

但生产 Case 不能直接作为 Example Source。

流程：

```text
优秀人工结果
↓
推荐为 Example Candidate
↓
人工审核
↓
脱敏
↓
PUBLISHED
↓
Example Library
```

Example 生命周期 V1：

```text
CANDIDATE
PUBLISHED
RETIRED
```

---

# 34. Example 类型

V1 支持：

```text
POSITIVE
CONTRASTIVE
MISSED_INSIGHT
```

其中 `MISSED_INSIGHT` 非常重要：

```text
Input Context
↓
AI 没发现
↓
Human Added Finding
↓
Teaching Point
```

它能让系统逐步学习“应该看见什么”。

---

# 35. Example 分层

至少分：

```text
ANALYSIS EXAMPLES
AUTHORING EXAMPLES
VALIDATION EXAMPLES
```

Analysis Example 教：

> 面对这类输入应该形成什么专业判断。

Authoring Example 教：

> 已确认的判断应该如何表达给用户。

Validation Example 教：

> 哪些属于事实漂移、越界、重复、过度推断。

三类不能混用。

---

# 36. Dynamic Example Retrieval

V1 推荐：

```text
Skill / Fragment 过滤
↓
Tag / Scenario 过滤
↓
Embedding Top-K
↓
Quality Filter
↓
Diversity 去重
↓
最终 Top 2~3
```

禁止简单使用“整个用户 Profile 做向量相似度 TopK”。

SkillRun 必须记录：

```text
Example ID
Example Version
Retrieval Score
Retrieval Policy
```

Example 只是参考，不是事实来源。

Prompt 中必须明确：

> 不得把 Example 中其他用户的具体事实迁移到当前用户。

---

# 37. Knowledge Layer

Skill 的知识与 Example 不同。

```text
Instructions = 怎么做
Knowledge = 是什么
Examples = 类似情况怎么处理
Tools = 确定性能力
```

例如：

```text
荣格概念定义
命理符号解释规则
CBT / ACT 方法定义
```

属于 Knowledge。

而：

```text
某种复杂冲突具体如何分析
```

更适合 Example。

V1 Knowledge 先保持轻量：

- 小型、稳定 Knowledge 可以随 SkillVersion Snapshot 固化；
- 大型 Knowledge 后续再独立 Knowledge Asset / Retrieval 系统；
- V1 不需要先做完整知识管理后台。

---

# 38. Context Model

SkillRuntime 使用统一 Context Envelope 逻辑：

```text
subject
request
facts
observations
confirmed_findings
upstream_outputs
artifacts
runtime
```

来源类型至少区分：

```text
SYSTEM_CALCULATED
USER_PROVIDED
HUMAN_CONFIRMED
AI_GENERATED
EXTERNAL_REFERENCE
```

ContextPolicy 需要支持：

```text
required
optional
forbidden
```

ContextProjection 支持：

```text
FULL
SUMMARY
STRUCTURED_ONLY
SELECT_FIELDS
```

原则：

> 当前 Skill 只拿完成任务所需的最小上下文，而不是把整个 Case 历史全部塞进 Prompt。

---

# 39. PromptAssembler

统一顺序：

```text
GLOBAL POLICY
↓
SKILL IDENTITY
↓
TASK OBJECTIVE
↓
METHODOLOGY
↓
KNOWLEDGE
↓
DYNAMIC EXAMPLES
↓
CURRENT CONTEXT
↓
RUNTIME INSTRUCTION
↓
OUTPUT CONTRACT
```

Runtime Instruction 允许表达本 Case 的临时任务要求，但不得覆盖：

```text
Global Guardrails
Output Schema
Tool Permission
Safety Policy
```

---

# 40. Global AI Policy

至少包含：

```text
不进行医学 / 精神疾病 / 人格障碍诊断
不把传统命理解释表达成科学心理诊断
不写确定性未来
不使用宿命化表达
不从单一信号形成强人格结论
多来源冲突时保留冲突
用户现实经验优先校正模型
不伪造用户经历
不把 Example 用户事实迁移给当前用户
不暴露内部 Chain-of-Thought
```

Global Policy 独立版本化，SkillRun 记录实际版本。

---

# 41. SkillRuntime

统一执行流程：

```text
Load SkillVersion
↓
ContextBuilder
↓
ProcessorRunner
↓
KnowledgeRetriever
↓
ExampleRetriever
↓
PromptAssembler
↓
ModelGateway
↓
OutputParser
↓
SchemaValidator
↓
PostProcessor
↓
GuardrailEngine
↓
SkillOutput
↓
TraceRecorder
↓
Evaluation
```

业务代码不得绕过 SkillExecutor 直接调用具体模型。

---

# 42. ModelGateway

V1 可先接 DeepSeek，但业务层只能依赖 ModelGateway。

ModelGateway 至少记录：

```text
provider
model
input_tokens
output_tokens
latency_ms
estimated_cost
request/response trace
```

后续更换模型时不修改业务 Domain Service。

---

# 43. SkillRun

SkillRun 是 AI 执行审计的核心对象。

run_type：

```text
INITIAL
REGENERATE
REWRITE
VALIDATE
EVALUATION
```

建议目标类型：

```text
STEP
FINDING
FRAGMENT
NARRATIVE_PLAN
REPORT
```

一次 SkillRun 必须能够回答：

```text
用了哪个 SkillVersion
输入是什么
Context 是什么
Examples 是哪些
Knowledge 是哪些
模型是什么
输出是什么
耗时和 Token 是多少
最终是否成功
```

---

# 44. S6 Final QA

Final QA 分三层：

```text
Programmatic QA
        ↓
LLM Semantic QA
        ↓
Human Final Gate
```

原则：

> 程序能确定的问题，不交给 LLM 猜；LLM 能辅助发现的语义问题，不要求人工重新从头检查；最终人工负责交付责任。

---

# 45. Programmatic QA

适合程序检查：

```text
Required Fragment 是否存在
Fragment 是否 STALE
used_findings 是否存在
Finding 是否 CONFIRMED
Finding Revision 是否匹配
NarrativePlan 是否最新
Output Schema 是否合法
Block 是否有 Action
Action 是否有来源
CRITICAL Finding 是否完全未覆盖
同一 Finding 是否大量重复引用
硬编码禁止词 / 临床诊断词
篇幅 / 章节结构异常
```

Programmatic QA 失败时直接返回，不浪费 LLM Token。

---

# 46. LLM Semantic QA

逻辑上检查以下维度：

```text
Fact Fidelity
Semantic Consistency
Safety
Narrative Quality
Action Quality
Personalization
```

V1 可以一个 Validator SkillRun 一次输出多个维度，不要求六次模型调用。

## 46.1 Fact Fidelity

检查：

```text
SUPPORTED
PARTIALLY_SUPPORTED
UNSUPPORTED
CONTRADICTED
```

例如报告写了用户从未提供过的具体经历：

```text
UNSUPPORTED_CONTENT
severity = BLOCK
```

## 46.2 Semantic Consistency

检查：

```text
与 Confirmed Finding 冲突
章节之间自相矛盾
同一 Finding 在不同章节被解释成不同含义
```

## 46.3 Safety

重点：

```text
临床诊断
人格障碍诊断
宿命论
确定性未来
单一命理信号强推人格
命理包装成科学心理事实
绝对化措辞
```

## 46.4 Narrative

检查：

```text
你是谁 / 卡在哪 / 往哪去是否职责清晰
核心暗线是否贯穿
章节是否大量重复
卡点是否过早给完整解决方案
第三部分是否真正回应前面的共性模式
```

## 46.5 Action

检查：

```text
Action 是否回应真实 Block
是否发展目标能力
是否能说明为什么适合当前用户
是否只是泛化建议
```

## 46.6 Personalization

检查：

> 换一个用户名后这段是否仍然基本成立？

重点识别：

```text
GENERIC_CONTENT
```

---

# 47. QA Issue

Validator 不应该只有分数，而必须产生可修复 Issue。

```json
{
  "issue_type": "UNSUPPORTED_CONTENT",
  "severity": "BLOCK",
  "target_fragment": "report.direction.life_stage",
  "evidence": "...",
  "message": "...",
  "suggestion": "REWRITE_FRAGMENT"
}
```

Severity：

```text
BLOCK
WARN
SUGGESTION
```

状态：

```text
OPEN
RESOLVED
ACCEPTED
DISMISSED
```

BLOCK 不允许自动静默修改完整报告。

正确流程：

```text
QA Issue
↓
定位 Fragment
↓
返回 S5
↓
AI 局部 Rewrite / 人工修复
↓
重新 QA
```

---

# 48. Coverage Matrix

Coverage Matrix 不建表，QA 时动态计算。

例如：

| Semantic Asset | 报告使用情况 | 检查结果 |
|---|---|---|
| F018 核心张力 | 3处 | 可能重复 |
| F032 关系循环 | 2处 | 正常 |
| F077 自性方向 | 2处 | 正常 |
| F102 重要资源 | 0处 | 可能遗漏 |

用于发现：

```text
UNDER_COVERAGE
OVER_REPETITION
```

程序先发现候选，再由 LLM 判断语义上是否真的构成问题。

---

# 49. Human Final Gate

最终人工不重新做 S1～S5。

界面应直接展示：

```text
BLOCK = 0
WARN = 3
SUGGESTION = 5

核心主题
关键 Block
高风险内容
未覆盖 Finding
重复风险
```

人工重点判断：

```text
是否真的像这个人
核心叙事是否跑偏
高风险 WARN 是否可接受
整体是否存在明显违和
```

主要动作：

```text
APPROVE
RETURN_TO_AUTHORING
```

---

# 50. ReportAssembler

ReportAssembler 不是 AI 作者。

职责：

```text
读取 Confirmed ReportFragments
↓
按照确定模板排序
↓
应用样式
↓
组装 HTML / Markdown / PDF
↓
冻结 Snapshot
↓
生成 ReportVersion
```

Assembler 不允许：

```text
重新概括
重新分析
整体 AI 改写
新增 Finding
```

---

# 51. ReportVersion

ReportVersion 是最终交付快照，不是日常编辑版本。

生产期历史由：

```text
Finding Revision
Fragment Revision
NarrativePlan Version
```

承担。

通过 Final Gate 后才创建 ReportVersion。

ReportVersion 创建后 Immutable。

修改已交付报告：

```text
ReportVersion 1 DELIVERED
↓
重新进入修订流程
↓
ReportVersion 2 DELIVERED
```

不能覆盖 Version 1。

---

# 52. ReportCase 状态机

Case 只保持粗粒度业务状态：

```text
CREATED
ACTIVE
BLOCKED
READY_TO_DELIVER
DELIVERED
CANCELLED
```

不要使用：

```text
PSYCHOLOGY_REVIEWING
REPORT_WRITING
QA_RUNNING
```

这类细状态。

“当前做到哪一步”应由 StepTask 决定。

---

# 53. WorkflowInstance 状态

```text
CREATED
RUNNING
SUSPENDED
COMPLETED
CANCELLED
```

一次模型失败不意味着 Workflow 失败。

模型/任务错误属于 SkillRun 或 StepTask。

---

# 54. StepTask 状态机

建议：

```text
PENDING
READY
EXECUTING
WAITING_REVIEW
IN_REVIEW
NEEDS_REVISION
COMPLETED
FAILED
CANCELLED
```

HUMAN + AI Step：

```text
PENDING
↓
READY
↓
EXECUTING
↓
WAITING_REVIEW
↓
IN_REVIEW
↓
COMPLETED
```

返工：

```text
COMPLETED
↓
NEEDS_REVISION
↓
IN_REVIEW
↓
COMPLETED
```

RETURN / REOPEN 是 Command，不是长期 Status。

---

# 55. Fragment 状态

建议：

```text
DRAFT
READY_FOR_REVIEW
CONFIRMED
STALE
RETIRED
```

StepTask.status 与 Fragment.status 必须独立。

一个 Step 在 `IN_REVIEW` 时，可以同时存在：

```text
Fragment A CONFIRMED
Fragment B READY_FOR_REVIEW
Fragment C DRAFT
```

Step 完成由 CompletionGate 判定。

---

# 56. NarrativePlan 状态

```text
DRAFT
CONFIRMED
STALE
SUPERSEDED
```

Narrative Candidate 不需要生命周期。

---

# 57. Stale 传播规则

必须冻结以下规则：

```text
① Finding Semantic Revision 改变
→ 依赖 AnalysisFragment STALE
```

```text
② Analysis Semantic 改变
→ 下游 AnalysisFragment / NarrativePlan / ReportFragment 按依赖 STALE
```

```text
③ NarrativePlan 改变
→ 相关 ReportFragment STALE
→ Analysis Space 不受影响
```

```text
④ QA BLOCK
→ 对应 ReportFragment 返工
→ S5 NEEDS_REVISION
→ S6 暂停
```

```text
⑤ Delivered ReportVersion 永远不被后续修订覆盖
```

V1 使用：

```text
StalePropagationService
```

扫描当前 Case 的 Source Snapshot 即可，不需要图数据库或复杂 Dependency Engine。

---

# 58. CompletionGate

V1 不设计复杂条件 DSL。

WorkflowDefinition 只配置：

```json
{
  "completion_policy": "PSYCHOLOGY_REVIEW"
}
```

代码中通过：

```text
CompletionPolicyRegistry
```

解析。

例如 S2 完成条件：

```text
Required Findings 已处理
High-risk Finding 已显式确认
Required AnalysisFragments = CONFIRMED
没有 unresolved conflict
没有 STALE
没有 BLOCK Guardrail
人工点击完成
```

---

# 59. Consultant Workbench

原则：

> 底层严格结构化，前台尽量像正常审稿。

推荐布局：

```text
┌───────────────┬──────────────────────┬───────────────┐
│ Context       │ 分析 / 报告正文       │ 核心判断       │
│               │                      │               │
│ 用户问卷       │ AI Draft             │ Finding        │
│ 上游确认结果   │ 人工编辑             │ Confidence     │
│ 程序事实       │                      │ Evidence       │
│ 冲突提醒       │                      │ Risk           │
└───────────────┴──────────────────────┴───────────────┘
```

常用 AI 操作：

```text
重新生成
重新表达
降低确定性
补充替代解释
冲突检查
一致性检查
压缩
扩写
```

咨询师不直接操作数据库结构。

---

# 60. Skill Studio

面向：

```text
Skill Owner
高级咨询师
AI / 产品负责人
```

支持：

```text
Overview
Instructions
Knowledge
Examples
Context Policy
Tools / Processors
Output Schema
Guardrails
Evaluation
Runs
Issues
Versions
```

Published SkillVersion 不允许原地修改。

调试运行不能创建正式 StepOutput。

---

# 61. Evaluation

## 61.1 Skill Evaluation

重点：

```text
Schema Validity
Faithfulness
Coverage
Over-inference
Consistency
Safety
Expression
Human Edit Ratio
Finding Acceptance Rate
Finding Modification Rate
Finding Rejection Rate
Human Added Finding Rate
```

辰鉴最重要的指标不是单纯“写得好不好”，而是：

```text
Over-inference
Consistency
Safety
Human Semantic Correction
```

## 61.2 Workflow Evaluation

```text
Step 平均耗时
人工处理时间
AI Regenerate 次数
Return / Reopen 次数
STALE 次数
节点等待时间
总交付时间
异常率
```

## 61.3 Validator Evaluation

记录：

```text
False Positive
False Negative
Human Override Rate
Block Precision
Block Recall
```

---

# 62. Regression 与 Experiment

真实生产问题：

```text
Issue
↓
Fix
↓
Regression Case
```

V1 Regression 数据先文件化：

```text
tests/
  skill_regression/
    psychology_mapping/
      case_001.json
```

Experiment 一次尽量只改变一个主要变量：

```text
Skill Version
Example Snapshot
Knowledge Snapshot
Model
```

不要同时全改，否则无法判断效果来源。

---

# 63. 问题定位方法

遇到 AI 质量问题时统一判断：

```text
不知道“怎么做”
→ Instructions

不知道“是什么”
→ Knowledge

知道规则但不会处理“这种情况”
→ Example

本来就不该靠生成解决
→ Tool / Processor

输入 / 顺序 / 责任 / 节点设计不合理
→ Workflow / Context
```

不要看到 AI 输出不好就只改 Prompt。

---

# 64. V1 最终物理数据模型

V1 核心表冻结为 14 张。

| # | 表 | 作用 |
|---:|---|---|
| 1 | `report_cases` | 一次人生说明书生产 Case |
| 2 | `workflow_versions` | Workflow 配置与版本 |
| 3 | `workflow_instances` | Workflow 运行实例 |
| 4 | `step_tasks` | 每个业务节点运行状态 |
| 5 | `workflow_outbox` | 可靠异步事件 |
| 6 | `case_evidence_items` | 用户事实 / 工具事实 |
| 7 | `finding_revisions` | Signal / Finding + 历史版本 |
| 8 | `content_fragment_revisions` | Analysis / Report Fragment + 历史版本 |
| 9 | `narrative_plans` | 最终报告叙事方案 |
| 10 | `qa_issues` | QA 问题与处理 |
| 11 | `report_versions` | 最终不可变交付快照 |
| 12 | `ai_skill_versions` | Skill 定义与版本 |
| 13 | `skill_runs` | AI 执行与 Trace |
| 14 | `skill_examples` | Dynamic Few-shot Example Library |

这 14 张表是 V1 开发基线。

如果现有 InnerPath 已经存在等价结构，应优先映射/复用，而不是为了名字一致强制重建。

---

# 65. 表结构建议

## 65.1 `report_cases`

```text
id
user_id
status
application_snapshot JSONB
application_submitted_at
workflow_instance_id
current_narrative_plan_id
created_at
delivered_at
cancelled_at
```

V1 将 ReportApplication 逻辑合并进 Case。

---

## 65.2 `workflow_versions`

```text
id
workflow_key
name
version
status
definition_json JSONB
created_by
published_by
created_at
published_at
```

约束：

```text
UNIQUE(workflow_key, version)
```

---

## 65.3 `workflow_instances`

```text
id
report_case_id
workflow_version_id
status
started_at
completed_at
suspended_at
```

---

## 65.4 `step_tasks`

```text
id
workflow_instance_id
step_key
sequence_no
executor
status
required_capability
assignee_id
activation_no
config_snapshot JSONB
result_json JSONB
activated_at
started_at
completed_at
retry_count
last_error
```

约束：

```text
UNIQUE(workflow_instance_id, step_key)
```

Reopen 使用 `activation_no + 1`，不新建 StepTask。

---

## 65.5 `workflow_outbox`

```text
id
aggregate_type
aggregate_id
event_type
payload_json JSONB
status
retry_count
created_at
published_at
```

用于保证：

```text
数据库事务
↓
异步任务
```

之间可靠一致。

---

## 65.6 `case_evidence_items`

```text
id
report_case_id
evidence_key
source_type
source_ref
value_json JSONB
status
created_at
```

---

## 65.7 `finding_revisions`

V1 使用单表 Revision 模型。

```text
id
report_case_id
finding_key
revision_no
is_current
kind
semantic_role
status
claim
confidence
importance
reportability
structured_data JSONB
evidence_refs JSONB
relation_refs JSONB
source_step_task_id
source_skill_run_id
revision_type
created_by_type
created_by_id
created_at
```

约束：

```text
UNIQUE(report_case_id, finding_key, revision_no)
```

同一个 Case + FindingKey 只能有一个 `is_current = true`。

---

## 65.8 `content_fragment_revisions`

V1 同样使用 Revision 单表模型。

```text
id
report_case_id
space
fragment_key
fragment_type
revision_no
is_current
semantic_revision
content_revision
status
stale_reason
structured_data JSONB
content_json JSONB
source_snapshot JSONB
owner_step_task_id
source_skill_run_id
source_narrative_plan_id
revision_type
created_by_type
created_by_id
created_at
```

其中：

```text
space = ANALYSIS | REPORT
```

约束：

```text
UNIQUE(report_case_id, fragment_key, revision_no)
```

---

## 65.9 `narrative_plans`

```text
id
report_case_id
version_no
is_current
status
selected_skill_run_id
selected_candidate_key
plan_json JSONB
source_snapshot JSONB
created_by
confirmed_by
created_at
confirmed_at
```

---

## 65.10 `qa_issues`

```text
id
report_case_id
source_type
source_ref_id
issue_type
severity
status
target_fragment_key
target_fragment_revision_id
message
evidence_json JSONB
suggestion
resolution
resolved_by
resolved_at
created_at
```

---

## 65.11 `report_versions`

```text
id
report_case_id
version_no
workflow_version_id
narrative_plan_id
fragment_snapshot JSONB
semantic_snapshot JSONB
structured_data JSONB
rendered_html
pdf_url
created_at
delivered_at
```

约束：

```text
UNIQUE(report_case_id, version_no)
```

---

## 65.12 `ai_skill_versions`

```text
id
skill_key
name
category
version
status
specification_json JSONB
created_by
published_by
created_at
published_at
```

约束：

```text
UNIQUE(skill_key, version)
```

category：

```text
ANALYSIS
ACTION
AUTHORING
VALIDATOR
```

---

## 65.13 `skill_runs`

```text
id
skill_version_id
report_case_id
workflow_instance_id
step_task_id
target_type
target_key
run_type
status
idempotency_key
runtime_instruction
input_snapshot JSONB
context_snapshot JSONB
output_raw
output_parsed JSONB
selected_examples JSONB
selected_knowledge JSONB
model_trace JSONB
started_at
completed_at
```

约束：

```text
UNIQUE(idempotency_key)
```

---

## 65.14 `skill_examples`

```text
id
skill_key
target_fragment_key
example_key
version_no
status
example_type
scenario_tags JSONB
applicability_json JSONB
input_context JSONB
expected_output JSONB
teaching_points JSONB
anti_patterns JSONB
quality_score
source_case_id
deidentified
created_by
reviewed_by
created_at
published_at
```

---

# 66. V1 不建表的概念

下列概念只是 Service / Projection / Runtime Object：

| 概念 | V1 形式 |
|---|---|
| ContextEnvelope | Runtime Object |
| ContextProjection | Skill 配置 + Runtime |
| CaseSemanticModel | Runtime Projection |
| NarrativeCandidate | SkillRun Output |
| CoverageMatrix | QA 动态计算 |
| CompletionGate | Domain Service |
| PromptAssembler Result | SkillRun Trace |
| ToolRegistry | Code Registry |
| ProcessorRegistry | Code Registry |
| ReportAssembler | Domain Service |
| Workflow Engine | Domain Service |
| SkillExecutor | Domain Service |
| DependencyGraph | Runtime 扫描 / Service |

Codex 不应因为文档中出现一个名词，就机械创建一个 Entity / Table。

---

# 67. JSONB 使用原则

适合 JSONB：

```text
用户问卷 Snapshot
Workflow Definition
Step Config Snapshot
Skill Specification
Evidence Value
Finding Structured Data
Finding Evidence Refs
Finding Relation Refs
Fragment Structured Data
Fragment Content
Fragment Source Snapshot
NarrativePlan
Skill Input / Context / Output
QA Evidence / Metrics
Report Snapshot
```

不应该埋进 JSONB 的高频状态：

```text
Step Status
Finding Status
Fragment Status
semantic_revision
content_revision
QA Severity
QA Status
Case Status
```

原则：

> 需要高频过滤、状态判断、唯一性约束的数据用正常列；复杂但低频变化的结构内容使用 JSONB。

---

# 68. 关键索引

优先：

```text
step_tasks(workflow_instance_id, status)

finding_revisions(report_case_id, is_current, status, semantic_role)

content_fragment_revisions(report_case_id, is_current, space, status)

qa_issues(report_case_id, status, severity)

skill_runs(step_task_id, status)

skill_examples(skill_key, status)
```

不要第一期给所有 JSONB 都加 GIN。

有明确查询需求后再加。

---

# 69. 事务边界

## 69.1 Finding Semantic Edit

```text
BEGIN

插入 Finding Revision
↓
旧 Revision is_current = false
↓
新 Revision is_current = true
↓
触发 StalePropagationService
↓
写 Outbox Event

COMMIT
```

异步任务必须在事务提交后由 Outbox 驱动。

## 69.2 Step Complete

```text
BEGIN

CompletionGate 校验
↓
StepTask = COMPLETED
↓
激活 Next StepTask
↓
写 Outbox Event

COMMIT
```

随后：

```text
Outbox Dispatcher
↓
StepActivated Event
↓
如果 generate_on_activate
↓
启动 SkillRun
```

---

# 70. 幂等

至少以下任务必须具备幂等键：

```text
Step Activation
AI Initial Draft
Fragment Regenerate
QA Run
Report Assembly
```

推荐：

```text
step:{step_task_id}:initial:{activation_no}
```

以及：

```text
fragment:{fragment_key}:rewrite:{semantic_revision}:{request_id}
```

Celery 只能作为执行器。

数据库始终是 Source of Truth。

---

# 71. 后端模块建议

不要按一张表建一个 Module。

推荐：

```text
app/

  cases/
    report_case

  workflow/
    definition
    runtime
    completion
    outbox

  content/
    evidence
    findings
    fragments
    stale

  authoring/
    narrative
    reporting

  skills/
    registry
    runtime
    examples
    model_gateway

  quality/
    guardrails
    qa

  delivery/
    report_version
    renderer

  calendar/
```

如果现有项目已经有合理模块，不要求完全照此重排。

目标是依赖方向清晰，而不是目录名一致。

---

# 72. 服务职责建议

核心 Domain Service：

```text
WorkflowEngine
StepCompletionService
StalePropagationService
CaseSemanticModelBuilder
NarrativePlanningService
ReportAuthoringService
ProgrammaticQAService
ReportAssembler
```

核心 Skill Runtime Service：

```text
SkillRegistry
SkillExecutor
ContextBuilder
KnowledgeRetriever
ExampleRetriever
PromptAssembler
ModelGateway
OutputValidator
GuardrailEngine
TraceRecorder
```

V1 不需要“万能 Agent Orchestrator”。

---

# 73. Capability / 权限模型

Workflow Step 不直接绑定具体角色，而绑定 Capability。

例如：

```text
REPORT_CASE_VIEW
METAPHYSICS_REVIEW
PSYCHOLOGY_REVIEW
INTEGRATION_REVIEW
REPORT_EDITORIAL_REVIEW
FINAL_QA_APPROVE
SKILL_EDIT
SKILL_PUBLISH
EXAMPLE_RECOMMEND
EXAMPLE_PUBLISH
```

角色只是 Capability 集合。

这样未来：

```text
CONSULTANT_A
CONSULTANT_B
SENIOR_CONSULTANT
ADMIN
```

可以复用同一 Workflow。

---

# 74. 上下游可见性

咨询师默认可见：

```text
当前 Step 所需用户资料
上游 Confirmed Findings
上游 Confirmed Fragments
必要 Evidence
冲突提示
```

默认不可见：

```text
其他咨询师内部 AI 对话
废弃 Draft
Rejected Finding 的完整生产过程
与当前任务无关的内部备注
```

原则：

> 下游看上游“确认结果”，不看上游“全部生产过程”。

---

# 75. V1 必须实现

V1 必须包含：

- WorkflowVersion；
- SYSTEM / HUMAN Step；
- activation 后 AI 自动 Draft；
- StepTask 状态机；
- Return / Reopen；
- Transactional Outbox；
- SkillVersion；
- SkillExecutor；
- Global Policy；
- ContextBuilder；
- Tool / Processor Registry；
- Evidence；
- Finding Revision；
- Finding-first / Structure-first；
- AnalysisFragment / ReportFragment；
- Semantic / Content Revision；
- Source Snapshot；
- STALE Propagation；
- Consultant Workbench；
- CaseSemanticModelBuilder；
- Narrative Candidate；
- Human Editorial Choice；
- NarrativePlan；
- Report Authoring；
- Programmatic QA；
- LLM Validator；
- Human Final Gate；
- QAIssue；
- Immutable ReportVersion；
- Dynamic Few-shot；
- Example Library；
- 基础 Skill Evaluation；
- 文件化 Regression Dataset；
- 下游 Calendar Workflow 基础接口。

---

# 76. V1 明确暂缓

第一期不要实现：

- BPMN；
- 拖拽 Workflow Editor；
- 并行 Workflow；
- 复杂条件 DSL；
- 多人同时审批；
- 自动负载均衡；
- 自动咨询师调度；
- 图数据库；
- MCP；
- Sub-Agent；
- 大规模 Agent Planning；
- 任意 Shell / Python 执行；
- 模型自由 Function Calling；
- 完整 Knowledge 管理平台；
- 完整在线 Evaluation 平台；
- Shadow / A-B 自动发布；
- 自动 Skill 发布；
- 通用 Artifact 抽象；
- 复杂 Block-level 富文本引擎。

---

# 77. Codex 开发前置流程

拿到本文后，Codex **不要立即重构代码**。

第一阶段必须先输出《现有代码与目标架构差距分析》，至少回答：

```text
1. 当前 Report / Case 数据模型是什么？
2. 当前 Workflow / 状态流转在哪里实现？
3. 当前 AI Prompt / 模型调用在哪里？
4. 当前报告草稿与最终版本如何存储？
5. 当前是否已经存在 Revision / History？
6. 当前异步任务如何实现？
7. 当前权限 / Capability 如何实现？
8. 当前数据库有哪些表可以复用？
9. 目标 14 张表中哪些已经有等价表？
10. 哪些模块可以保留？
11. 哪些模块需要重构？
12. 哪些新增功能可增量接入而无需重写？
```

完成差距分析后再输出落地方案。

---

# 78. Codex 落地原则

Codex 实现时必须遵守：

## 78.1 优先增量改造

不要因为目标设计中的名称不同，就删除现有合理代码重写。

判断标准：

```text
语义是否等价？
职责是否合理？
版本/追溯能力是否满足？
依赖方向是否可接受？
```

如果满足，优先复用。

## 78.2 不提前过度抽象

禁止为了“未来通用”创建：

```text
Artifact
SemanticUnit
AIResource
ExecutionNode
BusinessObject
ContentNode
```

这类万能实体，除非现有代码已经证明有真实需求。

当前业务语言已经足够：

```text
Case
Step
Finding
Fragment
NarrativePlan
QAIssue
ReportVersion
Skill
Example
```

## 78.3 不破坏版本不可变原则

Published：

```text
WorkflowVersion
SkillVersion
```

不可原地修改。

Delivered：

```text
ReportVersion
```

不可覆盖。

## 78.4 不让 AI 承担确定性逻辑

例如：

```text
排盘
Schema 校验
Revision 比较
STALE 判断
Required Fragment 检查
Report Assembly
```

优先程序实现。

## 78.5 不把 Skill 简化成 Prompt 表

Skill 必须保留：

```text
Context
Knowledge
Examples
Tools
Output Contract
Guardrails
Evaluation
```

等语义。

---

# 79. 推荐实施顺序

不要同时重构所有东西。

## Phase 1：Workflow 与 Version 基座

完成：

```text
report_cases
workflow_versions
workflow_instances
step_tasks
workflow_outbox
```

以及：

```text
WorkflowEngine
Step Activation
CompletionGate
Return / Reopen
```

验收：

> 不接 AI，也能完整跑通一个纯人工 Sequential Workflow。

## Phase 2：Skill Runtime

完成：

```text
ai_skill_versions
skill_runs
SkillExecutor
ContextBuilder
PromptAssembler
ModelGateway
```

验收：

> 一个 Step 激活后，可以通过固定 SkillVersion 自动生成结构化输出，并可完整追踪。

## Phase 3：Evidence / Finding / Fragment

完成：

```text
case_evidence_items
finding_revisions
content_fragment_revisions
```

以及：

```text
Finding-first
Semantic Edit
Style Edit
StalePropagation
```

验收：

> 修改上游 Semantic Finding 后，真正依赖它的下游 Fragment 会 STALE；纯文字修改不会传播。

## Phase 4：Consultant Workbench

完成：

```text
AI Draft
Finding 接受/修改/拒绝/新增
Evidence 查看
Fragment 编辑
Complete Step
```

验收：

> 咨询师无需理解底层 JSON，也能完成完整专业审核。

## Phase 5：Narrative / Report Authoring

完成：

```text
CaseSemanticModelBuilder
Narrative Planner
Narrative Candidate
Human Choice
NarrativePlan
ReportFragment Authoring
```

验收：

> 前四步完成后，系统不依赖“四篇长文重新阅读”，可以基于 Confirmed Semantic Assets 形成个性化报告。

## Phase 6：Final QA / Delivery

完成：

```text
Programmatic QA
Validator Skill
qa_issues
Human Final Gate
ReportAssembler
report_versions
```

验收：

> 存在 BLOCK 时绝不交付；通过后产生不可变 ReportVersion。

## Phase 7：Dynamic Few-shot / Evaluation

完成：

```text
skill_examples
Example Candidate
Example Publish
Dynamic Retrieval
基础 Evaluation
Regression Dataset
```

验收：

> 咨询师优质人工修改可以变成审核后的 Example，新 SkillRun 可动态检索并记录使用来源。

---

# 80. V1 最终端到端验收场景

至少需要覆盖以下场景。

## 场景 A：正常生成

```text
用户提交
↓
S0 Evidence
↓
S1～S4 AI Draft + 人工确认
↓
Case Semantic Model
↓
Narrative Candidates
↓
人工选定 NarrativePlan
↓
ReportFragments
↓
Final QA PASS
↓
ReportVersion DELIVERED
```

## 场景 B：Finding 被人工修改

```text
AI Finding v1
↓
Human Semantic Edit
↓
Finding v2
↓
相关 Fragment STALE
↓
重新确认
```

## 场景 C：仅修改文风

```text
Fragment content_revision + 1
semantic_revision 不变
↓
下游不 STALE
```

## 场景 D：上游返工

```text
S4 发现 S2 判断有问题
↓
RETURN_TO_STEP(S2)
↓
S2 NEEDS_REVISION
↓
修改后重新完成
↓
下游按真实依赖 STALE
```

## 场景 E：NarrativePlan 改变

```text
Plan v1
↓
改为 Plan v2
↓
ReportFragments NARRATIVE_CHANGED
↓
Analysis Space 不变
```

## 场景 F：QA BLOCK

```text
Validator 发现确定性未来表达
↓
QAIssue BLOCK
↓
对应 ReportFragment 返工
↓
S5 NEEDS_REVISION
↓
重新 QA
↓
PASS
```

## 场景 G：历史可复现

对任意已交付 ReportVersion 能查到：

```text
WorkflowVersion
NarrativePlan Version
ReportFragment Revisions
Finding Revisions
SkillVersions
SkillRuns
Examples
Model Trace
```

---

# 81. 核心架构不变量

后续无论代码如何落地，都应保持以下不变量：

```text
1. Workflow 决定顺序，Skill 决定 AI 如何做。
2. Step 不等于人工审核，AI Assistance 与 Executor 正交。
3. Published WorkflowVersion / SkillVersion 不可变。
4. Case 绑定确定 WorkflowVersion，不自动迁移。
5. Evidence 与 AI 推论必须区分。
6. AI Generated Finding 未经确认不能成为下游强事实。
7. Step 1 心理内容优先作为 Signal。
8. 前四步的核心产物是 Semantic Assets，不是长文档。
9. Finding 是核心最小专业判断单位。
10. Analysis Space 与 Report Space 分离。
11. Report Authoring 不允许创建新专业 Finding。
12. ReportFragment 必须可追溯上游 Semantic Revision。
13. Semantic Edit 会传播 STALE，Style Edit 不传播。
14. 人工成果不得被上游变化自动覆盖。
15. NarrativePlan 只改变叙事，不改变专业事实。
16. Final QA 不负责静默改写报告。
17. ReportAssembler 只做确定性组装。
18. Delivered ReportVersion 永远不可覆盖。
19. Dynamic Few-shot 与生产案例库隔离。
20. AI 质量问题必须能定位到 Workflow / Context / Instruction / Knowledge / Example / Tool。
```

---

# 82. 最终架构总图

```text
┌──────────────────────────────┐
│        ReportCase            │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│       WorkflowInstance       │
│ WorkflowVersion pinned       │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│          StepTask            │
│ SYSTEM / HUMAN               │
│ required_capability          │
└──────────────┬───────────────┘
               │
        ┌──────┴────────┐
        ▼               ▼
 Deterministic       SkillRun
 Processor              │
        │                ▼
        │         SkillVersion
        │                │
        │       Context / Knowledge
        │       Examples / Guardrails
        │                │
        └────────┬───────┘
                 ▼
              Evidence
                 │
                 ▼
              Finding
                 │
                 ▼
        AnalysisFragment
                 │
          Human Confirm
                 │
                 ▼
       Case Semantic Model
                 │
                 ▼
       Narrative Candidates
                 │
         Human Editorial
                 │
                 ▼
          NarrativePlan
                 │
                 ▼
          ReportFragments
                 │
                 ▼
       Programmatic QA
                 │
                 ▼
        LLM Semantic QA
                 │
                 ▼
        Human Final Gate
                 │
                 ▼
         ReportAssembler
                 │
                 ▼
          ReportVersion
                 │
              DELIVER
```

---

# 83. Codex 最终任务说明

将本文交给 Codex 后，建议明确要求：

```text
第一阶段不要修改代码。

请先扫描当前项目并基于《辰鉴 AI 内容生产工作流与 Skills 架构设计 v1.0》输出：

1. 当前架构与目标架构映射；
2. 可直接复用模块；
3. 需要增量改造模块；
4. 必须新增的数据模型；
5. 现有数据库表与目标 14 张表的对应关系；
6. Migration 方案；
7. Backend / Frontend 改造范围；
8. 按 Phase 1～7 的实施任务；
9. 每个 Phase 的验收测试；
10. 风险与兼容性问题。

未经确认，不要一次性大规模重构现有代码。
```

后续所有代码实现都应以本文的“核心架构不变量”为判断基准。

---

# 84. 最终结论

辰鉴 V1 的核心不是构建一个复杂 Agent 平台，而是构建一套：

> **结构化专业分析 + 人工语义校准 + 可追踪 AI 写作 + 独立质量控制 + 持续经验学习**

的内容生产基础设施。

最终生产范式是：

```text
Evidence
↓
AI Candidate Semantic
↓
Human Confirmed Semantic
↓
Narrative Planning
↓
AI Authoring
↓
Human Editorial Review
↓
Independent QA
↓
Immutable Delivery
↓
Feedback / Example / Evaluation
↓
下一版本能力提升
```

这套架构既保留专业咨询师的判断价值，又让 AI 承担大量分析、组织、写作和校验工作；同时通过 Version、Revision、Source Snapshot、STALE、SkillRun、Example Library 和 QA Issue，使系统能够长期演进，而不是随着 Prompt 越堆越多逐渐失控。

**v1.0 至此作为 Codex 开发目标架构基线冻结。**
