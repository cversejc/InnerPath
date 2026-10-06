import { parseLegacyReportContent } from './report-content.js'
import { paginateReportSection } from './reader-pagination.js'
import { parseReportMarkdownStructure } from './report-markdown-structure.js'

const REPORT_LABELS = {
  action_plan: '行动方案',
  action: '具体行动',
  actions: '行动方案',
  area: '行动主题',
  background: '背景说明',
  before: '调整前',
  beliefs: '核心信念',
  career_guidance: '方向与节奏',
  challenges: '挑战',
  conclusion: '结论',
  core_drive: '核心驱动力',
  core_drive_and_talents: '核心驱动力与天赋',
  core_beliefs: '核心信念',
  core_traits: '核心特质',
  current_issues: '关注议题',
  current_stage: '当前阶段',
  day: '日柱',
  day_master: '日主',
  development: '发展建议',
  development_suggestions: '发展建议',
  energy: '能量特质',
  energy_balance: '能量平衡点',
  energy_profile: '能量特质',
  environment: '现实环境',
  exercises: '成长实验',
  growth_experiments: '成长实验',
  growth_direction: '成长方向',
  growth_resources: '成长资源',
  insights: '关键发现',
  life_direction: '人生方向',
  life_stage_map: '人生阶段地图',
  life_stages: '人生阶段',
  life_theme: '人生主题',
  mode: '运行模式',
  next_steps: '下一步行动',
  personal_analysis: '个人分析',
  personal_growth: '个人成长',
  personal_profile: '个人画像',
  relationship_pattern: '关系模式',
  report: '报告正文',
  resources: '支持资源',
  result: '分析结果',
  stages: '阶段地图',
  strengths: '优势',
  timeline: '时间建议',
  to: '调整后',
  type: '类型',
  work_style: '工作风格',
  topics: '关注议题',
  user_issues: '用户议题',
  user_topics: '用户议题',
  pattern: '模式',
  thinking_pattern: '思维模式',
  personal_coordinates: '个人坐标',
  psychological_mechanism: '心理机制',
  strategy: '应对策略',
  self_check: '自检清单',
  decision_checklist: '决策自检',
  action_steps: '行动步骤',
  after: '调整后',
  from: '调整前',
  phase: '阶段',
  patterns: '格局',
  style: '关系风格',
  suitable_paths: '适合方向',
  summary: '总结与寄语',
  period: '时间阶段',
  age: '年龄阶段',
  time: '时间'
}

function hasReportValue(value) {
  if (value == null) return false
  if (typeof value === 'string') return Boolean(value.trim())
  if (Array.isArray(value)) return value.some(hasReportValue)
  if (typeof value === 'object') return Object.values(value).some(hasReportValue)
  return true
}

function textValue(value) {
  if (typeof value === 'string') return value.trim()
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return ''
}

function labelForKey(key) {
  const normalized = String(key).replace(/([a-z])([A-Z])/g, '$1_$2').toLowerCase()
  return REPORT_LABELS[normalized] || '补充内容'
}

function reportBodyBlocks(blocks = []) {
  return blocks.map(block => ({
    ...block,
    depth: Math.max(0, (Number(block.depth) || 0) - 1),
    children: reportBodyBlocks(block.children || [])
  }))
}

const BLOCK_META_KEYS = new Set([
  'title', 'heading', 'label', 'name', 'area', 'subtitle', 'icon', 'id', 'kind',
  'display_type', 'displaytype', 'presentation_type', 'presentationtype', 'render_type', 'rendertype',
  'content', 'text', 'body', 'description', 'action', 'items', 'actions', 'points', 'highlights',
  'sections', 'subsections', 'children', 'stages', 'from', 'to', 'before', 'after',
  'from_label', 'to_label', 'before_label', 'after_label', 'chapter', 'content_revision',
  'fragment_key', 'revision_no', 'section_key', 'section_title', 'semantic_revision',
  'sequence_no', 'source_narrative_plan_id', 'source_skill_run_id', 'source_snapshot'
])

const DISPLAY_TYPE_ALIASES = {
  callout: 'takeaway',
  conclusion: 'takeaway',
  takeaway: 'takeaway',
  insight: 'takeaway',
  quote: 'quote',
  flow: 'flow',
  process: 'flow',
  sequence: 'flow',
  comparison: 'comparison',
  contrast: 'comparison',
  timeline: 'timeline',
  stages: 'timeline',
  experiment: 'action',
  action: 'action',
  action_plan: 'action',
  checklist: 'checklist',
  tags: 'tags',
  keywords: 'tags',
  list: 'list',
  prose: 'prose'
}

