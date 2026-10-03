export const REPORT_WORKFLOW_STAGES = [
  {
    stepKey: 'S1',
    name: '命理基础结构',
    shortName: '命理基础',
    purpose: '先核对出生资料和系统测算结果，再形成有依据的初步判断。涉及心理感受的内容先保留为待验证线索。',
    task: '核对出生日期、时间与地点，再查看系统测算结果。整理命理层面的结构判断；涉及心理感受的内容只记录为待验证线索。',
    actions: [
      '先核对申请时保存的出生日期、时间和地点。',
      '查看命理测算结果，只把它作为结构线索，不当作心理事实。',
      '逐条审核建议，接受、修改或拒绝，并标出仍需验证的内容。'
    ],
    inputGuidance: '出生资料以用户本次确认的信息为准。系统测算用于专业分析，不代表用户的心理事实。',
    deliverable: '有资料依据的基础判断，以及需要后续验证的线索。',
    outputEmpty: '生成分析建议并逐条审核后，已确认的判断和分析会显示在这里。',
    inputGroups: [
      { key: 'profile', title: '申请时确认的出生档案', reason: '用于核对测算是否采用了用户本次确认的资料。', empty: '申请快照没有保存完整出生档案，请先核对用户资料。' },
      { key: 'context', title: '用户本次提出的情况', reason: '这是用户的现实问题和期待；心理含义仍需由后续自述验证。', empty: '用户没有填写额外情境描述。' },
      { key: 'systemEvidence', title: '系统测算结果', reason: '用于整理命理结构线索，不能单独证明性格或心理状态。', empty: '开始本步骤后，系统测算结果会出现在这里。' }
    ],
    tools: [
      { label: '查看申请资料', section: 'case-context' },
      { label: '核对测算依据', section: 'case-evidence' },
      { label: '审核专业判断', section: 'case-findings' },
      { label: '编辑分析内容', section: 'case-fragments' }
    ],
    checklist: ['核对出生资料与测算依据', '确认每条判断都有资料支持', '把心理含义保留为待验证线索', '接受、修改或拒绝建议'],
    sections: ['case-context', 'case-evidence', 'case-findings', 'case-fragments']
  },
  {
    stepKey: 'S2',
    name: '心理映射',
    shortName: '心理映射',
    purpose: '结合用户自述与已核对的基础信息，整理可能的思考和应对模式，不作临床诊断。',
    task: '以用户自述和具体情境为主，结合上一步已确认的基础判断，识别可能的思考、情绪和应对模式。资料不足时保留不确定性。',
    actions: [
      '先读用户对当前处境、感受和应对方式的描述。',
      '把第一步已确认的内容当作对照线索，不直接推导心理结论。',
      '审核每条建议：区分用户明确说过的事实与咨询分析的假设。'
    ],
    inputGuidance: '上一步的内容只是对照线索；正式心理判断必须能回到用户自述或具体情境，不作临床诊断。',
    deliverable: '有用户资料支持的心理运作模式判断，并清楚标记推测边界。',
    outputEmpty: '审核通过的心理模式判断和分析内容会显示在这里。',
    inputGroups: [
      { key: 'context', title: '用户的自述与当前情境', reason: '判断必须能回到用户描述的具体事件、感受或做法。', empty: '申请快照没有保存用户的情境说明。' },
      { key: 'upstreamFindings', title: '前序已确认的基础判断', reason: '只作辅助对照，不能代替用户自述或单独作为心理证据。', empty: '前序步骤还没有已确认的判断；请先完成审核。' },
      { key: 'referencedEvidence', title: '上述判断引用的资料', reason: '点明每条分析所依据的原始信息，资料不足时保留不确定性。', empty: '当前没有可追溯的资料引用。' }
    ],
    tools: [
      { label: '查看用户情境', section: 'case-context' },
      { label: '查看相关资料', section: 'case-evidence' },
      { label: '审核心理判断', section: 'case-findings' },
      { label: '审阅分析内容', section: 'case-fragments' }
    ],
    checklist: ['区分用户事实与分析假设', '核对触发情境、感受和应对方式', '为重要判断说明依据', '对资料不足或相互矛盾处保留不确定性'],
    sections: ['case-context', 'case-evidence', 'case-findings', 'case-fragments']
  },
  {
    stepKey: 'S3',
    name: '命理、心理与哲学整合',
    shortName: '三重整合',
    purpose: '把前两步已经确认的内容放在一起，梳理主要矛盾、发展方向和可以整合的部分。',
    task: '把前两步已确认的判断放在一起，梳理彼此支持、互相冲突或仍缺少资料的部分，再提炼主要张力与发展方向。',
    actions: [
      '只查看前两步已确认的判断和分析内容。',
      '标出哪些内容互相支持、存在冲突，或仍缺少信息。',
      '整理一条有来源的核心张力和发展方向，不预测选择结果。'
    ],
    inputGuidance: '只使用前序已确认的专业判断和分析内容。不要把尚未审核的建议当成事实。',
    deliverable: '一条有来源的核心张力，以及与用户现实选择相关的发展方向。',
    outputEmpty: '审核通过的整合判断和分析内容会显示在这里。',
    inputGroups: [
      { key: 'upstreamFindings', title: '前序已确认的专业判断', reason: '用于比较已核实的命理线索和心理观察，不能引入后续节点的结论。', empty: '前序步骤尚无已确认判断。' },
      { key: 'upstreamFragments', title: '前序已确认的分析内容', reason: '查看前两步的解释是否一致，并据此提炼共同主线。', empty: '前序步骤尚无已确认分析内容。' },
      { key: 'referencedEvidence', title: '专业判断对应的原始资料', reason: '回看每条判断的来源，避免把推测写成用户事实。', empty: '当前没有可追溯的资料引用。' }
    ],
    tools: [
      { label: '查看前序依据', section: 'case-evidence' },
      { label: '审核整合判断', section: 'case-findings' },
      { label: '审阅整合内容', section: 'case-fragments' }
    ],
    checklist: ['只整合已经确认的内容', '识别相互支持或存在冲突的判断', '说明主要矛盾与可发展的能力', '避免把结论写成绝对人格或确定未来'],
    sections: ['case-evidence', 'case-findings', 'case-fragments']
  },
  {
    stepKey: 'S4',
    name: '机制、卡点与行动',
    shortName: '机制与行动',
    purpose: '理解一种应对方式为什么会出现、有什么代价，再整理具体、可调整的行动方向。',
    task: '解释用户在当前情境中如何应对、这种方式短期解决了什么、长期可能付出什么代价，并设计低成本、可调整的行动。',
    actions: [
      '从用户面对的具体情境开始，梳理触发点、想法、感受和应对方式。',
      '说明这种做法短期保护了什么，以及长期可能带来什么代价。',
      '提出低成本、能观察结果、可以随时调整的小行动。'
    ],
    inputGuidance: '每条机制都要有前序判断或用户情境支持。行动建议应可逆、可观察，不替用户作重大决定。',
    deliverable: '有依据的应对机制、主要卡点，以及能由用户自行决定是否尝试的小行动。',
    outputEmpty: '审核通过的机制、卡点和行动建议会显示在这里。',
    inputGroups: [
      { key: 'context', title: '用户正在面对的现实情境', reason: '从真实选择和当前行动出发，不把一般描述套成固定人格。', empty: '申请快照没有保存用户的情境说明。' },
      { key: 'upstreamFindings', title: '前序已确认的判断', reason: '用来支持机制解释；每个解释都要能指出对应判断。', empty: '前序步骤尚无已确认判断。' },
      { key: 'upstreamFragments', title: '前序已确认的分析内容', reason: '承接已经审核过的理解，避免重复或新增未经确认的结论。', empty: '前序步骤尚无已确认分析内容。' },
      { key: 'referencedEvidence', title: '支撑这些判断的资料', reason: '核对用户事实来源，并检查行动是否回应具体卡点。', empty: '当前没有可追溯的资料引用。' }
    ],
    tools: [
      { label: '查看用户情境', section: 'case-context' },
      { label: '核对资料依据', section: 'case-evidence' },
      { label: '审核机制与行动判断', section: 'case-findings' },
      { label: '审阅行动内容', section: 'case-fragments' }
    ],
    checklist: ['确认每种解释都有前序依据', '区分问题理解与行动建议', '行动要具体、低成本且可调整', '不替用户作重大决定'],
    sections: ['case-evidence', 'case-findings', 'case-fragments']
  },
  {
    stepKey: 'S5',
    name: '叙事方案与报告写作',
    shortName: '报告写作',
    purpose: '依据前序已经确认的判断，选择报告主线并逐段生成、审阅和调整内容。',
    task: '先看 AI 提出的报告主线，选择或调整最贴合用户问题的一条并确认；再按内容安排顺序生成报告段落，逐段核对依据和表达。',
    actions: [
      '先选定一条最贴合用户问题的报告主线，并确认内容安排。',
      '逐段生成报告草稿，核对每段引用的判断和资料。',
      '修正事实、逻辑和表达后，确认可以进入最终检查的段落。'
    ],
    inputGuidance: '写作只能重组、解释和表达已确认的专业判断；不能新增事实、诊断、Finding 或确定的未来事件。',
    deliverable: '一份按确认主线组织、每段都能追溯到已确认判断的报告初稿。',
    outputEmpty: '确认主线并生成报告段落后，写作结果会显示在这里。',
    inputGroups: [
      { key: 'confirmedFindings', title: '可以写入报告的已确认判断', reason: '报告只能基于已经审核通过的判断，不能把建议直接写成结论。', empty: '没有已确认的专业判断，暂时不能开始写作。' },
      { key: 'confirmedFragments', title: '前序已确认的分析内容', reason: '用于解释判断之间的联系；写作时可以改写表达，不能新增专业判断。', empty: '没有已确认的分析内容，暂时不能开始写作。' },
      { key: 'narrativePlan', title: '咨询师确认的报告主线', reason: '决定报告如何组织，不改变已经确认的专业判断。', empty: '尚未确认报告主线。请先查看“叙事与写作”并选择一条建议。' },
      { key: 'plannedFragments', title: '各段内容安排', reason: '说明每段的目的和依据，帮助你发现遗漏、重复或顺序不合适。', empty: '确认报告主线后，系统会列出每段的重点和依据。' }
    ],
    tools: [
      { label: '查看专业判断', section: 'case-findings' },
      { label: '查看已确认分析', section: 'case-fragments' },
      { label: '选择主线并逐段写作', section: 'case-narrative' }
    ],
    checklist: ['确认报告只使用已确认的专业判断', '选择适合用户情境的报告主线', '逐段审阅内容与资料依据', '处理连贯性问题后完成本步骤'],
    sections: ['case-findings', 'case-fragments', 'case-narrative']
  },
  {
    stepKey: 'S6',
    name: '最终质量审核',
    shortName: '交付前检查',
    purpose: '检查报告是否完整、连贯并适合交付，逐项处理问题后完成最终复核。',
    task: '运行交付前检查，逐条处理阻断问题和需要说明的提示；最后复核报告是否贴合用户情况、依据充分、表达稳妥。',
    actions: [
      '运行系统检查和 AI 内容复核，阅读每项问题指向的段落。',
      '先修复所有阻断问题；内容改动后重新运行检查。',
      '通读最终稿和处理记录，确认后完成最终复核并交付。'
    ],
    inputGuidance: '检查对象是已审阅的报告正文、对应的确认依据和系统检查结果。存在阻断问题时不能交付。',
    deliverable: '通过质量检查并完成最终人工确认后，生成不可覆盖的交付版本。',
    outputEmpty: '运行交付前检查并完成最终审核后，检查结论会显示在这里。',
    inputGroups: [
      { key: 'reportFragments', title: '等待最终复核的报告正文', reason: '只复核已确认的报告段落；重点看是否准确回应用户本次问题。', empty: '还没有可供复核的报告段落。' },
      { key: 'confirmedFindings', title: '报告可以引用的已确认判断', reason: '用来核验报告每项重要结论是否有已审核的专业依据。', empty: '没有已确认的专业判断。' },
      { key: 'qualityIssues', title: '系统检查与待处理事项', reason: '按严重程度处理问题；仍有阻断项时不能完成交付。', empty: '尚未运行交付前检查。' }
    ],
    tools: [
      { label: '查看报告正文', section: 'case-narrative' },
      { label: '查看资料与判断依据', section: 'case-evidence' },
      { label: '运行检查并处理问题', section: 'case-quality' }
    ],
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

const REPORT_FRAGMENT_TITLES = {
  'report.overview.psychic_structure': '整体心灵结构',
  'report.identity.outer_self': '世界看到的你',
  'report.identity.foundation_notes': '命盘逻辑旁注',
  'report.identity.self_perception': '你眼中的自己',
  'report.identity.hidden_self': '被隐藏的自己',
  'report.identity.energy_pattern': '能量如何流动',
  'report.identity.relationship_pattern': '关系中的循环',
  'report.identity.self_direction': '走向更完整的自己',
  'report.blocks.block_01': '卡点一',
  'report.blocks.block_02': '卡点二',
  'report.blocks.block_03': '卡点三',
  'report.blocks.block_04': '卡点四',
  'report.blocks.block_05': '卡点五',
  'report.blocks.common_pattern': '卡点背后的共性',
  'report.blocks.breakthrough': '整合与破局方向',
  'report.direction.current_stage': '当下的阶段主题',
  'report.direction.life_map': '人生阶段地图',
  'report.direction.growth_experiments': '专属成长实验',
  'report.ending': '给你的寄语'
}

export function reportFragmentTitle(fragmentKey, fallback = '') {
  const title = String(fallback || '').trim()
  if (title && !/[A-Za-z]{2,}/.test(title)) return title
  return REPORT_FRAGMENT_TITLES[String(fragmentKey || '')] || '报告段落'
}
