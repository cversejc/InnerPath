import { reportFragmentTitle } from "../report-cases/stages.js";
// Presentation labels never change the stable keys sent to the skill runtime.
export const REPORT_SKILLS = [
  {
    key: "report.s1_foundation_analysis",
    step: "S1",
    name: "命理基础分析",
    node: "命理基础",
    input: "本次出生资料、用户情境和程序测算结果",
    output: "命理结构判断、内部分析和待验证线索",
    task: "核对测算依据，审核每条候选判断。",
  },
  {
    key: "report.s2_psychology_mapping",
    step: "S2",
    name: "心理映射分析",
    node: "心理映射",
    input: "用户自述、已确认的命理判断和资料依据",
    output: "心理运作模式假设与待核对问题",
    task: "回到用户原文核对假设，保留反证和不确定性。",
  },
  {
    key: "report.s3_integration",
    step: "S3",
    name: "命理、心理与哲学整合",
    node: "三重整合",
    input: "前序已确认的判断和分析",
    output: "中心张力、人生方向和整合任务候选",
    task: "选择贴合用户的整合方向，处理前序分歧。",
  },
  {
    key: "report.s4_mechanism_block_action",
    step: "S4",
    name: "机制、卡点与行动分析",
    node: "机制与行动",
    input: "前序已确认内容及用户现实困扰",
    output: "保护机制、关键卡点和成长实验",
    task: "确认卡点与行动相互对应，动作具体且可复盘。",
  },
  {
    key: "report.narrative_plan",
    step: "S5",
    name: "报告主线与编排",
    node: "报告写作",
    input: "咨询师已确认的专业判断、分析和行动",
    output: "报告主线候选及逐段内容安排",
    task: "选择并确认主线，再核对每段使用的依据。",
  },
  {
    key: "report.fragment_authoring",
    step: "S5",
    name: "报告逐段写作",
    node: "报告写作",
    input: "已确认主线、当前段落安排与指定依据",
    output: "单段报告正文及来源记录",
    task: "逐段核对事实、含义和表达，修改后确认。",
  },
  {
    key: "report.final_validator",
    step: "S6",
    name: "报告交付质量检查",
    node: "交付前检查",
    input: "已组装报告、已确认依据和用户情境",
    output: "七维评分和可定位的质量问题",
    task: "处理问题、通读最终稿，再完成交付确认。",
  },
];

export const CALENDAR_SKILLS = [
  { key: 'calendar.temporal_analysis', name: '30天时序分析', node: '日历分析', input: '已审核命盘、报告、问卷与逐日历法', output: '每日心理主题、权重依据与换气口', task: '检查来源引用与缺失资料边界。' },
  { key: 'calendar.monthly_tone', name: '30天总基调', node: '日历基调', input: '报告与30天时序分析', output: '成长任务、资源、旧模式和决定原则', task: '核对月度方向是否承接报告。' },
  { key: 'calendar.daily_authoring', name: '逐日决策文案', node: '日历文案', input: '每日分析、月基调与本次目标', output: '关键词、具体行动、觉察问题与时段建议', task: '维护有针对性且可执行的表达。' },
  { key: 'calendar.calibration', name: '30天整体校准', node: '日历校准', input: '完整30天日历及分析依据', output: '重复、节奏和一致性问题及修订', task: '严重问题未解决时阻止发布。' }
]

export const ALL_SKILLS = [...REPORT_SKILLS, ...CALENDAR_SKILLS];
export const CALENDAR_SKILL_KEYS = new Set(CALENDAR_SKILLS.map((item) => item.key));
export const REASONING_GUIDANCE_SKILL_KEYS = new Set(
  ALL_SKILLS.map((item) => item.key),
);

export function skillInfo(key, fallback = "") {
  return (
    ALL_SKILLS.find((item) => item.key === key) || {
      key,
      step: "",
      name: /[\u4e00-\u9fff]/.test(fallback)
        ? fallback
        : key === "report.generate"
          ? "完整报告草稿生成"
          : "其他技能",
      node: "其他工具",
      input: "技能配置中指定的资料",
      output: "由技能配置确定",
      task: "审核输出后再用于报告。",
    }
  );
}

export function buildSkillCatalog(versions = []) {
  const catalog = ALL_SKILLS.map((item) => ({ ...item }));
  for (const version of versions) {
    if (version.skill_key === "report.generate") continue;
    if (!catalog.some((item) => item.key === version.skill_key))
      catalog.push(skillInfo(version.skill_key, version.name));
  }
  return catalog;
}

export function runSkillKey(run) {
  if (run.target_type === 'CALENDAR_PRODUCTION') return run.context_snapshot?.skill_key || run.model_trace?.skill_key || ''
  const step =
    run.context_snapshot?.analysis_context?.step_key ||
    (/^S[1-4]$/.test(run.target_key || "") ? run.target_key : "");
  if (step) return REPORT_SKILLS.find((item) => item.step === step)?.key || "";
  return (
    {
      REPORT_NARRATIVE_CANDIDATES: "report.narrative_plan",
      NARRATIVE_CANDIDATES: "report.narrative_plan",
      REPORT_FRAGMENT: "report.fragment_authoring",
      REPORT_VALIDATION: "report.final_validator",
      REPORT_QA: "report.final_validator",
    }[run.target_type] ||
    (run.target_type?.includes("NARRATIVE")
      ? "report.narrative_plan"
      : run.target_type?.includes("VALIDAT")
        ? "report.final_validator"
        : run.target_type?.includes("FRAGMENT")
          ? "report.fragment_authoring"
          : "")
  );
}

