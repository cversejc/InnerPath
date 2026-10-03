import { reportFragmentTitle } from './stages.js'

const CONTEXT_LABELS = {
  focus_topics: '关注主题',
  selected_topics: '关注主题',
  current_challenge: '本次主要困扰',
  expected_outcomes: '期待获得的帮助',
  issue_duration: '持续时间',
  impact_level: '影响程度',
  decision_status: '目前的决策进度',
  decision_description: '选择情况',
  decision_style: '通常如何做决定',
  additional_info: '补充说明',
  usage_scenario: '使用场景',
  calendar_goal: '当前目标',
  goal: '当前目标',
  self_reported_mbti: '自述 MBTI 类型',
  self_reported_strengths: '自述优势',
  self_reported_patterns: '自述应对方式',
  decision_options: '正在比较的选项',
  work_history: '工作经历补充'
}

const VALUE_LABELS = {
  male: '男', female: '女', solar: '公历', lunar: '农历',
  career: '职业发展', relationship: '亲密关系', family: '家庭议题',
  self: '自我价值', growth: '个人成长', stress: '压力与焦虑', decision: '选择与决策',
  low: '较低', medium: '一般', high: '较高', critical: '很高',
  unknown: '不确定', approximate: '大约时间', exact: '准确时间',
  not_started: '尚未开始', considering: '正在考虑', decided: '已经决定',
  undecided: '尚未决定', unsure: '尚未确定', yes: '是', no: '否'
}

const PROFILE_LABELS = {
  name: '称呼', gender: '性别', birth_year: '出生年', birth_month: '出生月',
  birth_day: '出生日', birth_date: '出生日期', birth_time: '出生时间',
  birth_hour: '出生时', birth_minute: '出生分',
  birth_place: '出生地点', calendar_type: '日期历法', time_accuracy: '出生时间准确度',
  birth_is_leap_month: '是否闰月'
}

const EVIDENCE_KEY_LABELS = {
  'input.additional_info': '用户补充说明',
  'input.selected_topics': '关注主题',
  'input.context.focus_topics': '关注主题',
  'input.context.current_challenge': '本次主要困扰',
  'input.context.expected_outcomes': '期待获得的帮助',
  'input.context.issue_duration': '困扰持续时间',
  'input.context.impact_level': '对生活的影响',
  'input.context.decision_status': '目前的决策进度',
  'input.context.decision_description': '选择情况',
  'input.context.decision_options': '正在比较的选项',
  'input.context.decision_style': '通常如何做决定',
  'input.context.self_reported_strengths': '自述优势',
  'input.context.self_reported_patterns': '自述应对方式',
  'input.context.work_history': '工作经历补充',
  'input.profile.name': '用户称呼',
  'input.profile.gender': '性别',
  'input.profile.birth_year': '出生年',
  'input.profile.birth_month': '出生月',
  'input.profile.birth_day': '出生日',
  'input.profile.birth_date': '出生日期',
  'input.profile.birth_hour': '出生时',
  'input.profile.birth_minute': '出生分',
  'input.profile.birth_time': '出生时间',
  'input.profile.birth_place': '出生地点',
  'input.profile.calendar_type': '日期历法',
  'input.profile.time_accuracy': '出生时间准确度',
  'input.profile.birth_is_leap_month': '是否闰月',
  'system.bazi': '八字测算结果',
  'system.four_pillars': '八字测算结果',
  'system.ziwei': '紫微测算结果',
  'calculated.mingli_foundation.v1': '命理测算依据',
  'calculated.foundation.skill_run': '本次分析采用的测算依据'
}

const STATUS_LABELS = {
  CONFIRMED: '已确认', PROPOSED: '待审核', STALE: '需要复核',
  REJECTED: '已拒绝', OPEN: '待处理', RESOLVED: '已处理',
  ACCEPTED: '已接受', DISMISSED: '已忽略', PASSED: '检查通过',
  BLOCKED: '暂不能交付', PROGRAMMATIC_BLOCKED: '发现必须处理的问题',
  READY: '可以进行最终复核', NOT_RUN: '尚未检查'
}

const ROLE_LABELS = {
  IDENTITY: '个人特质', RESOURCE: '个人资源', SHADOW: '待探索的部分',
  COMPLEX: '内在议题', DEFENSE: '应对方式', CONFLICT: '内在张力',
  PATTERN: '重复模式', BLOCK: '当前卡点', NEED: '重要需要',
  INTEGRATION_DIRECTION: '发展方向', TIMING: '阶段节奏', ACTION: '行动建议',
  CAREER_PATTERN: '职业模式', MOTIVATION_PATTERN: '动力模式',
  INTEGRATED_INSIGHT: '整合观察', ACTION_STRATEGY: '行动策略'
}

