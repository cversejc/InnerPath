export const REPORT_WORKFLOW_STAGES = [
  {
    stepKey: 'S1',
    name: '命理基础结构',
    shortName: '命理基础',
    purpose: '先核对出生资料和系统测算结果，再形成有依据的初步判断。涉及心理感受的内容先保留为待验证线索。',
    inputs: ['本次用户资料与申请情境', '系统测算结果与来源'],
    tools: ['查看测算依据', '生成分析建议', '核对判断与来源', '编辑报告内容'],
    checklist: ['核对出生资料与测算依据', '确认每条判断都有资料支持', '把心理含义保留为待验证线索', '接受、修改或拒绝建议'],
    sections: ['case-context', 'case-evidence', 'case-findings', 'case-fragments']
  },
  {
    stepKey: 'S2',
    name: '心理映射',
    shortName: '心理映射',
    purpose: '结合用户自述与已核对的基础信息，整理可能的思考和应对模式，不作临床诊断。',
    inputs: ['用户自述与申请情境', '已确认的基础判断', '相关资料依据'],
    tools: ['生成分析建议', '查看前序判断与依据', '审核判断和报告内容'],
    checklist: ['区分用户事实与分析假设', '核对触发情境、感受和应对方式', '为重要判断说明依据', '对资料不足或相互矛盾处保留不确定性'],
    sections: ['case-context', 'case-evidence', 'case-findings', 'case-fragments']
  },
  {
    stepKey: 'S3',
    name: '命理、心理与哲学整合',
    shortName: '三重整合',
    purpose: '把前两步已经确认的内容放在一起，梳理主要矛盾、发展方向和可以整合的部分。',
    inputs: ['前序已确认的判断与分析内容', '支持这些判断的资料'],
    tools: ['生成整合建议', '核对内容之间的关系与依据', '审核判断和报告内容'],
    checklist: ['只整合已经确认的内容', '识别相互支持或存在冲突的判断', '说明主要矛盾与可发展的能力', '避免把结论写成绝对人格或确定未来'],
    sections: ['case-evidence', 'case-findings', 'case-fragments']
  },
  {
    stepKey: 'S4',
    name: '机制、卡点与行动',
    shortName: '机制与行动',
    purpose: '理解一种应对方式为什么会出现、有什么代价，再整理具体、可调整的行动方向。',
    inputs: ['前序已确认的判断与分析内容', '用户提供的具体情境'],
    tools: ['生成机制与行动建议', '核对资料依据', '审核判断和报告内容'],
    checklist: ['确认每种解释都有前序依据', '区分问题理解与行动建议', '行动要具体、低成本且可调整', '不替用户作重大决定'],
    sections: ['case-evidence', 'case-findings', 'case-fragments']
  },
  {
    stepKey: 'S5',
    name: '叙事方案与报告写作',
    shortName: '报告写作',
    purpose: '依据前序已经确认的判断，选择报告主线并逐段生成、审阅和调整内容。',
    inputs: ['前序已确认的判断与分析内容', '咨询师确认的报告主线', '各段内容安排'],
    tools: ['生成报告主线建议', '选择并确认主线', '按顺序生成内容', '检查章节和全文连贯性'],
    checklist: ['确认报告只使用已确认的专业判断', '选择适合用户情境的报告主线', '逐段审阅内容与资料依据', '处理连贯性问题后完成本步骤'],
    sections: ['case-findings', 'case-fragments', 'case-narrative']
  },
  {
    stepKey: 'S6',
    name: '最终质量审核',
    shortName: '交付前检查',
    purpose: '检查报告是否完整、连贯并适合交付，逐项处理问题后完成最终复核。',
    inputs: ['已审阅的报告内容与资料依据', '系统检查结果', '内容审核建议'],
    tools: ['运行最终检查', '定位并处理问题', '完成最终复核', '生成并交付报告'],
    checklist: ['确认系统检查和内容审核已完成', '处理所有阻断问题', '复核报告主线、用户贴合度和处理记录', '确认无误后完成最终交付'],
    sections: ['case-narrative', 'case-quality']
  }
]

export const REPORT_STEP_STATUS_LABELS = {
  PENDING: '等待上一步',
  READY: '待开始',
  IN_REVIEW: '待处理',
  EXECUTING: '正在生成内容',
  WAITING_REVIEW: '待你审核',
  NEEDS_REVISION: '需要修改',
  COMPLETED: '已完成',
  CANCELLED: '已取消'
}

export function reportStage(stepKey) {
  return REPORT_WORKFLOW_STAGES.find(stage => stage.stepKey === stepKey) || null
}
