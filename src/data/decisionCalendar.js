const weekdayNames = ['日', '一', '二', '三', '四', '五', '六']

const pad = value => String(value).padStart(2, '0')

function toDateKey(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

function parseDateKey(dateKey) {
  const [year, month, day] = dateKey.split('-').map(Number)
  return new Date(year, month - 1, day)
}

function currentDateKey() {
  return toDateKey(new Date())
}

export const calendarMeta = {
  year: 2026,
  startDate: '2026-09-07',
  endDate: '2026-10-07',
  title: '辰鉴 · 你的丁酉月时区说明书',
  subtitle: '辰鉴 · 你的决策时机参照系',
  dateLabel: '甲申日（9月7日）→ 丁酉月末（10月7日）',
  pillars: '癸未 甲寅 丙寅 丁酉',
  rhythm: '少说，多做，多记录',
  intro: '这不是一张催你行动的日程表，而是一张帮你看见“此刻适合做什么”的参照系。',
  overview: [
    '丁火（劫财）坐酉金（正财），与你的时柱丁酉形成“伏吟”。本月你会反复琢磨钱怎么分、时间怎么用、精力怎么分配，这很正常。',
    '流月酉金与日柱寅木形成“寅酉暗合”：看起来在休息，实际上在布局。台面动作不多，台下的判断和整合会非常密集。'
  ]
}

export const phaseDefinitions = [
  {
    id: 'observe',
    label: '想法记录期',
    shortLabel: '记录',
    dateRange: '9月7日—9月11日',
    startDate: '2026-09-07',
    endDate: '2026-09-11',
    tone: 'yellow',
    statusLabel: '黄灯 · 先记录',
    summary: '想法频繁涌现，但建议只记录、不推进。把模糊的念头先变成纸上的条目。',
    suitable: ['整理产品框架里的不确定项', '记录灵感与过去一周的决策节奏', '听团队意见，暂不急着拍板'],
    unsuitable: ['启动对外宣发或招募', '在情绪里做最终决策', '为了完成度强行推进'],
    timeWindow: '申时（15—17点）通常更清晰，适合安排重要沟通；酉时（17—19点）后逐步收气。'
  },
  {
    id: 'express',
    label: '表达落地期',
    shortLabel: '表达',
    dateRange: '9月12日—9月17日',
    startDate: '2026-09-12',
    endDate: '2026-09-17',
    tone: 'green',
    statusLabel: '绿灯 · 可推进',
    summary: '输出欲望和执行力逐步抬升，适合把“辰鉴是什么”写下来，并完成第一批可反馈的交付。',
    suitable: ['确认产品框架与模块', '写产品介绍和对外文本', '完成用户名单、交付模板与首批材料'],
    unsuitable: ['材料不足时凭冲动开新题', '下午后反复修改或重做', '临时推翻已经确认的安排'],
    timeWindow: '巳时（9—11点）适合核心执行；申时（15—17点）适合沟通与回顾；17日午时前是本月最后一段高效输出。'
  },
  {
    id: 'rest',
    label: '休整积累期',
    shortLabel: '休整',
    dateRange: '9月18日—9月23日',
    startDate: '2026-09-18',
    endDate: '2026-09-23',
    tone: 'rest',
    statusLabel: '黄/红灯 · 先收气',
    summary: '不适合发起新动作。你可能觉得“什么都没做”，但实际是在积攒精力、等待反馈。',
    suitable: ['记录与整理', '回复搁置消息', '完成不需脑力的扫尾工作', '安静等待用户反馈'],
    unsuitable: ['做新产品决策', '主动追问反馈或招募', '在沟通里强行定方向'],
    timeWindow: '让工作留出呼吸感：减少长时间盯屏，多起身、散步或做一点体力活。'
  },
  {
    id: 'feedback',
    label: '反馈调整期',
    shortLabel: '调整',
    dateRange: '9月24日—10月7日',
    startDate: '2026-09-24',
    endDate: '2026-10-07',
    tone: 'green',
    statusLabel: '绿灯 · 复盘微调',
    summary: '财务结构和用户反馈开始显现，适合做小幅调整，不适合大规模推翻重做。',
    suitable: ['收集首批用户的真实感受', '复盘9月的决策节奏', '微调产品形态、定价与交付方式'],
    unsuitable: ['过早宣发“正式版”', '因为单条反馈重构全部产品', '把等待误判成停滞'],
    timeWindow: '把反馈分成“事实、感受、下一步”三栏，留出一天再决定是否调整。'
  }
]

const dailyDetails = {
  '2026-09-07': {
    dayPillar: '甲申',
    tone: 'yellow',
    statusLabel: '黄灯 · 适合准备',
    keyword: '观察',
    suitable: ['把“辰鉴”的产品框架再读一遍，标记不确定的部分', '团队对话中先听再说', '晚上复盘过去一周的决策节奏，只记录不评价'],
    unsuitable: ['做最终决策', '对外宣发或招募'],
    timeWindow: '申时（15—17点）能量最清晰，适合安排重要沟通；酉时（17—19点）后能量转弱，不宜继续工作。'
  },
  '2026-09-08': {
    dayPillar: '乙酉',
    tone: 'yellow-green',
    statusLabel: '黄灯 → 晚上绿灯',
    keyword: '梳理',
    suitable: ['将产品问题按“已定 / 待定”重新分类', '把昨晚的复盘整理成“上周回顾”存档'],
    unsuitable: ['中午前决定定价、分账或预算', '回应情绪化对话'],
    timeWindow: '酉时（17—19点）能量最顺，适合写下还未落笔的想法；戌时（19—21点）后不宜做需要耐心的工作。'
  },
  '2026-09-09': {
    dayPillar: '丙戌',
    tone: 'red',
    statusLabel: '红灯 · 建议休息',
    keyword: '清扫',
    suitable: ['清理文件、回复搁置消息、整理书架', '完成之前中断的事务性任务', '晚上散步或做体力活'],
    unsuitable: ['产品决策、写文档、想新点子', '涉及规则或边界的谈判'],
    timeWindow: '午时（11—13点）后容易焦虑，若烦躁可以提前结束工作。'
  },
  '2026-09-10': {
    dayPillar: '丁亥',
    tone: 'red-yellow',
    statusLabel: '红灯 → 晚上黄灯',
    keyword: '缓冲',
    suitable: ['延续整理、归档、归类', '线上消息只读不回（紧急除外）', '晚上翻看笔记，标记现在仍有价值的内容'],
    unsuitable: ['开始新任务', '做涉及未来规划的决策'],
    timeWindow: '全天水气偏重，避免长时间盯屏幕，多起身活动。'
  },
  '2026-09-11': {
    dayPillar: '戊子',
    tone: 'yellow-green',
    statusLabel: '黄灯 → 下午绿灯',
    keyword: '启动',
    suitable: ['下午把想法转成可执行的下一步', '汇总9月以来的决策日志', '傍晚客观评估“辰鉴”当前进度'],
    unsuitable: ['上午做财务决定', '回应“谁对谁错”的争论'],
    timeWindow: '申时（15—17点）能量最清晰，适合安排一次决策回顾。'
  },
  '2026-09-12': {
    dayPillar: '己丑',
    tone: 'green',
    statusLabel: '绿灯 · 适合推进',
    keyword: '落地',
    suitable: ['推进已确定的决策，例如分配团队任务、确认印刷数量', '完成搁置的文案或产品介绍', '晚上对产品路线做简短展望'],
    unsuitable: ['材料不充分时做新决策'],
    timeWindow: '巳时（9—11点）执行力最强；酉时（17—19点）后适合做财务轻量整理。'
  },
  '2026-09-13': {
    dayPillar: '庚寅',
    tone: 'green-yellow',
    statusLabel: '绿灯 → 下午黄灯',
    keyword: '表达',
    suitable: ['上午写一篇500—800字的产品介绍', '写下“为什么做辰鉴”', '下午发给合适的人看看感觉'],
    unsuitable: ['下午后做决定', '反复修改文本'],
    timeWindow: '巳时是写作窗口；申时（15—17点）是沟通窗口，适合同步信息但不拍板。'
  },
  '2026-09-14': {
    dayPillar: '辛卯',
    tone: 'green-yellow',
    statusLabel: '绿灯 → 晚上黄灯',
    keyword: '细化',
    suitable: ['把产品构想和讨论会决议合并成《辰鉴产品文档》', '发文案给朋友征求修改意见', '傍晚整理用户需求反馈'],
    unsuitable: ['晚上做决策', '为追求完美反复开新版本'],
    timeWindow: '巳时和申时是两个高效率窗口，核心任务分置在这两个时段。'
  },
  '2026-09-15': {
    dayPillar: '壬辰',
    tone: 'yellow-green',
    statusLabel: '黄灯 → 下午绿灯',
    keyword: '收束',
    suitable: ['确认“9月15日前我要交付什么”', '完成回复邮件、整理文件等事务性工作', '下午处理印刷数量、交付方式等轻量决策'],
    unsuitable: ['上午做精密决策', '做长远布局的决定'],
    timeWindow: '午时后思路会更清晰，先列任务，再逐个推进。'
  },
  '2026-09-16': {
    dayPillar: '癸巳',
    tone: 'green',
    statusLabel: '绿灯 · 适合推进',
    keyword: '推进',
    suitable: ['确认首批用户名单', '确定第一批用户拿到的交付模板', '把产品形态上的犹豫收束成一个可交付版本'],
    unsuitable: ['临时改变已决定的事', '申时后再开启新决定'],
    timeWindow: '巳时（9—11点）决策力最强，核心决策集中于此。'
  },
  '2026-09-17': {
    dayPillar: '甲午',
    tone: 'green',
    statusLabel: '绿灯 · 本月最后窗口',
    keyword: '交付',
    suitable: ['定稿《人生说明书》内容', '确认用户名单并安排物流', '上午启动“辰鉴·共鉴计划”等对外发布'],
    unsuitable: ['拖延交付', '把今天的窗口留给无关紧要的修改'],
    timeWindow: '午时前是本月最后一段高效输出时间，抓紧完成核心交付。'
  }
}

export const decisionNodes = [
  { date: '9月12日', pillar: '己丑', tone: 'green', type: '产品框架确认、模块细化' },
  { date: '9月15日', pillar: '壬辰', tone: 'yellow-green', type: '事务性扫尾与轻量决策' },
  { date: '9月16日', pillar: '癸巳', tone: 'green', type: '用户名单、交付模板确认' },
  { date: '9月17日', pillar: '甲午', tone: 'green', type: '首批交付、对外启动' },
  { date: '9月24日', pillar: '辛丑', tone: 'green', type: '财务与定价决策' }
]

export const recordPrompts = [
  { index: '01', title: '决策日志', text: '每次决策时记录时间、情绪、结果，月底回看自己的模式。' },
  { index: '02', title: '此刻我在做什么', text: '每天选一个时间，写下我现在在做什么、为什么做它、明天还会做它吗。' },
  { index: '03', title: '对外文本积累', text: '把关于“辰鉴”的想法写成200字左右的短文本，不求发布，只求存档。' }
]

export const cautionNotes = [
  '你觉得自己“什么都没做”的时候，很可能正在做最重要的事——判断和等待。',
  '若出现“我是不是该现在做点什么”的焦虑，先记下来，等下一个绿灯日再处理。',
  '这个月不需要做到“完美交付”，只需要做到“能够反馈的交付”。'
]

function phaseForDate(dateKey) {
  return phaseDefinitions.find(phase => dateKey >= phase.startDate && dateKey <= phase.endDate)
}

export function getDateEntry(dateKey) {
  const phase = phaseForDate(dateKey)
  const daily = dailyDetails[dateKey]

  if (daily) {
    return {
      ...daily,
      phaseId: phase?.id,
      phaseLabel: phase?.label,
      isPhase: false
    }
  }

  if (!phase) {
    return null
  }

  return {
    ...phase,
    keyword: phase.id === 'rest' ? '积累' : phase.id === 'feedback' ? '反馈' : '调整',
    phaseId: phase.id,
    phaseLabel: phase.label,
    isPhase: true
  }
}

export function createCalendarDays() {
  const days = []
  const cursor = parseDateKey(calendarMeta.startDate)
  const end = parseDateKey(calendarMeta.endDate)

  while (cursor <= end) {
    const date = toDateKey(cursor)
    const entry = getDateEntry(date)
    days.push({
      date,
      day: cursor.getDate(),
      month: cursor.getMonth() + 1,
      weekday: weekdayNames[cursor.getDay()],
      ...entry
    })
    cursor.setDate(cursor.getDate() + 1)
  }

  return days
}

export function resolveDefaultDate(now = new Date()) {
  const today = toDateKey(now)

  if (today < calendarMeta.startDate) {
    return calendarMeta.startDate
  }

  if (today > calendarMeta.endDate) {
    return calendarMeta.endDate
  }

  return today
}

export function isToday(dateKey) {
  return dateKey === currentDateKey()
}