const QUALITY_ISSUE_LABELS = {
  FINDING_OVER_REPEATED: '同一专业判断被多段引用',
  source_fidelity: '用户经历需要核对',
  repetition: '段落内容需要精简',
  safety: '确认尊重用户边界',
  block_to_action_link: '行动建议需要对应卡点',
  report_coherence: '报告表达需要复核',
  chapter_coherence: '章节衔接需要调整'
}

const QUALITY_ISSUE_GUIDANCE = {
  FINDING_OVER_REPEATED: '核对各段是否各自承担不同作用；如果只是重复说明，可减少不必要的引用。',
  source_fidelity: '对照用户申请资料检查该段内容，只保留资料能够支持的经历与事实。',
  repetition: '比较相关段落的职责，保留一次完整说明，其余部分改为承接或补充新的角度。',
  safety: '对照用户明确表达的边界，确认报告没有用专业解释替用户作决定或预测结果。',
  block_to_action_link: '为行动建议指出它回应的具体卡点；需要时补上一句承接说明。',
  report_coherence: '通读相邻段落，统一叙述方式并检查前后衔接。',
  chapter_coherence: '补足段落之间的承接，并把具体执行步骤集中在行动章节。'
}

export function isInternalMetadataKey(key) {
  const leafKey = String(key || '').split('.').pop()
  return /^(?:id|.+_id|version|.+_version|created_at|updated_at|user_profile|profile_ref|user|profile|account|record|case|request|workflow|step|task|run|revision)(?:_|$)/i.test(leafKey)
}

function presentValue(value) {
  if (Array.isArray(value)) return value.map(presentValue).filter(Boolean).join('、') || '—'
  if (value && typeof value === 'object') {
    return Object.entries(value)
      .filter(([key, item]) => !isInternalMetadataKey(key)
        || (key === 'profile' && item && typeof item === 'object' && !Array.isArray(item)))
      .map(([key, item]) => `${CONTEXT_LABELS[key] || PROFILE_LABELS[key] || '补充内容'}：${presentValue(item)}`)
      .filter(Boolean)
      .join('；') || '—'
  }
  if (value === true) return '是'
  if (value === false) return '否'
  if (value === null || value === undefined || value === '') return '—'
  const text = String(value).trim()
  return VALUE_LABELS[text.toLowerCase().replace(/[ -]+/g, '_')] || text
}

function calculationSummary(value) {
  if (!value || typeof value !== 'object') return presentValue(value)
  const parts = []
  const bazi = value.bazi || value
  const pillarLabels = { year: '年柱', month: '月柱', day: '日柱', hour: '时柱' }
  const pillars = Object.entries(pillarLabels)
    .map(([key, label]) => {
      const pillar = bazi[key]
      return pillar?.stem && pillar?.branch ? `${label}${pillar.stem}${pillar.branch}` : null
    })
    .filter(Boolean)
  if (pillars.length) parts.push(pillars.join('、'))
  if (bazi.day_master) parts.push(`日主：${bazi.day_master}`)
  if (bazi.note || value.note) parts.push(`测算说明：${bazi.note || value.note}`)

  const ziwei = value.ziwei
  if (ziwei && typeof ziwei === 'object') {
    const palaceLabels = { life_palace: '命宫', career_palace: '官禄宫' }
    for (const [key, label] of Object.entries(palaceLabels)) {
      const palace = ziwei[key]
      if (!palace || typeof palace !== 'object') continue
      const stars = Array.isArray(palace.main_stars) ? palace.main_stars.filter(Boolean).join('、') : ''
      const detail = [palace.branch ? `${palace.branch}宫` : '', stars].filter(Boolean).join('，')
      if (detail) parts.push(`${label}：${detail}`)
    }
  }

  if (parts.length) return parts.join('；')
  return presentValue(value)
}

export function formatConsultantEvidenceValue(value, sourceType = '') {
  return sourceType === 'SYSTEM_CALCULATED' ? calculationSummary(value) : presentValue(value)
}

export function isVisibleConsultantEvidence(item) {
  return !isInternalMetadataKey(item?.evidence_key)
}