function displayTypeFor(value, title, hasItems) {
  const explicit = value?.display_type || value?.displayType || value?.presentation_type
    || value?.presentationType || value?.render_type || value?.renderType || value?.kind
  const normalizedType = String(explicit || '').replace(/([a-z])([A-Z])/g, '$1_$2').toLowerCase()
  if (DISPLAY_TYPE_ALIASES[normalizedType]) return DISPLAY_TYPE_ALIASES[normalizedType]
  if (value?.type && DISPLAY_TYPE_ALIASES[String(value.type).toLowerCase()]) {
    return DISPLAY_TYPE_ALIASES[String(value.type).toLowerCase()]
  }
  if (value?.from != null && value?.to != null || value?.before != null && value?.after != null) return 'comparison'
  if (Array.isArray(value?.stages) || (Array.isArray(value?.timeline) && value.timeline.some(item => item && typeof item === 'object'))) return 'timeline'
  if (value?.action && (value?.area || value?.timeline || value?.period || value?.time)) return 'action'
  const normalizedTitle = String(title || '').replace(/[\s·・]/g, '')
  if (/^(结论|核心结论|关键发现|最重要的发现|重要提醒)$/.test(normalizedTitle)) return 'takeaway'
  if (/^(决策自检|自检清单|检查清单)$/.test(normalizedTitle)) return 'checklist'
  if (hasItems && /^(关键词|核心特质|优势|关注议题|支持资源|标签)$/.test(normalizedTitle)) return 'tags'
  return hasItems ? 'list' : 'prose'
}

function blockMetadata(value, displayType) {
  const entries = []
  const candidates = [
    ['timeline', '时间'], ['period', '阶段'], ['age', '年龄'], ['date', '日期'], ['time', '时间']
  ]
  if (displayType === 'action' || displayType === 'timeline') {
    for (const [key, label] of candidates) {
      const text = textValue(value?.[key])
      if (text) entries.push({ label, value: text })
    }
  }
  return entries
}

function isRenderableBlock(block) {
  return Boolean(block && (
    String(block.content || '').trim()
    || block.items?.length
    || block.comparison?.from
    || block.comparison?.to
    || block.metadata?.some(item => item.value)
    || block.children?.some(isRenderableBlock)
  ))
}

export function normalizeReportBlock(value, titleHint = '', id = 'block', depth = 0) {
  if (!hasReportValue(value)) return null

  if (Array.isArray(value)) {
    const primitiveItems = value.map(textValue).filter(Boolean)
    const objectItems = value.filter(item => item && typeof item === 'object')
    return {
      id,
      title: titleHint || (objectItems.length ? '' : '补充内容'),
      subtitle: '',
      content: '',
      items: primitiveItems,
      children: objectItems.map((item, index) => normalizeReportBlock(item, '', `${id}-${index}`, depth + 1)).filter(isRenderableBlock),
      displayType: primitiveItems.length ? 'list' : 'prose',
      depth
    }
  }

  if (typeof value !== 'object') {
    return { id, title: titleHint, subtitle: '', content: textValue(value), items: [], children: [], displayType: 'prose', depth }
  }

  const title = textValue(value.title || value.heading || value.label || value.name || value.area) || titleHint
  const content = textValue(value.content ?? value.text ?? value.body ?? value.description ?? value.action)
  const subtitle = textValue(value.subtitle)
  const itemValue = value.items ?? value.actions ?? value.points ?? value.highlights
  const itemValues = Array.isArray(itemValue) ? itemValue : hasReportValue(itemValue) ? [itemValue] : []
  const items = itemValues.map(textValue).filter(Boolean)
  const displayType = displayTypeFor(value, title, items.length > 0)
  const comparison = displayType === 'comparison'
    ? {
        fromLabel: textValue(value.from_label || value.before_label) || '之前',
        from: textValue(value.from ?? value.before),
        toLabel: textValue(value.to_label || value.after_label) || '之后',
        to: textValue(value.to ?? value.after)
      }
    : null
  const children = []
  itemValues.filter(item => item && typeof item === 'object').forEach((item, index) => {
    const child = normalizeReportBlock(item, '', `${id}-item-${index}`, depth + 1)
    if (child) children.push(child)
  })
  const nested = value.subsections ?? value.children ?? value.sections ?? value.stages
    ?? (Array.isArray(value.timeline) ? value.timeline : undefined)

  if (Array.isArray(nested)) {
    nested.forEach((item, index) => {
      const child = normalizeReportBlock(item, '', `${id}-child-${index}`, depth + 1)
      if (child) children.push(child)
    })
  } else if (hasReportValue(nested)) {
    const child = normalizeReportBlock(nested, '内容', `${id}-child`, depth + 1)
    if (child) children.push(child)
  }

  const seenFieldKeys = new Set()
  for (const [key, childValue] of Object.entries(value)) {
    const normalizedKey = String(key).replace(/([a-z])([A-Z])/g, '$1_$2').toLowerCase()
    if (
      BLOCK_META_KEYS.has(normalizedKey)
      || normalizedKey === 'type'
      || (['action', 'timeline'].includes(displayType) && ['timeline', 'period', 'age', 'date', 'time'].includes(normalizedKey))
      || seenFieldKeys.has(normalizedKey)
      || !hasReportValue(childValue)
    ) continue
    seenFieldKeys.add(normalizedKey)
    const child = normalizeReportBlock(childValue, labelForKey(key), `${id}-${key}`, depth + 1)
    if (child) children.push(child)
  }

  const renderableChildren = children.filter(isRenderableBlock)
  return {
    id,
    title,
    subtitle,
    content,
    items,
    children: renderableChildren,
    depth,
    displayType,
    comparison,
    metadata: blockMetadata(value, displayType)
  }
}

