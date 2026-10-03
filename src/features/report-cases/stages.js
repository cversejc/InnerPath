export const REPORT_WORKFLOW_STAGES = [
  {
    stepKey: 'S1',
    name: '命理基础结构',
    shortName: '命理基础',
    purpose: '整理系统计算结果，形成有依据的结构判断与待验证信号，不直接推断心理问题。',
    inputs: ['本次用户资料与申请情境', '确定性八字 / 紫微计算 Evidence'],
    tools: ['DeepSeek 分析草稿', 'Evidence 来源核对', 'Finding / Signal 审核', 'Analysis Fragment 编辑'],
    checklist: ['核对出生资料和系统计算依据', '判断每条结论是否被 Evidence 支持', '将心理含义保留为待验证 Signal', '接受、修改或拒绝候选判断'],
    sections: ['case-context', 'case-evidence', 'case-findings', 'case-fragments']
  },
  {
    stepKey: 'S2',
    name: '心理映射',
    shortName: '心理映射',
    purpose: '把已确认的 S1 结构映射为可验证的运作模式假设，避免临床诊断式定性。',
    inputs: ['用户自述与申请情境', '已确认的 S1 Finding / Signal', '相关 Evidence'],
    tools: ['DeepSeek 分析草稿', '上游 Finding / Evidence 查看', 'Finding / Fragment 审核'],
    checklist: ['区分用户事实、命理解释与心理假设', '检查触发、情绪、自动想法和应对模式', '为关键判断标注置信度和依据', '对资料不足或冲突处保留不确定性'],
    sections: ['case-context', 'case-evidence', 'case-findings', 'case-fragments']
  },
  {
    stepKey: 'S3',
    name: '命理、心理与哲学整合',
    shortName: '三重整合',
    purpose: '综合已确认判断，提出中心张力、自我方向和整合任务，不重做上游分析。',
    inputs: ['已确认的 S1–S2 Finding 与 Analysis Fragment', '支持判断的 Evidence'],
    tools: ['DeepSeek 整合草稿', '关系与来源核对', 'Finding / Fragment 审核'],
    checklist: ['只整合已确认的上游语义', '识别相互支持或冲突的判断', '说明中心张力与可发展的能力', '避免写成完美人格或确定未来'],
    sections: ['case-evidence', 'case-findings', 'case-fragments']
  },
  {
    stepKey: 'S4',
    name: '机制、卡点与行动',
    shortName: '机制与行动',
    purpose: '解释模式的保护功能与长期代价，整理重点卡点，并提出低风险、可复盘的行动候选。',
    inputs: ['已确认的 S1–S3 Finding 与 Analysis Fragment', '用户明确提供的情境 Evidence'],
    tools: ['DeepSeek 机制 / 行动草稿', 'Evidence 与来源核对', 'Finding / Fragment 审核'],
    checklist: ['检查机制解释是否有上游依据', '区分卡点理解与行动建议', '行动需具体、低成本且可逆', '确认建议没有替用户作重大决定'],
    sections: ['case-evidence', 'case-findings', 'case-fragments']
  },
  {
    stepKey: 'S5',
    name: '叙事方案与报告写作',
    shortName: '报告写作',
    purpose: '基于已确认语义选择叙事主线，按片段分配、写作、追溯来源并进行连贯性审阅。',
    inputs: ['已确认 Finding / Analysis Fragment', '咨询师确认的 NarrativePlan', '片段分配与来源快照'],
    tools: ['生成叙事候选', '选择并确认 NarrativePlan', '按分配顺序写作', '章节 / 全文连贯性检查'],
    checklist: ['确认只使用已确认的专业语义', '选择并确认合适的叙事主线', '审阅每段内容及来源映射', '处理连贯性问题后完成 S5'],
    sections: ['case-findings', 'case-fragments', 'case-narrative']
  },
  {
    stepKey: 'S6',
    name: '最终质量审核',
    shortName: '最终 QA',
    purpose: '运行程序与语义 QA，处理阻断项，完成最终人工门禁后生成不可覆盖的交付版本。',
    inputs: ['已审阅的报告片段与来源映射', '程序 QA 结果', '语义 Validator 结果'],
    tools: ['运行最终 QA', '按片段定位并处理问题', '最终责任确认', '生成并交付版本'],
    checklist: ['确认程序检查和语义审核已完成', '所有 BLOCK / 未处理问题均已清理', '复核核心叙事、用户贴合度和处理记录', '通过最终门禁后生成交付版本'],
    sections: ['case-narrative', 'case-quality']
  }
]

export const REPORT_STEP_STATUS_LABELS = {
  PENDING: '等待前序',
  READY: '待开始',
  IN_REVIEW: '处理中',
  EXECUTING: 'AI 执行中',
  WAITING_REVIEW: '待审核',
  NEEDS_REVISION: '待返工',
  COMPLETED: '已完成',
  CANCELLED: '已取消'
}

export function reportStage(stepKey) {
  return REPORT_WORKFLOW_STAGES.find(stage => stage.stepKey === stepKey) || null
}