export function visibleConsultantEvidence(items = []) {
  const seenCalculations = new Set()
  return items.filter(item => {
    if (!isVisibleConsultantEvidence(item)) return false
    if (item?.source_type !== 'SYSTEM_CALCULATED') return true
    const signature = JSON.stringify(item.value_json)
    if (seenCalculations.has(signature)) return false
    seenCalculations.add(signature)
    return true
  })
}

function profileItems(profile = {}) {
  if (!profile || typeof profile !== 'object') return []
  const birthDate = [profile.birth_year, profile.birth_month, profile.birth_day]
    .every(value => value !== null && value !== undefined && value !== '')
    ? `${profile.birth_year} 年 ${profile.birth_month} 月 ${profile.birth_day} 日`
    : profile.birth_date
  const birthTime = profile.birth_hour !== null && profile.birth_hour !== undefined
    ? `${String(profile.birth_hour).padStart(2, '0')} 时${profile.birth_minute !== null && profile.birth_minute !== undefined ? `${String(profile.birth_minute).padStart(2, '0')} 分` : ''}`
    : profile.birth_time
  const entries = [
    ['name', profile.name],
    ['gender', profile.gender],
    ['birth_date', birthDate],
    ['birth_time', birthTime || '未提供'],
    ['birth_place', profile.birth_place],
    ['calendar_type', profile.calendar_type],
    ['time_accuracy', profile.time_accuracy]
  ]
  return entries
    .filter(([, value]) => value !== null && value !== undefined && value !== '')
    .map(([key, value]) => ({ title: PROFILE_LABELS[key] || key, body: presentValue(value), meta: '申请时留存' }))
}

function contextItems(snapshot = {}) {
  const context = snapshot.context && typeof snapshot.context === 'object' ? snapshot.context : {}
  const entries = Object.entries(context).filter(([key, value]) =>
    Object.prototype.hasOwnProperty.call(CONTEXT_LABELS, key)
    && value !== null
    && value !== undefined
    && value !== ''
    && !(Array.isArray(value) && value.length === 0)
  )
  if (snapshot.additional_info && !entries.some(([key]) => key === 'additional_info')) {
    entries.push(['additional_info', snapshot.additional_info])
  }
  return entries.map(([key, value], index) => ({
    key: `context-${key}-${index}`,
    title: CONTEXT_LABELS[key] || '用户补充信息',
    body: presentValue(value),
    meta: '用户本次申请'
  }))
}

export function buildApplicationProfileItems(snapshot) {
  return profileItems(snapshot?.profile)
}

export function buildApplicationContextItems(snapshot) {
  return contextItems(snapshot)
}

function evidenceTitle(item) {
  if (EVIDENCE_KEY_LABELS[item.evidence_key]) return EVIDENCE_KEY_LABELS[item.evidence_key]
  const key = String(item.evidence_key || '')
  if (key.startsWith('input.profile.')) return PROFILE_LABELS[key.slice('input.profile.'.length)] || '出生资料'
  if (key.startsWith('input.context.')) return CONTEXT_LABELS[key.slice('input.context.'.length)] || '本次申请情境'
  if (key.toLowerCase().includes('ziwei')) return '紫微测算结果'
  if (key.toLowerCase().includes('bazi') || key.toLowerCase().includes('four_pillars')) return '八字测算结果'
  if (item.source_type === 'SYSTEM_CALCULATED') return '系统测算依据'
  if (item.source_type === 'USER_CONTEXT' || item.source_type === 'APPLICATION_CONTEXT') return '本次申请情境'
  return '用户提交的资料'
}

export function reportEvidenceTitle(item) {
  return evidenceTitle(item || {})
}

function evidenceItems(evidence = [], keys = null) {
  const wanted = keys ? new Set(keys) : null
  return visibleConsultantEvidence(evidence)
    .filter(item => item.status === 'ACTIVE'
      && (!wanted || wanted.has(item.evidence_key)))
    .map(item => ({
      key: item.evidence_key,
      title: evidenceTitle(item),
      body: formatConsultantEvidenceValue(item.value_json, item.source_type),
      meta: item.source_type === 'SYSTEM_CALCULATED' ? '系统测算' : item.source_type === 'EXTERNAL_REFERENCE' ? '外部资料' : '用户提供'
    }))
}

function excerpt(value, limit = 280) {
  const text = String(value || '').replace(/\s+/g, ' ').trim()
  return text.length > limit ? `${text.slice(0, limit)}…` : text
}