function sectionFromNode(key, value, index) {
  const root = normalizeReportBlock(value, labelForKey(key), `section-${index}`)
  if (!root) return null
  if (
    !root.content
    && !root.items.length
    && !root.children.length
    && !root.comparison?.from
    && !root.comparison?.to
    && !root.metadata?.length
  ) return null
  return {
    id: root.id,
    title: root.title || labelForKey(key),
    subtitle: root.subtitle,
    content: root.content,
    items: root.items,
    blocks: reportBodyBlocks(root.children),
    displayType: root.displayType,
    comparison: root.comparison,
    metadata: root.metadata,
    kind: 'content'
  }
}

function foundationSection(data, index = 0) {
  if (!hasReportValue(data)) return null
  const foundationData = data && typeof data === 'object' ? data : { content: textValue(data) }
  const extras = Object.fromEntries(Object.entries(foundationData).filter(([key]) => !['bazi', 'ziwei'].includes(key)))
  return {
    id: `foundation-${index}`,
    title: '命理基础',
    subtitle: '',
    kind: 'foundation',
    foundationData,
    foundationExtras: normalizeReportBlock(extras, '', 'foundation-extra'),
    blocks: []
  }
}

function structuredEntries(value) {
  if (Array.isArray(value)) {
    return value.map((item, index) => [item?.key || item?.id || `section-${index}`, item])
  }
  if (value && typeof value === 'object') {
    if (Array.isArray(value.sections) && !value.title && !value.type) {
      const metadata = Object.entries(value).filter(([key]) => key !== 'sections')
      return [...metadata, ...structuredEntries(value.sections)]
    }
    return Object.entries(value)
  }
  return []
}

const DELIVERY_SECTION_TITLES = {
  identity: '你是谁',
  challenge: '卡在哪',
  direction: '往哪去',
  ending: '带回日常'
}

function deliverySections(value) {
  if (!Array.isArray(value) || !value.some(item => (
    item && typeof item === 'object'
    && (item.section_key || item.section_title || item.fragment_key)
  ))) return null

  const groups = new Map()
  for (const item of value) {
    if (!item || typeof item !== 'object') continue
    const fragmentKey = textValue(item.fragment_key)
    const sectionKey = textValue(item.section_key) || 'additional'
    const groupKey = fragmentKey === 'report.ending' ? 'ending' : sectionKey
    const groupTitle = DELIVERY_SECTION_TITLES[groupKey]
      || textValue(item.section_title)
      || '补充内容'
    let group = groups.get(groupKey)
    if (!group) {
      group = { key: groupKey, title: groupTitle, fragments: [] }
      groups.set(groupKey, group)
    }
    group.fragments.push({
      title: textValue(item.title || item.heading || item.label),
      content: textValue(item.content ?? item.text ?? item.body ?? item.description)
    })
  }

  return [...groups.values()]
    .map((group, index) => sectionFromNode(group.key, {
      title: group.title,
      subsections: group.fragments
    }, index))
    .filter(Boolean)
}

function summaryFrom(value) {
  const block = normalizeReportBlock(value, '总结', 'summary')
  if (!block) return null
  const needsPresentationBlock = Boolean(
    block.items.length
    || block.comparison?.from
    || block.comparison?.to
    || block.metadata?.length
    || block.displayType !== 'prose'
  )
  return {
    id: block.id,
    title: block.title || '总结与寄语',
    content: needsPresentationBlock ? '' : block.content,
    blocks: [
      ...(needsPresentationBlock ? [{
        ...block,
        id: `${block.id}-lead`,
        title: '',
        depth: 0,
        children: []
      }] : []),
      ...reportBodyBlocks(block.children)
    ]
  }
}

function hasStructuredContent(sections, summary) {
  return sections.some(section => section.kind !== 'foundation')
    || Boolean(summary?.content || summary?.blocks.length)
}

