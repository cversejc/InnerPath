import { parseLegacyReportContent } from './report-content.js'

const REPORT_LABELS = {
  action: '具体行动',
  action_plan: '行动方案',
  actions: '行动方案',
  area: '行动主题',
  challenges: '挑战',
  core_beliefs: '核心信念',
  core_traits: '核心特质',
  current_issues: '关注议题',
  day_master: '日主',
  development_suggestions: '发展建议',
  growth_direction: '成长方向',
  patterns: '格局',
  resources: '支持资源',
  strengths: '优势',
  style: '关系风格',
  suitable_paths: '适合方向',
  summary: '总结',
  timeline: '时间建议',
  type: '类型',
  work_style: '工作风格'
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
  return REPORT_LABELS[normalized] || normalized.replace(/_/g, ' ')
}

const BLOCK_META_KEYS = new Set([
  'title', 'heading', 'label', 'name', 'area', 'subtitle', 'icon', 'id',
  'content', 'text', 'body', 'description', 'action', 'items', 'actions', 'points', 'highlights',
  'sections', 'subsections', 'children'
])

export function normalizeReportBlock(value, titleHint = '', id = 'block') {
  if (!hasReportValue(value)) return null

  if (Array.isArray(value)) {
    const primitiveItems = value.map(textValue).filter(Boolean)
    const objectItems = value.filter(item => item && typeof item === 'object')
    return {
      id,
      title: titleHint,
      subtitle: '',
      content: '',
      items: primitiveItems,
      children: objectItems.map((item, index) => normalizeReportBlock(item, '', `${id}-${index}`)).filter(Boolean)
    }
  }

  if (typeof value !== 'object') {
    return { id, title: titleHint, subtitle: '', content: textValue(value), items: [], children: [] }
  }

  const title = textValue(value.title || value.heading || value.label || value.name || value.area) || titleHint
  const content = textValue(value.content ?? value.text ?? value.body ?? value.description ?? value.action)
  const subtitle = textValue(value.subtitle)
  const itemValue = value.items ?? (content ? null : value.actions ?? value.points ?? value.highlights)
  const itemValues = Array.isArray(itemValue) ? itemValue : hasReportValue(itemValue) ? [itemValue] : []
  const items = itemValues.map(textValue).filter(Boolean)
  const children = []
  itemValues.filter(item => item && typeof item === 'object').forEach((item, index) => {
    const child = normalizeReportBlock(item, '', `${id}-item-${index}`)
    if (child) children.push(child)
  })
  const nested = value.subsections ?? value.children ?? value.sections

  if (Array.isArray(nested)) {
    nested.forEach((item, index) => {
      const child = normalizeReportBlock(item, '', `${id}-child-${index}`)
      if (child) children.push(child)
    })
  } else if (hasReportValue(nested)) {
    const child = normalizeReportBlock(nested, '内容', `${id}-child`)
    if (child) children.push(child)
  }

  const seenFieldKeys = new Set()
  for (const [key, childValue] of Object.entries(value)) {
    const normalizedKey = String(key).replace(/([a-z])([A-Z])/g, '$1_$2').toLowerCase()
    const structuralType = ['foundation', 'energy', 'topic', 'summary', 'section'].includes(String(childValue).toLowerCase())
    if (
      BLOCK_META_KEYS.has(normalizedKey)
      || (normalizedKey === 'type' && structuralType)
      || seenFieldKeys.has(normalizedKey)
      || !hasReportValue(childValue)
    ) continue
    seenFieldKeys.add(normalizedKey)
    const child = normalizeReportBlock(childValue, labelForKey(key), `${id}-${key}`)
    if (child) children.push(child)
  }

  return { id, title, subtitle, content, items, children }
}

function sectionFromNode(key, value, index) {
  const root = normalizeReportBlock(value, labelForKey(key), `section-${index}`)
  if (!root) return null
  if (!root.content && !root.items.length && !root.children.length) return null
  return {
    id: root.id,
    title: root.title || labelForKey(key),
    subtitle: root.subtitle,
    content: root.content,
    items: root.items,
    blocks: root.children,
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

function summaryFrom(value) {
  const block = normalizeReportBlock(value, '总结', 'summary')
  if (!block) return null
  return {
    content: block.content,
    blocks: [...(block.items.length ? [{ ...block, title: block.title || '总结' }] : []), ...block.children]
  }
}

function hasStructuredContent(sections, summary) {
  return sections.some(section => section.kind !== 'foundation')
    || Boolean(summary?.content || summary?.blocks.length)
}

export function buildReportDocument(report, { foundationData = null, markdown = '' } = {}) {
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

    if (normalizedKey === 'topics' && Array.isArray(value)) {
      value.forEach((topic, index) => {
        const section = sectionFromNode(topic?.title || `topic-${index}`, topic, sections.length)
        if (section) sections.push(section)
      })
      continue
    }

    const section = sectionFromNode(key, value, sections.length)
    if (section) sections.push(section)
  }

  if (hasReportValue(resolvedFoundation) && !hasFoundationSection && sections.length) {
    sections.unshift(foundationSection(resolvedFoundation, 0))
  } else if (hasReportValue(resolvedFoundation) && !hasFoundationSection) {
    const section = foundationSection(resolvedFoundation, 0)
    if (section) sections.push(section)
  }

  let summary = summaryFrom(summaryValue)
  if (hasStructuredContent(sections, summary)) {
    return { sections, summary: summary || summaryFrom(report.summary) }
  }

  if (markdown.trim()) {
    const markdownSections = []
    if (resolvedFoundation) markdownSections.push(foundationSection(resolvedFoundation, 0))
    markdownSections.push({
      id: 'legacy-markdown',
      title: '完整解读',
      subtitle: '',
      content: markdown,
      items: [],
      blocks: [],
      kind: 'markdown'
    })
    return { sections: markdownSections.filter(Boolean), summary: null }
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
  return { sections: sections.filter(Boolean), summary }
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

  const model = buildReportDocument(report, { foundationData, markdown })
  return {
    id: report.id ?? null,
    title: (textValue(report.title) || '人生说明书').replace(/^辰鉴[·・]\s*/, ''),
    recipient: textValue(report.basicInfo?.name),
    reportDate: textValue(report.basicInfo?.reportDate),
    sections: model.sections,
    summary: model.summary
  }
}