function sourceEvidenceTitles(item, evidenceByKey) {
  const refs = Array.isArray(item.evidence_refs)
    ? item.evidence_refs
    : (item.source_snapshot?.evidence || []).map(source => source.evidence_key)
  return [...new Set(refs.map(key => evidenceByKey.get(key)).filter(Boolean))].join('、')
}

function sourceFindingTitles(item, findingsByKey) {
  return [...new Set((item.source_snapshot?.findings || []).map(source => {
    if (typeof source === 'string') return findingsByKey.get(source)?.claim
    return source?.claim || findingsByKey.get(source?.finding_key)?.claim
  }).filter(Boolean))].join('；')
}

function findingCards(findings, evidenceByKey) {
  return findings.map(item => ({
    key: item.finding_key,
    title: item.claim,
    body: `专业角色：${ROLE_LABELS[item.semantic_role] || '综合观察'} · 把握程度：${({ LOW: '较低', MEDIUM: '一般', HIGH: '较高' })[item.confidence] || '一般'}`,
    meta: STATUS_LABELS[item.status] || '专业判断',
    source: sourceEvidenceTitles(item, evidenceByKey) ? `资料来源：${sourceEvidenceTitles(item, evidenceByKey)}` : '尚未关联具体资料'
  }))
}

function fragmentCards(fragments, evidenceByKey, findingsByKey = new Map()) {
  return fragments.map(item => {
    const evidenceSources = sourceEvidenceTitles(item, evidenceByKey)
    const findingSources = sourceFindingTitles(item, findingsByKey)
    return {
      key: item.fragment_key,
      title: item.title || '分析内容',
      body: excerpt(item.content),
      meta: STATUS_LABELS[item.status] || '分析内容',
      source: evidenceSources || findingSources ? `依据：${evidenceSources || findingSources}` : '尚未关联资料来源'
    }
  })
}

function planCards(plan, findingsByKey) {
  if (!plan) return []
  const planJson = plan.plan_json || {}
  const included = (planJson.must_include_findings || [])
    .map(key => findingsByKey.get(key)?.claim)
    .filter(Boolean)
  return [{
    key: `narrative-${plan.id}`,
    title: excerpt(planJson.core_theme, 180) || '已保存报告主线',
    body: included.length ? `主线重点：${included.join('；')}` : '报告主线已保存，尚未指定重点判断。',
    meta: STATUS_LABELS[plan.status] || '报告主线'
  }]
}

function plannedFragmentCards(plan, findingsByKey) {
  const fragments = plan?.plan_json?.content_plan?.fragments || []
  return fragments.map((fragment, index) => ({
    key: fragment.fragment_key || `planned-${index}`,
    title: reportFragmentTitle(fragment.fragment_key, fragment.title || fragment.chapter || `第 ${index + 1} 段`),
    body: excerpt(fragment.purpose || fragment.must_cover?.join('；') || '按报告主线展开。'),
    meta: (fragment.finding_refs || []).map(key => findingsByKey.get(key)?.claim).filter(Boolean).join('；') || '尚未标注重点判断'
  }))
}

function reportFragmentCards(fragments, findingsByKey, evidenceByKey) {
  return fragments
    .filter(item => item.fragment_type === 'REPORT')
    .map(item => {
      const findingSources = sourceFindingTitles(item, findingsByKey)
      const evidenceSources = sourceEvidenceTitles(item, evidenceByKey)
      return {
        key: item.fragment_key,
        title: reportFragmentTitle(item.fragment_key, item.title || '报告正文'),
        body: excerpt(item.content),
        meta: STATUS_LABELS[item.status] || '报告正文',
        source: findingSources || evidenceSources
          ? `主要依据：${[findingSources, evidenceSources].filter(Boolean).join('；')}`
          : '尚未关联已确认依据'
      }
    })
}