const LABELS = {
  identity: "技能信息",
  name: "名称",
  description: "说明",
  instructions: "工作要求",
  objective: "目标",
  methodology: "分析方法",
  profile: "用户档案",
  context: "本次情境",
  subject: "用户情况",
  request: "本次需求",
  foundation_data: "程序测算结果",
  analysis_context: "节点分析资料",
  current_challenge: "当前困扰",
  expected_outcomes: "期待结果",
  additional_info: "补充说明",
  focus_topics: "关注主题",
  findings: "专业判断",
  claim: "判断内容",
  category: "判断类别",
  confidence: "把握程度",
  importance: "重要程度",
  fragments: "分析内容",
  analysis_fragments: "分析内容",
  title: "标题",
  content: "正文",
  body: "内容",
  risks: "风险提示",
  message: "问题说明",
  candidates: "主线候选",
  theme: "核心主题",
  rationale: "选择理由",
  priority_blocks: "重点卡点",
  narrative_arc: "叙事顺序",
  core_theme: "核心主线",
  self_direction: "人生方向",
  content_plan: "逐段内容安排",
  purpose: "本段目标",
  chapter: "所属章节",
  issues: "检查问题",
  issue_type: "问题类型",
  severity: "严重程度",
  evidence: "核对依据",
  suggestion: "处理建议",
  scorecard: "质量评分",
  dimensions: "评分维度",
  score: "得分",
  reason: "原因",
  status: "状态",
  action: "建议行动",
  trigger: "触发情境",
  steps: "操作步骤",
  frequency: "频率",
  duration: "耗时",
  observation: "观察内容",
  exit_condition: "退出条件",
  mechanism: "运作机制",
  protective_function: "保护功能",
  long_term_cost: "长期代价",
  integration_invitation: "整合邀请",
  teaching_points: "示例要点",
  anti_patterns: "需要避免",
  input_context: "输入情境",
  expected_output: "参考输出",
  applicability_json: "适用条件",
  professional_role: "专业角色",
  presentation_role: "报告用途",
  must_cover: "需要覆盖",
  must_not_repeat: "避免重复",
  new_information_role: "本段作用",
  scenario_tags: "情境标签",
  required: "必需资料",
  optional: "可选资料",
  forbidden: "禁止使用",
  fields: "可用字段",
  field: "字段",
  value: "内容",
  text: "文字",
  note: "说明",
  summary: "摘要",
  time_horizon: "时间范围",
  uncertainty: "不确定性",
  personality_keywords: "性格关键词",
  strengths: "优势",
  limitations: "限制",
  occupation_status: "职业情况",
  mbti: "自报性格类型",
  female: "女",
  male: "男",
  solar: "公历",
  lunar: "农历",
  exact: "精确时间",
  career: "职业",
  growth: "成长",
  relationship: "关系",
  "decision-making": "决策",
  decision: "决策",
  POSITIVE: "正向示例",
  CONTRASTIVE: "对照示例",
  MISSED_INSIGHT: "补充洞察",
  CONFIRMED: "已确认",
  PROPOSED: "待审核",
  PUBLISHED: "已发布",
  DRAFT: "草稿",
  COMPLETED: "已完成",
  BLOCK: "必须处理",
  MAJOR: "重要问题",
  MINOR: "提示",
  quality: "质量",
  facts: "事实",
  safety: "安全",
  action_value: "行动价值",
  case_fidelity: "案例事实忠实度",
  personalization: "个性化",
  reading_experience: "阅读体验",
  uncertainty_safety: "不确定性与安全",
  psychological_logic: "心理逻辑",
  narrative_coherence: "三章连贯性",
  known: "已知情况",
  missing: "待补充内容",
  interpretation: "解释线索",
  confirmed: "已确认内容",
  confirmed_block: "已确认卡点",
  tension: "中心张力",
  direction: "整合方向",
  metaphor: "哲学意象",
  phase: "发展阶段",
  cycle: "互动循环",
  shadow: "被压下的需要",
  counter_question: "反证问题",
  method: "使用方法",
  duration_minutes: "耗时（分钟）",
  stop_rule: "暂停条件",
  arc: "叙事顺序",
  self_report: "用户自述",
  weekly: "每周",
  daily: "每天",
  report_fragments: "报告正文",
  confirmed_analysis: "已确认分析",
  profile_fields: "用户档案字段",
  context_fields: "情境字段",
  basic_info: "基本信息",
  energy_profile: "能量结构",
  career_guidance: "职业方向",
  relationship_pattern: "关系模式",
  personal_growth: "成长方向",
  ai_generated_content: "生成内容",
  risk_flags: "风险提示",
  structured_data: "补充分析",
  kind: "内容类型",
  semantic_role: "专业用途",
  reportability: "报告呈现程度",
  FINDING: "专业判断",
  SIGNAL: "待验证线索",
  LOW: "较低",
  MEDIUM: "一般",
  HIGH: "较高",
  CRITICAL: "优先处理",
  INTERNAL_ONLY: "仅供内部参考",
  OPTIONAL: "可酌情呈现",
  RECOMMENDED: "建议呈现",
  MUST_INCLUDE: "报告需要包含",
  PROFESSIONAL_OBSERVATION: "综合观察",
  OBSERVATION: "综合观察",
  STRENGTH: "优势",
  RISK: "需要留意",
  TENSION: "内在张力",
  PATTERN: "行为模式",
  CORE_THEME: "核心主题",
  ACTION_DIRECTION: "行动方向",
  topics: "分析范围",
  task: "任务",
  deliverable: "本步成果",
  responsibilities: "职责分工",
  program: "程序",
  ai: "人工智能",
  human: "咨询师",
  repetition: "重复表达",
  source_fidelity: "事实忠实度",
  safety: "表达安全",
  block_to_action_link: "卡点与行动对应",
  report_coherence: "全文连贯性",
  chapter_coherence: "章节连贯性",
  gender: "性别",
  birth_year: "出生年",
  birth_month: "出生月",
  birth_day: "出生日",
  birth_hour: "出生时",
  birth_minute: "出生分",
  birth_place: "出生地",
  calendar_type: "历法",
  birth_time_precision: "时间精度",
  selected_topics: "关注主题",
  issue_duration: "困扰持续时间",
  impact_level: "影响程度",
  decision_status: "决策进度",
  decision_style: "决策方式",
  current_residence: "现居地",
  highest_education: "学历",
  marital_status: "婚姻状况",
};

