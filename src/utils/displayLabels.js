// User-facing labels for stable values returned by the API.
// Keep technical keys in payloads and use these maps only at presentation boundaries.

export const TOPIC_LABELS = {
  career: '职业发展',
  relationship: '亲密关系',
  relationships: '人际关系',
  family: '家庭议题',
  finance: '财务规划',
  health: '身心健康',
  social: '人际关系',
  self: '个人成长',
  growth: '个人成长',
  personal_growth: '个人成长',
  children: '子女教育',
  stress: '压力与焦虑',
  decision: '选择与决策',
  other: '其他'
}

export const EXPECTED_OUTCOME_LABELS = {
  '认识自己': '更清晰地认识自己',
  '解决方案': '找到当前问题的解决方案',
  '方向指引': '获得对未来方向的指引',
  '验证判断': '验证自己已有的判断',
  '心理支持': '获得心理上的安慰与支持',
  '节奏参考': '了解自己的命理 / 运势节奏',
  action_windows: '看见适合推进的时间',
  pause_windows: '知道什么时候适合观察或休整',
  daily_prompt: '获得每日行动提示',
  decision_review: '在重要决策前获得参考',
  reflection: '记录并复盘真实选择',
  emotional_support: '获得稳定情绪的提醒',
  other: '其他'
}

export const DECISION_STYLE_LABELS = {
  intuition: '凭直觉判断',
  rational: '理性分析利弊',
  family_friends: '咨询家人 / 朋友意见',
  professional: '寻求专业人士建议',
  wait: '顺其自然，等时间给答案',
  other: '其他'
}

export const USAGE_SCENARIO_LABELS = {
  morning_planning: '每天早上规划一天',
  evening_review: '每天晚上复盘反思',
  when_confused: '遇到困惑时查找指引',
  before_decision: '做重要决策前参考',
  emotional_support: '情绪低落时寻求安慰',
  daily: '每天使用',
  other: '其他'
}

export const PROFILE_VALUE_LABELS = {
  male: '男',
  female: '女',
  solar: '公历',
  lunar: '农历',
  unknown: '不知道',
  approximate: '大概时间',
  exact: '精确时间',
  single: '单身',
  dating: '恋爱中',
  married: '已婚',
  divorced: '离异',
  other: '其他',
  full_time: '全职工作',
  freelance: '自由职业',
  entrepreneur: '创业者',
  student: '学生',
  unemployed: '待业',
  job_seeking: '求职中',
  high_school_or_below: '高中及以下',
  college: '大专',
  bachelor: '本科',
  master: '硕士',
  doctorate_or_above: '博士及以上',
  bazi_ziwei: '八字 / 紫微斗数命理咨询',
  astrology: '星座 / 星盘分析',
  tarot: '塔罗牌占卜',
  ai_divination: '在线 AI 占卜 / 命理工具',
  feng_shui: '风水咨询',
  never: '从未接触过',
  strongly_believe: '非常相信',
  reference: '比较相信，作为参考',
  uncertain: '半信半疑',
  curious: '不太相信，但感兴趣',
  disbelieve: '完全不相信',
  concise: '简洁明了，给核心结论即可',
  balanced: '中等深度，有解释和背景',
  deep: '深入详细，希望了解完整的命理逻辑',
  explorer: '探索者'
}

export const SERVICE_TYPE_LABELS = {
  report: '人生说明书',
  calendar: '决策日历'
}

export const CONSULTATION_TYPE_LABELS = {
  metaphysics: '命理',
  mingli: '命理',
  psychology: '心理',
  integrated: '综合（命理 + 心理）',
  overall: '全部报告',
  unspecified: '未分类'
}

export const WORKFLOW_TYPE_LABELS = {
  calendar_generation: '日历生成',
  calendar_legacy: '旧版日历流程',
  report: '报告申请',
  service_request: '服务申请'
}

export const RESULT_TYPE_LABELS = {
  report: '报告',
  calendar: '日历'
}

export const USER_TYPE_LABELS = {
  explorer: '探索者',
  consultant: '咨询师',
  admin: '管理员'
}

export const ROLE_LABELS = {
  user: '用户',
  consultant: '咨询师',
  admin: '管理员'
}

export const REPORT_STATUS_LABELS = {
  processing: '生成中',
  completed: '已完成',
  failed: '失败'
}

export const CALENDAR_STATUS_LABELS = {
  draft: '草稿',
  published: '已发布',
  archived: '已归档'
}

export const CALENDAR_TONE_LABELS = {
  green: '推进',
  'green-yellow': '先推后收',
  'yellow-green': '先备后行',
  yellow: '观察',
  'red-yellow': '缓冲',
  red: '收气',
  rest: '休整'
}

export const DECISION_STATUS_LABELS = {
  done: '已完成',
  doing: '进行中',
  skipped: '已跳过'
}