function qualityCards(quality = {}, content = {}) {
  const issues = quality.issues || []
  if (!issues.length) {
    const status = qualitySummaryLabel(quality)
    const body = quality.can_approve
      ? '所有检查项均已处理，可以进入最终人工复核。'
      : quality.latest_validator_run
        ? '报告内容有更新，请重新运行交付前检查。'
        : '运行交付前检查后，结果会显示在这里。'
    return [{ key: 'quality-state', title: `检查结果：${status}`, body, meta: '交付前检查' }]
  }
  const fragmentsByKey = new Map((content.fragments || []).map(item => [item.fragment_key, item]))
  const findingsByKey = new Map((content.findings || []).map(item => [item.finding_key, item]))
  return issues.map(issue => {
    const targetFragment = fragmentsByKey.get(issue.target_fragment_key)
    const targetTitle = targetFragment
      ? reportFragmentTitle(issue.target_fragment_key, targetFragment.title)
      : ''
    const repeatedFinding = issue.issue_type === 'FINDING_OVER_REPEATED'
      ? findingsByKey.get(issue.evidence_json?.finding_key)?.claim
      : ''
    const title = QUALITY_ISSUE_LABELS[issue.issue_type] || '报告内容需要复核'
    const detail = QUALITY_ISSUE_GUIDANCE[issue.issue_type]
      || consultantText(issue.suggestion, '对照报告正文和对应资料，记录处理结论后再继续。')
    const count = issue.evidence_json?.fragment_count
    const severityLabel = {
      BLOCK: '必须处理',
      MAJOR: '需要处理',
      MINOR: '建议复核',
      WARN: '建议处理'
    }[issue.severity] || '待复核'

    return {
      key: `quality-${issue.id}`,
      title: issue.issue_type === 'FINDING_OVER_REPEATED' && repeatedFinding
        ? `${title}：${excerpt(repeatedFinding, 120)}`
        : targetTitle ? `${targetTitle} · ${title}` : title,
      body: issue.issue_type === 'FINDING_OVER_REPEATED' && count
        ? `目前有 ${count} 段引用。${detail}`
        : detail,
      meta: `${severityLabel} · ${STATUS_LABELS[issue.status] || '待处理'}`
    }
  })
}

export function qualitySummaryLabel(quality = {}, fallbackStatus = '') {
  const status = quality.quality_status || fallbackStatus
  const runStatus = quality.latest_validator_run?.status
  const openCount = Number(quality.open_count ?? (quality.issues || []).filter(issue => issue.status === 'OPEN').length)

  if (quality.can_approve) return '可以进入最终复核'
  if (runStatus === 'PENDING' || runStatus === 'RUNNING') return '正在检查'
  if (runStatus === 'FAILED') return '检查失败，请重试'
  if (runStatus === 'COMPLETED' || status === 'COMPLETED') {
    return openCount ? `检查完成 · ${openCount} 项待处理` : '内容有更新，需重新检查'
  }
  if (status === 'PROGRAMMATIC_BLOCKED') return '发现必须处理的问题'
  if (status === 'BLOCKED') return '暂不能交付'
  return '尚未检查'
}

function candidateCards(run, content, evidenceByKey) {
  if (!run?.output_parsed) return []
  const findings = content?.findings || []
  const fragments = content?.fragments || []
  const output = run.output_parsed
  const cards = []

  for (const candidate of output.findings || []) {
    if (findings.some(item => item.finding_key === candidate.finding_key && item.source_skill_run_id === run.id)) continue
    const source = sourceEvidenceTitles(candidate, evidenceByKey)
    const claim = consultantText(candidate.claim, '这条建议暂时无法显示，请前往专业判断查看。')
    cards.push({
      key: `suggestion-${run.id}-${candidate.finding_key}`,
      title: claim,
      body: `把握程度：${({ LOW: '较低', MEDIUM: '一般', HIGH: '较高' })[candidate.confidence] || '一般'} · 尚未加入审核。`,
      meta: candidate.kind === 'SIGNAL' ? '待验证线索' : '专业判断建议',
      source: source ? `资料来源：${source}` : '尚未关联具体资料'
    })
  }

  for (const candidate of output.analysis_fragments || []) {
    if (fragments.some(item => item.fragment_key === candidate.fragment_key && item.source_skill_run_id === run.id)) continue
    const source = sourceEvidenceTitles(candidate, evidenceByKey)
    cards.push({
      key: `suggestion-${run.id}-${candidate.fragment_key}`,
      title: consultantText(candidate.title, '分析内容建议'),
      body: excerpt(consultantText(candidate.content, '这段建议暂时无法显示，请前往报告内容查看。')),
      meta: '分析内容建议 · 尚未加入审核',
      source: source ? `资料来源：${source}` : '尚未关联具体资料'
    })
  }

  return cards
}

function consultantText(value, fallback) {
  const text = String(value || '').trim()
  return text && !/[A-Za-z]{2,}/.test(text) ? text : fallback
}

