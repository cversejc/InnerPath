export function normalizeReportData(report) {
  const contentPayload = report.content_payload || report.contentPayload || null
  const source = contentPayload || report
  const rawBasicInfo = source.basicInfo || source.basic_info || report.basicInfo || report.basic_info || {}
  const rawEnergy = source.energyProfile || source.energy_profile || report.energyProfile || report.energy_profile || {}
  const rawCareer = source.careerGuidance || source.career_guidance || report.careerGuidance || report.career_guidance || {}
  const rawRelationship = source.relationshipPattern || source.relationship_pattern || report.relationshipPattern || report.relationship_pattern || {}
  const rawGrowth = source.personalGrowth || source.personal_growth || report.personalGrowth || report.personal_growth || {}

  return {
    basicInfo: {
      ...rawBasicInfo,
      name: rawBasicInfo.name || '用户',
      reportDate: rawBasicInfo.reportDate || rawBasicInfo.report_date || new Date().toISOString().split('T')[0]
    },
    contentPayload,
    structuredSections: source.structuredSections || source.structured_sections || report.structuredSections || report.structured_sections || null,
    energyProfile: {
      ...rawEnergy,
      coreTraits: rawEnergy.coreTraits || rawEnergy.core_traits || ''
    },
    careerGuidance: {
      ...rawCareer,
      suitablePaths: rawCareer.suitablePaths || rawCareer.suitable_paths || [],
      workStyle: rawCareer.workStyle || rawCareer.work_style || '',
      developmentSuggestions: rawCareer.developmentSuggestions || rawCareer.development_suggestions || []
    },
    relationshipPattern: {
      ...rawRelationship,
      growthDirection: rawRelationship.growthDirection || rawRelationship.growth_direction || '',
      strengths: rawRelationship.strengths || [],
      challenges: rawRelationship.challenges || []
    },
    personalGrowth: {
      ...rawGrowth,
      currentIssues: rawGrowth.currentIssues || rawGrowth.current_issues || [],
      actionPlan: rawGrowth.actionPlan || rawGrowth.action_plan || [],
      resources: rawGrowth.resources || []
    },
    summary: source.summary || report.summary || '',
    // New reports use edited structured content; legacy reports keep their original Markdown.
    aiGeneratedContent: contentPayload ? null : (report.aiGeneratedContent || report.ai_generated_content || report.ai_raw_content || null)
  }
}

function splitStemBranch(text) {
  if (text.length >= 2) return [text[0], text[1]]
  return [text, '']
}

function parseBazi(content) {
  const baziMatch = content.match(/### 八字四柱\s+([\s\S]*?)(?=###|$)/i)
  if (!baziMatch) return null

  const baziText = baziMatch[1]
  const bazi = {}
  const pillars = [
    ['year', /\*\*年柱：\*\*\s*([^\s（]+)(?:（([^）]+)）)?/],
    ['month', /\*\*月柱：\*\*\s*([^\s（]+)(?:（([^）]+)）)?/],
    ['day', /\*\*日柱[^：]*：\*\*\s*([^\s（]+)/],
    ['hour', /\*\*时柱：\*\*\s*([^\s（]+)(?:（([^）]+)）)?/]
  ]

  for (const [key, pattern] of pillars) {
    const match = baziText.match(pattern)
    if (!match) continue
    const [stem, branch] = splitStemBranch(match[1])
    bazi[key] = key === 'day' ? { stem, branch } : { stem, branch, ten_god: match[2] || '' }
  }

  return Object.keys(bazi).length ? bazi : null
}

function parseZiwei(content) {
  const ziweiMatch = content.match(/### 紫微斗数\s+([\s\S]*?)(?=##[^#]|$)/i)
  if (!ziweiMatch) return null

  const ziweiText = ziweiMatch[1]
  const ziwei = {}
  const palaces = [
    ['life_palace', '命宫'],
    ['career_palace', '事业宫'],
    ['wealth_palace', '财帛宫'],
    ['relationship_palace', '夫妻宫']
  ]

  for (const [key, label] of palaces) {
    const match = ziweiText.match(new RegExp(`\\*\\*${label}：\\*\\*\\s*([^\\n]+)`))
    if (!match) continue
    ziwei[key] = { main_stars: match[1].split('、').filter(star => star.trim()) }
    if (key === 'life_palace') ziwei[key].aux_stars = []
  }

  const auxStarsMatch = ziweiText.match(/\-\s*辅星：([^\n]+)/)
  if (auxStarsMatch && ziwei.life_palace) {
    ziwei.life_palace.aux_stars = auxStarsMatch[1].split('、').filter(star => star.trim())
  }

  const patternsMatch = ziweiText.match(/\*\*格局：\*\*\s*([^\n]+)/)
  if (patternsMatch) ziwei.patterns = patternsMatch[1].split('、').filter(pattern => pattern.trim())

  return Object.keys(ziwei).length ? ziwei : null
}

export function parseLegacyReportContent(content) {
  const hasBaziSection = /### 八字四柱\s+([\s\S]*?)(?=###|$)/i.test(content)
  const hasZiweiSection = /### 紫微斗数\s+([\s\S]*?)(?=##[^#]|$)/i.test(content)
  const bazi = parseBazi(content)
  const ziwei = parseZiwei(content)
  const foundationData = bazi || ziwei ? { ...(bazi ? { bazi } : {}), ...(ziwei ? { ziwei } : {}) } : null
  const contentWithoutFoundation = hasBaziSection || hasZiweiSection
    ? content.replace(/## 命理基础[\s\S]*?(?=\n## (?!#)|\n---\n|\n\n## (?!#)|$)/i, '')
    : content

  return { foundationData, contentWithoutFoundation }
}

export function formatReportMarkdown(content) {
  if (!content) return ''

  let html = content
    .replace(/^---$/gim, '<hr>')
    .replace(/^##### (.*$)/gim, '<h5>$1</h5>')
    .replace(/^#### (.*$)/gim, '<h4>$1</h4>')
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/^\- (.*$)/gim, '<li>$1</li>')
    .replace(/^\* (.*$)/gim, '<li>$1</li>')
    .replace(/\n\n+/g, '</p><p>')
    .replace(/\n/g, '<br>')

  html = html.replace(/(<li>.*?<\/li>(<br>)?)+/g, match => `<ul>${match.replace(/<br>/g, '')}</ul>`)
  if (!html.startsWith('<h') && !html.startsWith('<ul>')) html = `<p>${html}</p>`
  return html
}