export const SERVICE_REQUEST_STATUS_LABELS = {
  submitted: '待接单',
  accepted: '已接单',
  ai_processing: '生成初稿',
  processing: '处理中',
  ai_ready: '待审校',
  reviewing: '审校中',
  needs_info: '待补充',
  failed: '处理失败',
  delivered: '已交付',
  workflow_complete: '待交付',
  withdrawn: '已撤回',
  rejected: '已关闭'
}

export const CALENDAR_REQUEST_STATUS_LABELS = {
  pending: '待生成',
  queued: '排队中',
  generating: '生成中',
  processing: '生成中',
  delivered: '已交付',
  reviewing: '审核中',
  failed: '生成失败',
  fulfilled: '已完成',
  rejected: '已退回',
  cancelled: '已取消'
}

export const FEEDBACK_TYPE_LABELS = {
  PRAISE: '表扬',
  SUGGESTION: '建议',
  COMPLAINT: '投诉'
}

export const FEEDBACK_STATUS_LABELS = {
  NEW: '待处理',
  IN_PROGRESS: '处理中',
  RESOLVED: '已结案'
}

export const QUALITY_SEVERITY_LABELS = {
  BLOCK: '阻断',
  MAJOR: '主要',
  MINOR: '提示',
  WARN: '建议处理',
  INFO: '提示'
}

export const QUALITY_STATUS_LABELS = {
  OPEN: '待处理',
  RESOLVED: '已解决',
  ACCEPTED: '已接受',
  DISMISSED: '已忽略',
  PASSED: '检查通过',
  PROGRAMMATIC_BLOCKED: '发现必须处理的问题',
  BLOCKED: '暂不能交付',
  NOT_RUN: '尚未检查',
  PENDING: '等待检查',
  RUNNING: '正在检查',
  READY: '可以进行最终复核',
  COMPLETED: '检查已完成',
  FAILED: '检查失败'
}

export const QUALITY_SOURCE_LABELS = {
  PROGRAMMATIC: '规则检查',
  VALIDATOR: '语义检查'
}

export const REPORT_CASE_STATUS_LABELS = {
  CREATED: '新建',
  ACTIVE: '处理中',
  BLOCKED: '受阻',
  READY_TO_DELIVER: '待交付',
  DELIVERED: '已交付',
  CANCELLED: '已取消'
}

export const REPORT_STEP_STATUS_LABELS = {
  PENDING: '等待上一步',
  READY: '待开始',
  IN_REVIEW: '待处理',
  EXECUTING: '正在生成内容',
  WAITING_REVIEW: '待你审核',
  NEEDS_REVISION: '需要修改',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
  FAILED: '处理失败'
}

export const REPORT_ASSET_STATUS_LABELS = {
  ACTIVE: '可用',
  CONFIRMED: '已确认',
  PROPOSED: '待审核',
  REJECTED: '已拒绝',
  STALE: '需要重新审核',
  OPEN: '待处理',
  RESOLVED: '已处理',
  ACCEPTED: '已接受',
  DISMISSED: '已忽略',
  PENDING: '待开始',
  RUNNING: '正在处理',
  COMPLETED: '已完成',
  FAILED: '暂时失败',
  READY: '待开始',
  BLOCKED: '需要处理',
  NOT_RUN: '尚未检查',
  PASSED: '检查通过',
  PROGRAMMATIC_BLOCKED: '发现必须处理的问题',
  IN_PROGRESS: '正在生成',
  NEEDS_REVISION: '需要修改',
  READY_FOR_REVIEW: '待审核',
  CREATED: '待开始',
  DELIVERED: '已交付',
  CANCELLED: '已关闭'
}

export const EVIDENCE_SOURCE_LABELS = {
  USER_PROVIDED: '用户提供',
  USER_CONTEXT: '申请补充',
  APPLICATION_CONTEXT: '申请补充',
  USER_PROFILE: '用户档案',
  SYSTEM_CALCULATED: '系统测算',
  CONSULTANT_CORRECTED: '咨询师修订',
  EXTERNAL_REFERENCE: '外部资料',
  REPORT: '已交付报告',
  CONSULTANT: '咨询师补充'
}

export const FINDING_KIND_LABELS = {
  FINDING: '专业判断',
  SIGNAL: '待验证线索'
}

export const FINDING_STATUS_LABELS = {
  PROPOSED: '待审核',
  CONFIRMED: '已确认',
  REJECTED: '已拒绝',
  STALE: '需复核'
}

export const EDIT_KIND_LABELS = {
  STYLE: '表达调整',
  SEMANTIC: '内容调整'
}

export const CONFIDENCE_LABELS = {
  LOW: '较低',
  MEDIUM: '一般',
  HIGH: '较高'
}

export const IMPORTANCE_LABELS = {
  LOW: '普通',
  MEDIUM: '关注',
  HIGH: '重要',
  CRITICAL: '优先'
}