export function buildWorkbenchInputGroups({ stage, reportCase, content, narrativePlan, quality }) {
  if (!stage || !reportCase) return []
  const snapshot = reportCase.application_snapshot || {}
  const steps = reportCase.workflow_instance?.steps || []
  const current = steps.find(step => step.step_key === stage.stepKey)
  const upstreamIds = new Set(steps
    .filter(step => current && step.sequence_no < current.sequence_no)
    .map(step => step.id))
  const findings = (content?.findings || []).filter(item => item.status === 'CONFIRMED')
  const upstreamFindings = findings.filter(item => upstreamIds.has(item.owner_step_task_id))
  const confirmedFindings = ['S2', 'S3', 'S4'].includes(stage.stepKey)
    ? upstreamFindings
    : stage.stepKey === 'S1' ? [] : findings
  const analysisFragments = (content?.fragments || []).filter(item =>
    item.fragment_type === 'ANALYSIS'
    && item.status === 'CONFIRMED'
    && (stage.stepKey === 'S5' || stage.stepKey === 'S6' || upstreamIds.has(item.owner_step_task_id))
  )
  const relevantFindings = ['S2', 'S3', 'S4'].includes(stage.stepKey)
    ? upstreamFindings
    : stage.stepKey === 'S1' ? [] : findings
  const evidenceByKey = new Map((content?.evidence || []).map(item => [item.evidence_key, evidenceTitle(item)]))
  const findingsByKey = new Map(findings.map(item => [item.finding_key, item]))
  const allRefs = [...new Set(relevantFindings.flatMap(item => item.evidence_refs || []))]
  const inputItems = {
    profile: profileItems(snapshot.profile),
    context: contextItems(snapshot),
    systemEvidence: evidenceItems(content?.evidence || []).filter(item => item.meta === '系统测算'),
    referencedEvidence: evidenceItems(content?.evidence || [], allRefs),
    upstreamFindings: findingCards(upstreamFindings, evidenceByKey),
    confirmedFindings: findingCards(confirmedFindings, evidenceByKey),
    upstreamFragments: fragmentCards(analysisFragments, evidenceByKey, findingsByKey),
    confirmedFragments: fragmentCards(analysisFragments, evidenceByKey, findingsByKey),
    narrativePlan: planCards(narrativePlan, findingsByKey),
    plannedFragments: plannedFragmentCards(narrativePlan, findingsByKey),
    reportFragments: reportFragmentCards(
      (content?.fragments || []).filter(item => item.status === 'CONFIRMED'),
      findingsByKey,
      evidenceByKey
    ),
    qualityIssues: qualityCards(quality, content || {})
  }

  return stage.inputGroups.map(group => ({
    ...group,
    items: inputItems[group.key] || []
  }))
}

export function classifyWorkbenchStepView(viewStep, currentStep) {
  if (!viewStep) return 'NONE'
  if (currentStep && viewStep.id === currentStep.id) return 'CURRENT'
  if (
    currentStep
    && viewStep.sequence_no > currentStep.sequence_no
    && viewStep.status === 'PENDING'
  ) return 'UPCOMING'
  return 'HISTORY'
}

export function buildWorkbenchStageOutputs({ stage, reportCase, content, narrativePlan, quality, analysisRuns = [] }) {
  if (!stage || !reportCase) return []
  const steps = reportCase.workflow_instance?.steps || []
  const step = steps.find(item => item.step_key === stage.stepKey)
  const findings = content?.findings || []
  const findingsByKey = new Map(findings.map(item => [item.finding_key, item]))
  const evidenceByKey = new Map((content?.evidence || []).map(item => [item.evidence_key, evidenceTitle(item)]))

  if (['S1', 'S2', 'S3', 'S4'].includes(stage.stepKey)) {
    const latestRun = analysisRuns
      .filter(run => run.target_type === 'REPORT_ANALYSIS_DRAFT' && run.target_key === stage.stepKey && run.status === 'COMPLETED')
      .filter(run => run.context_snapshot?.analysis_activation_no === step?.activation_no)
      .sort((left, right) => right.id - left.id)[0]
    return [
      ...findingCards(findings.filter(item => item.owner_step_task_id === step?.id), evidenceByKey),
      ...fragmentCards((content?.fragments || []).filter(item =>
        item.fragment_type === 'ANALYSIS' && item.owner_step_task_id === step?.id
      ), evidenceByKey, findingsByKey),
      ...candidateCards(latestRun, content, evidenceByKey)
    ]
  }
  if (stage.stepKey === 'S5') {
    return [
      ...planCards(narrativePlan, findingsByKey),
      ...reportFragmentCards(
        (content?.fragments || []).filter(item => item.owner_step_task_id === step?.id),
        findingsByKey,
        evidenceByKey
      )
    ]
  }
  return qualityCards(quality)
}