export function displayText(value, field = "") {
  if (field === "semantic_role")
    return (
      {
        OBSERVATION: "综合观察",
        IDENTITY: "个人特质",
        RESOURCE: "个人资源",
        SHADOW: "待探索的部分",
        COMPLEX: "内在议题",
        DEFENSE: "应对方式",
        CONFLICT: "内在张力",
        PATTERN: "重复模式",
        BLOCK: "当前卡点",
        NEED: "重要需要",
        INTEGRATION_DIRECTION: "发展方向",
        TIMING: "阶段节奏",
        ACTION: "行动建议",
        CAREER_PATTERN: "职业模式",
        MOTIVATION_PATTERN: "动力模式",
        INTEGRATED_INSIGHT: "整合观察",
        ACTION_STRATEGY: "行动策略",
      }[value] || "其他专业用途"
    );
  if (value === null || value === undefined || value === "") return "未填写";
  if (typeof value === "boolean") return value ? "是" : "否";
  if (Object.hasOwn(LABELS, value)) return LABELS[value];
  return String(value)
    .replace(/\breport\.[a-z0-9_.]+\b/g, (key) => reportFragmentTitle(key))
    .replace(/\bS([1-6])\b/g, (_, step) => `第 ${step} 步`)
    .replace(
      /\b(Finding|Evidence|NarrativePlan|Signal|Case|SkillRun|Skill|Examples?|Tokens?|Prompt)\b/gi,
      (term) =>
        ({
          finding: "专业判断",
          evidence: "资料依据",
          narrativeplan: "报告主线",
          signal: "线索",
          case: "报告案例",
          skillrun: "技能运行记录",
          skill: "技能",
          example: "示例",
          examples: "示例",
          token: "计量单位",
          tokens: "计量单位",
          prompt: "提示词",
        })[term.toLowerCase()],
    );
}

export function fieldLabel(key) {
  return (
    (Object.hasOwn(LABELS, key) ? LABELS[key] : "") ||
    (/^[a-z_][a-z0-9_.]*$/i.test(key) ? "" : key)
  );
}

// Technical references are available in raw data, not presented as prose facts.
export function readableEntries(value) {
  return Object.entries(value || {})
    .filter(([key]) => fieldLabel(key))
    .map(([key, item]) => ({ key, label: fieldLabel(key), value: item }));
}

export function patchInstructions(text, patch) {
  const parsed = JSON.parse(text);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed))
    throw new Error("技能配置必须是对象");
  parsed.instructions = { ...parsed.instructions, ...patch };
  return JSON.stringify(parsed, null, 2);
}

export function evaluationCheckLabel(name) {
  if (name === "output_is_object") return "输出包含有效内容";
  if (name === "allowed_finding_refs") return "只引用允许使用的已确认判断";
  const [kind, path = ""] = name.split(":");
  const labels = {
    required: "包含必需内容",
    path_equals: "内容符合预期",
    minimum_array_length: "条目数量达到要求",
  };
  return labels[kind]
    ? `${labels[kind]} · ${path
        .split(".")
        .map(
          (part) =>
            fieldLabel(part) ||
            (/^\d+$/.test(part) ? `第 ${Number(part) + 1} 项` : "指定内容"),
        )
        .join(" / ")}`
    : "其他校验项";
}