export const REPORTABILITY_LABELS = {
  INTERNAL_ONLY: '仅供内部参考',
  OPTIONAL: '可酌情呈现',
  RECOMMENDED: '建议呈现',
  MUST_INCLUDE: '报告需要包含'
}

export const SEMANTIC_ROLE_LABELS = {
  OBSERVATION: '综合观察',
  IDENTITY: '个人特质',
  STRENGTH: '优势',
  RESOURCE: '个人资源',
  CHALLENGE: '需要留意',
  SHADOW: '待探索的部分',
  COMPLEX: '内在议题',
  DEFENSE: '应对方式',
  CONFLICT: '内在张力',
  PATTERN: '行为模式',
  SIGNAL: '待验证线索',
  THEME: '核心主题',
  BLOCK: '当前卡点',
  NEED: '重要需要',
  INTEGRATION_DIRECTION: '发展方向',
  TIMING: '阶段节奏',
  ACTION: '行动方向',
  CAREER_PATTERN: '职业模式',
  MOTIVATION_PATTERN: '动力模式',
  INTEGRATED_INSIGHT: '整合观察',
  ACTION_STRATEGY: '行动策略'
}

export const EXAMPLE_STATUS_LABELS = {
  CANDIDATE: '待审核',
  PUBLISHED: '已发布',
  RETIRED: '已停用'
}

export const EXAMPLE_TYPE_LABELS = {
  POSITIVE: '正向示例',
  CONTRASTIVE: '对照示例',
  MISSED_INSIGHT: '补充洞察'
}

export const SKILL_RUN_STATUS_LABELS = {
  PENDING: '排队中',
  RUNNING: '执行中',
  COMPLETED: '已完成',
  FAILED: '失败'
}

export const SKILL_VERSION_STATUS_LABELS = {
  DRAFT: '草稿',
  EVALUATION: '评测中',
  PUBLISHED: '已发布',
  RETIRED: '已停用'
}

export const SKILL_CATEGORY_LABELS = {
  ANALYSIS: '分析',
  ACTION: '行动',
  AUTHORING: '写作',
  VALIDATOR: '检查'
}

export const REPORT_ISSUE_TYPE_LABELS = {
  MISSING_REPORT_CONTENT: '报告内容不完整',
  MISSING_SEMANTIC_SUPPORT: '内容缺少判断依据',
  SOURCE_COVERAGE_GAP: '部分内容缺少来源说明',
  DUPLICATE_CONTENT: '内容存在重复',
  UNSUPPORTED_CLAIM: '发现缺少依据的表述',
  INCONSISTENT_NARRATIVE: '前后表达不一致',
  SAFETY_LANGUAGE: '需要检查建议表达',
  USER_CONTEXT_MISMATCH: '内容与用户情况不匹配',
  FINDING_OVER_REPEATED: '同一专业判断被多段引用',
  quality_score_below_threshold: '报告质量评分未达交付门槛',
  source_fidelity: '用户经历需要核对',
  repetition: '段落内容需要精简',
  safety: '确认尊重用户边界',
  block_to_action_link: '行动建议需要对应卡点',
  report_coherence: '报告表达需要复核',
  chapter_coherence: '章节衔接需要调整',
  FRAMEWORK_CONTENT_MISSING: '报告结构内容缺失',
  REPORT_COHERENCE_ISSUE: '报告全文连贯性需要复核',
  SEMANTIC_REVIEW: '语义内容需要复核'
}

export function labelFor(value, labels, fallback = '—') {
  if (value === null || value === undefined || value === '') return fallback
  return Object.prototype.hasOwnProperty.call(labels || {}, value) ? labels[value] : fallback
}

export function labelList(values, labels, fallback = '—') {
  if (!Array.isArray(values) || !values.length) return fallback
  return values.map(value => labelFor(value, labels, String(value))).join('、')
}

export function firstNonEmptyArray(...values) {
  return values.find(value => Array.isArray(value) && value.length)
    || values.find(value => Array.isArray(value))
    || []
}

export function profileValueLabel(value, fallback = '未填写') {
  if (Array.isArray(value)) return labelList(value, PROFILE_VALUE_LABELS, fallback)
  return labelFor(value, PROFILE_VALUE_LABELS, fallback)
}

export function topicLabel(values, fallback = '综合自我探索') {
  if (!Array.isArray(values) || !values.length) return fallback
  return values.map(value => labelFor(value, TOPIC_LABELS, '其他关注主题')).join('、')
}

export function usageScenarioLabel(value, fallback = '未填写用途') {
  return labelFor(value, USAGE_SCENARIO_LABELS, fallback)
}

export function expectedOutcomeLabel(value, fallback = '其他') {
  return labelFor(value, EXPECTED_OUTCOME_LABELS, fallback)
}

export function calendarToneLabel(value, fallback = '观察') {
  return labelFor(value, CALENDAR_TONE_LABELS, fallback)
}