function finalizeDocument(sections, summary) {
  const normalizedSections = sections.filter(Boolean).map(section => ({
    ...section,
    readerPages: paginateReportSection(section)
  }))
  const normalizedSummary = summary
    ? {
        ...summary,
        id: summary.id || 'summary',
        readerPages: paginateReportSection({ ...summary, id: summary.id || 'summary' })
      }
    : null
  return { sections: normalizedSections, summary: normalizedSummary }
}

export function buildReportDocument(report, { foundationData = null, markdown = '', reportTitle = '' } = {}) {
  const contentPayload = report.contentPayload || {}
  const structured = report.structuredSections || contentPayload.structuredSections || contentPayload.structured_sections
  const sections = []
  let summaryValue = null
  let resolvedFoundation = hasReportValue(foundationData)
    ? foundationData
    : hasReportValue(contentPayload.foundationData)
      ? contentPayload.foundationData
      : contentPayload.foundation_data || null
  let hasFoundationSection = false

  const deliveredSections = deliverySections(structured)
  if (deliveredSections) {
    sections.push(...deliveredSections)
  } else {
    for (const [key, value] of structuredEntries(structured)) {
      const nodeType = String(value?.type || '').toLowerCase()
      const normalizedKey = String(key).replace(/([a-z])([A-Z])/g, '$1_$2').toLowerCase()

      if (normalizedKey === 'summary' || nodeType === 'summary') {
        summaryValue = value
        continue
      }

      if (normalizedKey === 'foundation' || nodeType === 'foundation') {
        resolvedFoundation = value?.data ?? value?.foundation_data ?? value?.content ?? value
        const section = foundationSection(resolvedFoundation, sections.length)
        if (section) sections.push(section)
        hasFoundationSection = Boolean(section)
        continue
      }

      if (['topics', 'user_issues', 'user_topics'].includes(normalizedKey) && Array.isArray(value)) {
        value.forEach((topic, index) => {
          const section = sectionFromNode(topic?.title || `topic-${index}`, topic, sections.length)
          if (section) sections.push(section)
        })
        continue
      }

      const section = sectionFromNode(key, value, sections.length)
      if (section) sections.push(section)
    }
  }

  if (hasReportValue(resolvedFoundation) && !hasFoundationSection && sections.length) {
    sections.unshift(foundationSection(resolvedFoundation, 0))
  } else if (hasReportValue(resolvedFoundation) && !hasFoundationSection) {
    const section = foundationSection(resolvedFoundation, 0)
    if (section) sections.push(section)
  }

  let summary = summaryFrom(summaryValue)
  if (hasStructuredContent(sections, summary)) {
    return finalizeDocument(sections, summary || summaryFrom(report.summary))
  }

  if (markdown.trim()) {
    const parsed = parseReportMarkdownStructure(markdown, { reportTitle })
    const markdownSections = [...parsed.sections]
    if (resolvedFoundation) markdownSections.unshift(foundationSection(resolvedFoundation, 0))
    return finalizeDocument(markdownSections, parsed.summary || summaryFrom(report.summary))
  }

  const domainSections = [
    ['energyProfile', '能量特质'],
    ['relationshipPattern', '关系模式'],
    ['careerGuidance', '方向与节奏'],
    ['personalGrowth', '成长行动']
  ]
  for (const [key, title] of domainSections) {
    const value = report[key]
    if (!hasReportValue(value)) continue
    const section = sectionFromNode(title, { ...value, title: value.title || title }, sections.length)
    if (section) sections.push(section)
  }

  if (hasReportValue(resolvedFoundation) && !sections.some(section => section.kind === 'foundation')) {
    sections.unshift(foundationSection(resolvedFoundation, 0))
  }

  summary = summaryFrom(report.summary)
  return finalizeDocument(sections, summary)
}

export function createReportDocument(report) {
  const contentPayload = report.contentPayload || {}
  let foundationData = contentPayload.foundation_data ?? contentPayload.foundationData ?? null
  let markdown = textValue(report.aiGeneratedContent)

  if (!hasReportValue(foundationData) && markdown) {
    const legacyContent = parseLegacyReportContent(markdown)
    foundationData = legacyContent.foundationData
    markdown = legacyContent.contentWithoutFoundation
  }

  const title = (textValue(report.title) || '人生说明书').replace(/^辰鉴[·・]\s*/, '')
  const model = buildReportDocument(report, { foundationData, markdown, reportTitle: title })
  return {
    id: report.id ?? null,
    title,
    recipient: textValue(report.basicInfo?.name),
    reportDate: textValue(report.basicInfo?.reportDate),
    sections: model.sections,
    summary: model.summary
  }
}
